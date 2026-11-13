#!/usr/bin/env bash
# Download a GNPS2 task's tables (FBMN or Everything Bagel) into data/<dataset_name>/
#
#   ./download.sh                                  # the Ocean dataset (default below)
#   ./download.sh <task_id> <dataset_name>         # any FBMN or EB task
#   ./download.sh <task_id>                        # named after the task ID
#
# The workflow (FBMN or EB) is read from the task's job_parameters.yaml.
#
# Result:
#   data/<dataset_name>/
#     info.json           {"dataset_name", "workflow": "FBMN" | "EB", "task_id"}
#     feature_table.csv   feature quantification table
#     metadata.tsv        sample metadata (metadata.csv if the task's file was a CSV)
#     annotations.tsv     library annotations
set -euo pipefail

if [ $# -eq 0 ]; then
  TASK_ID="454547be77d94ae1ad00d798046ee7a0"
  NAME="ocean_fbmn"
else
  TASK_ID="$1"
  NAME="${2:-$1}"
fi
if ! [[ "$NAME" =~ ^[A-Za-z0-9_-]+$ ]]; then
  echo "dataset_name may only use letters, digits, _ and -" >&2
  exit 1
fi
if ! [[ "$TASK_ID" =~ ^[A-Za-z0-9]+$ ]]; then
  echo "task_id may only use letters and digits" >&2
  exit 1
fi

cd "$(dirname "$0")"
OUT="data/$NAME"
TMP="data/.download-$NAME"
rm -rf "$TMP"
mkdir -p "$TMP"
trap 'rm -rf "$TMP"' EXIT   # no half-finished folder if a download fails

fetch() {  # fetch <path in task> <local file>
  echo "Downloading $1"
  curl -fSL -# --retry 3 -A "ocean-portal-api" -o "$TMP/$2" \
    "https://gnps2.org/resultfile?task=${TASK_ID}&file=$1"
}

# Which workflow ran this task?
fetch job_parameters.yaml job_parameters.yaml
WORKFLOW_NAME=$(grep -E '^workflowname:' "$TMP/job_parameters.yaml" | awk '{print $2}' || true)
param() {  # value of a top-level key in job_parameters.yaml
  grep -E "^$1:" "$TMP/job_parameters.yaml" | head -1 | sed -E "s/^$1:[[:space:]]*//; s/^[\"']//; s/[\"']$//" || true
}

case "$WORKFLOW_NAME" in
  feature_based_molecular_networking_workflow)
    WORKFLOW="FBMN"
    fetch nf_output/clustering/featuretable_reformated.csv feature_table.csv
    fetch nf_output/metadata/merged_metadata.tsv           metadata.tsv
    fetch nf_output/library/merged_results_with_gnps.tsv   annotations.tsv
    ;;
  everything_bagel_workflow)
    WORKFLOW="EB"
    fetch nf_output/feature_finding/feature_finding_results/aligned_features.csv      feature_table.csv
    fetch nf_output/feature_library_search/merged_feature_library_search_results.tsv annotations.tsv
    # EB keeps the uploaded metadata in a folder named after the task parameter
    META=""
    for p in metadata_file metadata_filename; do
      v=$(param "$p")
      if [ -n "$v" ] && [ "$v" != "NO_FILE" ]; then META="$p/$(basename "$v")"; break; fi
    done
    if [ -z "$META" ]; then
      echo "No metadata file in this EB task's parameters" >&2
      exit 1
    fi
    case "$META" in *.csv) fetch "$META" metadata.csv ;; *) fetch "$META" metadata.tsv ;; esac
    ;;
  *)
    echo "Task $TASK_ID ran '${WORKFLOW_NAME:-unknown}'; only FBMN and Everything Bagel tasks are supported" >&2
    exit 1
    ;;
esac
rm "$TMP/job_parameters.yaml"

printf '{"dataset_name": "%s", "workflow": "%s", "task_id": "%s"}\n' "$NAME" "$WORKFLOW" "$TASK_ID" > "$TMP/info.json"

# replace any previous download only once everything arrived
rm -rf "$OUT"
mv "$TMP" "$OUT"
echo "Done: $OUT ($WORKFLOW)"
ls -lh "$OUT"

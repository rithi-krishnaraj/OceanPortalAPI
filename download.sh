#!/usr/bin/env bash
# Download a GNPS2 FBMN task's tables into data/<dataset_name>/
#
#   ./download.sh                                  # the Ocean dataset (default below)
#   ./download.sh <task_id> <dataset_name>         # any FBMN task
#
# Result:
#   data/<dataset_name>/
#     feature_table.csv   feature quantification table (nf_output/clustering/featuretable_reformated.csv)
#     metadata.tsv        sample metadata             (nf_output/metadata/merged_metadata.tsv)
#     annotations.tsv     library annotations         (nf_output/library/merged_results_with_gnps.tsv)
#     task_id.txt         the GNPS2 task it came from
set -euo pipefail

TASK_ID="${1:-454547be77d94ae1ad00d798046ee7a0}"
NAME="${2:-ocean_fbmn}"

cd "$(dirname "$0")"
OUT="data/$NAME"
TMP="data/.download-$NAME"
rm -rf "$TMP"
mkdir -p "$TMP"

fetch() {  # fetch <path in task> <local file>
  echo "Downloading $1"
  curl -fSL -# --retry 3 -A "ocean-portal-api" -o "$TMP/$2" \
    "https://gnps2.org/resultfile?task=${TASK_ID}&file=$1"
}

fetch nf_output/clustering/featuretable_reformated.csv feature_table.csv
fetch nf_output/metadata/merged_metadata.tsv           metadata.tsv
fetch nf_output/library/merged_results_with_gnps.tsv   annotations.tsv
echo "$TASK_ID" > "$TMP/task_id.txt"

# replace any previous download only once everything arrived
rm -rf "$OUT"
mv "$TMP" "$OUT"
echo "Done: $OUT"
ls -lh "$OUT"

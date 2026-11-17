"""
Save each dataset's downloaded tables (CSV/TSV) as Parquet, which the API reads much
faster, and delete the CSV/TSV. Datasets with nothing left to convert are skipped.

    python convert.py                  every dataset in data/
    python convert.py <name> ...       just these datasets
    python convert.py --force ...      rewrite the Parquet even if it is up to date
                                       (only for tables whose CSV/TSV is still there)

`make download` runs this after each download; `make convert` runs it on its own.
"""
import sys
import time

from tables import DATA_DIR, convert


def main(args: list[str]) -> None:
    force = "--force" in args
    names = [a for a in args if a != "--force"]
    folders = ([DATA_DIR / n for n in names] if names else
               sorted(p.parent for p in DATA_DIR.glob("*/info.json") if not p.parent.name.startswith(".")))
    for folder in folders:
        if not (folder / "info.json").exists():
            sys.exit(f"No dataset '{folder.name}' in {DATA_DIR}")
        start = time.perf_counter()
        done = convert(folder, force=force)
        took = time.perf_counter() - start
        print(f"{folder.name}: " + (f"converted {', '.join(done)} ({took:.1f}s)" if done else "up to date"))


if __name__ == "__main__":
    main(sys.argv[1:])

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy Silver *_valid Delta table folders to exact *_valid_test folder clones."
    )
    parser.add_argument(
        "--silver-root",
        default="/app/scripts/silver_layer",
        help="Silver Delta root folder.",
    )
    parser.add_argument(
        "--tables",
        nargs="+",
        default=["all"],
        help="Silver source table names without suffix (example: enrolment demographic) or 'all'.",
    )
    parser.add_argument(
        "--mode",
        choices=["overwrite"],
        default="overwrite",
        help="Only overwrite is supported because exact-copy mode replaces the destination folder.",
    )
    return parser.parse_args()


def discover_valid_tables(silver_root: Path) -> list[str]:
    names: list[str] = []
    if not silver_root.exists():
        return names
    for child in silver_root.iterdir():
        if not child.is_dir():
            continue
        if not child.name.endswith("_valid"):
            continue
        if not (child / "_delta_log").exists():
            continue
        base = child.name[: -len("_valid")]
        names.append(base)
    return sorted(names)


def resolve_tables(requested: list[str], silver_root: Path) -> list[str]:
    if "all" in requested:
        return discover_valid_tables(silver_root)
    return requested


def clone_delta_folder(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def main() -> None:
    args = parse_args()
    silver_root = Path(args.silver_root)
    tables = resolve_tables(args.tables, silver_root)
    if not tables:
        raise ValueError(
            f"No Silver tables selected. Check --silver-root and --tables. silver_root={silver_root}"
        )

    for table in tables:
        src = silver_root / f"{table}_valid"
        dst = silver_root / f"{table}_valid_test"

        if not (src / "_delta_log").exists():
            print(f"[SKIP] Source not found or not Delta: {src}")
            continue

        clone_delta_folder(src, dst)
        file_count = sum(1 for path in dst.rglob("*") if path.is_file())
        print(f"[OK] {src.name} -> {dst.name} | exact folder copy complete | files={file_count}")


if __name__ == "__main__":
    main()

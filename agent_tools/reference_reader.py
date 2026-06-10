import os
from pathlib import Path

REFERENCE_DIR = Path(__file__).resolve().parent.parent / "reference"


def read_reference_files(ref_dir: str | None = None) -> dict[str, str]:
    target = Path(ref_dir) if ref_dir else REFERENCE_DIR
    if not target.exists():
        return {}

    files = {}
    for f in sorted(target.rglob("*")):
        if f.suffix.lower() in (".v", ".sv", ".svh", ".vh", ".txt", ".md", ".py"):
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            files[str(f.relative_to(target))] = content
    return files


def list_reference_files(ref_dir: str | None = None) -> list[str]:
    target = Path(ref_dir) if ref_dir else REFERENCE_DIR
    if not target.exists():
        return []
    return [
        str(f.relative_to(target))
        for f in sorted(target.rglob("*"))
        if f.is_file()
    ]


if __name__ == "__main__":
    files = read_reference_files()
    for name, content in files.items():
        print(f"=== {name} ===")
        print(content[:500])
        print(f"... ({len(content)} chars total)")

import json
import os
import shutil
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"


def create_project(
    name: str,
    sources: list[str],
    toplevel: str,
    test_module: str,
    *,
    output_dir: str | None = None,
    sim: str = "verilator",
) -> str:
    proj_dir = Path(output_dir) if output_dir else OUTPUTS_DIR / name
    proj_dir.mkdir(parents=True, exist_ok=True)
    (proj_dir / "src").mkdir(exist_ok=True)
    (proj_dir / "tb").mkdir(exist_ok=True)

    cfg = {
        "sources": sources,
        "toplevel": toplevel,
        "test_module": test_module,
        "sim": sim,
    }
    with open(proj_dir / "project.json", "w") as f:
        json.dump(cfg, f, indent=4)

    return str(proj_dir)


def copy_templates(proj_dir: str, templates: dict[str, str] | None = None):
    proj = Path(proj_dir)

    if templates is None:
        templates = {}

    for dest, tmpl_name in templates.items():
        tmpl_path = TEMPLATES_DIR / tmpl_name
        dest_path = proj / dest
        if tmpl_path.exists():
            shutil.copy(tmpl_path, dest_path)
        else:
            dest_path.write_text("// TODO: write module\nmodule dummy;\nendmodule\n")

    if "tb/test_basic.py" not in templates:
        default_tb = TEMPLATES_DIR / "tb_basic.py"
        if default_tb.exists():
            shutil.copy(default_tb, proj / "tb" / "test_basic.py")


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="FPGA Project Generator")
    p.add_argument("name", help="Project name")
    p.add_argument("--sources", nargs="+", required=True, help="Source file paths (relative to src/)")
    p.add_argument("--toplevel", required=True)
    p.add_argument("--test-module", required=True)
    p.add_argument("--output-dir", default=None)
    p.add_argument("--sim", default="verilator")

    args = p.parse_args()

    path = create_project(
        name=args.name,
        sources=args.sources,
        toplevel=args.toplevel,
        test_module=args.test_module,
        output_dir=args.output_dir,
        sim=args.sim,
    )
    print(f"Created project at: {path}")

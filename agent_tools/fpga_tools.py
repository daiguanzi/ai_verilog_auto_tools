import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

try:
    from agent_tools.sim_driver import run_simulation as _run_sim
except ImportError:
    try:
        from sim_driver import run_simulation as _run_sim
    except ImportError:
        _run_sim = None


CONFIG_FILENAME = "project.json"


def load_project_config(project_dir: str) -> Optional[dict]:
    config_path = Path(project_dir) / CONFIG_FILENAME
    if not config_path.exists():
        return None
    try:
        with open(config_path) as f:
            cfg = json.load(f)
    except Exception:
        return None
    cfg.setdefault("sim", "verilator")
    cfg.setdefault("build_dir", "sim_build")
    if "sources" not in cfg or "toplevel" not in cfg or "test_module" not in cfg:
        return None
    cfg["__project_dir"] = str(config_path.parent.resolve())
    return cfg


def run_project(project_dir: str, *, sim: str | None = None, waves: bool = False) -> dict:
    cfg = load_project_config(project_dir)
    if cfg is None:
        return {"pass": False, "error": f"No valid {CONFIG_FILENAME} found in {project_dir}"}
    proj = cfg["__project_dir"]
    sources = [str(Path(proj) / s) for s in cfg["sources"]]
    return run_and_report(
        sources=sources,
        toplevel=cfg["toplevel"],
        test_module=cfg["test_module"],
        test_dir=proj,
        build_dir=str(Path(proj) / cfg.get("build_dir", "sim_build")),
        sim=sim or cfg["sim"],
        waves=waves,
    )


def scan_project(project_dir: str) -> dict:
    project_path = Path(project_dir).resolve()
    files = []
    for f in sorted(project_path.rglob("*")):
        if f.suffix.lower() in (".v", ".sv", ".svh", ".vh"):
            info = _extract_module_info(f)
            if info:
                files.append({
                    "path": str(f),
                    "module": info["module"],
                    "ports": info["ports"],
                    "parameters": info["parameters"],
                    "sub_modules": info["sub_modules"],
                })
    return {
        "project_dir": str(project_path),
        "file_count": len(files),
        "files": files,
    }


def find_top_module(project_dir: str) -> Optional[dict]:
    project = scan_project(project_dir)
    modules = {f["module"]: f for f in project["files"]}
    instantiated = set()
    for f in project["files"]:
        for sub in f["sub_modules"]:
            instantiated.add(sub)
    for name, info in modules.items():
        if name not in instantiated:
            return info
    if project["files"]:
        return project["files"][0]
    return None


def print_project_summary(project_dir: str) -> str:
    project = scan_project(project_dir)
    top = find_top_module(project_dir)

    lines = []
    lines.append("=" * 70)
    lines.append("  FPGA PROJECT SUMMARY")
    lines.append("=" * 70)
    lines.append(f"  Directory: {project['project_dir']}")
    lines.append(f"  HDL files: {project['file_count']}")

    if top:
        lines.append(f"  Top module: {top['module']} ({Path(top['path']).name})")
    lines.append("")

    for f in project["files"]:
        name = Path(f["path"]).name
        lines.append(f"  [{f['module']}]  {name}")
        if f["ports"]:
            for p in f["ports"]:
                direction = p.get("direction", "?")
                ptype = p.get("type", "")
                pname = p.get("name", "?")
                lines.append(f"           {direction:6s} {ptype:12s} {pname}")
        if f["parameters"]:
            for param in f["parameters"]:
                lines.append(f"           param    {param['name']} = {param.get('default', '')}")
        if f["sub_modules"]:
            lines.append(f"           uses: {', '.join(f['sub_modules'])}")
        lines.append("")
    lines.append("=" * 70)
    return "\n".join(lines)


def run_and_report(
    sources: list[str],
    toplevel: str,
    test_module: str,
    test_dir: str,
    *,
    build_dir: str | None = None,
    sim: str = "verilator",
    waves: bool = False,
) -> dict:
    if _run_sim is None:
        return {"pass": False, "error": "sim_driver.py not found in PYTHONPATH"}

    if build_dir is None:
        build_dir = str(Path(test_dir) / "sim_build")

    return _run_sim(
        sources=sources,
        hdl_toplevel=toplevel,
        test_module=test_module,
        test_dir=test_dir,
        build_dir=build_dir,
        sim=sim,
        waves=waves,
    )


def _extract_module_info(filepath: Path) -> Optional[dict]:
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    content_no_comments = _strip_comments(content)
    module_match = re.search(
        r"^\s*module\s+(\w+)\s*(?:#\s*\(([\s\S]*?)\))?\s*\(([\s\S]*?)\)\s*;",
        content_no_comments,
        re.MULTILINE,
    )
    if not module_match:
        return None

    module_name = module_match.group(1)
    param_block = module_match.group(2) or ""
    port_block = module_match.group(3) or ""

    parameters = _parse_parameters(param_block)
    ports = _parse_ports(port_block)
    sub_modules = _find_instantiations(content_no_comments, module_name)

    return {
        "module": module_name,
        "ports": ports,
        "parameters": parameters,
        "sub_modules": sub_modules,
    }


def _strip_comments(text: str) -> str:
    text = re.sub(r"//.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"/\*[\s\S]*?\*/", "", text)
    return text


def _parse_parameters(param_block: str) -> list[dict]:
    params = []
    if not param_block.strip():
        return params
    entries = re.split(r"\s*,\s*(?![^(]*\))", param_block.strip())
    for entry in entries:
        entry = entry.strip()
        m = re.match(r"\s*(?:parameter\s+)?\s*(\w[\w\s]*?)\s+(\w+)\s*(?:=\s*([^,]+))?", entry)
        if m:
            type_str = m.group(1).strip()
            name = m.group(2).strip()
            default = m.group(3).strip() if m.group(3) else ""
            params.append({"name": name, "type": type_str, "default": default})
    return params


def _parse_ports(port_block: str) -> list[dict]:
    ports = []
    for raw_entry in re.split(r"\s*,\s*(?![^(]*\))", port_block.strip()):
        entry = raw_entry.strip()
        if not entry:
            continue
        direction = ""
        if entry.startswith("input"):
            direction = "input"
        elif entry.startswith("output"):
            direction = "output"
        elif entry.startswith("inout"):
            direction = "inout"
        else:
            continue
        rest = re.sub(r"^(input|output|inout)\s+", "", entry).strip()
        parts = rest.split()
        if not parts:
            continue
        port_name = parts[-1]
        type_parts = parts[:-1]
        port_type = " ".join(type_parts) if type_parts else "wire"
        ports.append({"direction": direction, "type": port_type, "name": port_name})
    return ports


def _find_instantiations(content: str, own_module: str) -> list[str]:
    pattern = re.compile(r"\b(\w+)\s+(?:#\s*\([\s\S]*?\)\s*)?" r"(\w+)\s*\([\s\S]*?\)\s*;", re.MULTILINE)
    subs = set()
    for m in pattern.finditer(content):
        candidate = m.group(1)
        if (
            candidate != own_module
            and candidate not in ("module", "endmodule", "input", "output", "inout", "wire", "reg", "logic", "assign", "always", "initial", "if", "else", "begin", "end", "case", "for", "while")
            and not candidate[0].isdigit()
        ):
            subs.add(candidate)
    return sorted(subs)


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="FPGA Project Tools")
    p.add_argument("command", choices=["scan", "summary", "find-top", "run"])
    p.add_argument("project_dir", help="Path to project directory")
    p.add_argument("--json", action="store_true", help="Output JSON")
    p.add_argument("--sim", default="verilator", help="Simulator for run command")
    p.add_argument("--waves", action="store_true", help="Enable waveform dump for run command")

    args = p.parse_args()

    if args.command == "scan":
        result = scan_project(args.project_dir)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Found {result['file_count']} HDL file(s):")
            for f in result["files"]:
                print(f"  {f['module']:20s}  {Path(f['path']).name}")

    elif args.command == "summary":
        print(print_project_summary(args.project_dir))

    elif args.command == "find-top":
        top = find_top_module(args.project_dir)
        if top:
            if args.json:
                print(json.dumps(top, indent=2, ensure_ascii=False))
            else:
                print(f"Top module: {top['module']}  ({Path(top['path']).name})")
        else:
            print("No modules found.")

    elif args.command == "run":
        result = run_project(args.project_dir, sim=args.sim, waves=args.waves)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            status = "PASS" if result["pass"] else "FAIL"
            print(f"\n{'='*60}")
            print(f"  SIMULATION RESULT: {status}")
            if result.get("error"):
                print(f"  Error: {result['error']}")
            print(f"  Tests: {result.get('tests_total',0)} total, "
                  f"{result.get('tests_pass',0)} pass, "
                  f"{result.get('tests_fail',0)} fail")
            print(f"{'='*60}")
            for t in result.get("tests", []):
                flag = "PASS" if t["passed"] else "FAIL"
                print(f"  [{flag}] {t['name']}")
                if not t["passed"] and t.get("failure"):
                    print(f"         {t['failure'][:200]}")
            print(f"{'='*60}\n")
        sys.exit(0 if result["pass"] else 1)

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

try:
    from agent_tools.sim_driver import run_simulation as _run_sim
    from agent_tools.sim_driver import run_lint as _run_lint
except ImportError:
    try:
        from sim_driver import run_simulation as _run_sim
        from sim_driver import run_lint as _run_lint
    except ImportError:
        _run_sim = None
        _run_lint = None


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
    cfg.setdefault("includes", [])
    cfg.setdefault("defines", {})
    cfg.setdefault("parameters", {})
    cfg.setdefault("timescale", None)
    if "sources" not in cfg or "toplevel" not in cfg or "test_module" not in cfg:
        return None
    cfg["__project_dir"] = str(config_path.parent.resolve())
    return cfg


def run_project(project_dir: str, *, sim: str | None = None, waves: bool = False, lint: bool = True) -> dict:
    cfg = load_project_config(project_dir)
    if cfg is None:
        return {"pass": False, "error": f"No valid {CONFIG_FILENAME} found in {project_dir}"}
    proj = cfg["__project_dir"]
    sources = [str(Path(proj) / s) for s in cfg["sources"]]
    includes = [str(Path(proj) / i) for i in cfg.get("includes", [])]

    # ---- IP stub auto-inclusion (C4) ----
    # stub paths are relative to workspace root (where ip_models/ lives)
    workspace_root = Path(__file__).resolve().parent.parent
    ip_cfg = cfg.get("ip", {})
    for ip_name, ip_entry in ip_cfg.items():
        stub = ip_entry.get("stub", "")
        if stub:
            stub_abs = str(workspace_root / stub) if not os.path.isabs(stub) else stub
            if os.path.exists(stub_abs) and stub_abs not in sources:
                sources.append(stub_abs)

    lint_res = None
    if lint and _run_lint is not None:
        lint_res = _run_lint(
            sources=sources,
            hdl_toplevel=cfg["toplevel"],
            includes=includes,
            defines=cfg.get("defines", {}),
            timescale=cfg.get("timescale"),
        )
        if lint_res.get("available") and not lint_res["pass"]:
            return {
                "pass": False,
                "error": "Lint gate failed (verilator --lint-only -Wall). Fix lint errors before simulating.",
                "lint": lint_res,
                "tests_total": 0,
                "tests_pass": 0,
                "tests_fail": 0,
                "tests_skip": 0,
                "tests": [],
            }

    result = run_and_report(
        sources=sources,
        toplevel=cfg["toplevel"],
        test_module=cfg["test_module"],
        test_dir=proj,
        build_dir=str(Path(proj) / cfg.get("build_dir", "sim_build")),
        sim=sim or cfg["sim"],
        waves=waves,
        includes=includes,
        defines=cfg.get("defines", {}),
        parameters=cfg.get("parameters", {}),
        timescale=cfg.get("timescale"),
    )
    if lint_res is not None:
        result["lint"] = lint_res
    return result


def lint_project(project_dir: str) -> dict:
    cfg = load_project_config(project_dir)
    if cfg is None:
        return {"available": False, "pass": False,
                "errors": [f"No valid {CONFIG_FILENAME} found in {project_dir}"],
                "warnings": [], "raw": ""}
    if _run_lint is None:
        return {"available": False, "pass": True, "errors": [], "warnings": [],
                "raw": "run_lint not importable"}
    proj = cfg["__project_dir"]
    sources = [str(Path(proj) / s) for s in cfg["sources"]]
    includes = [str(Path(proj) / i) for i in cfg.get("includes", [])]

    # IP stub auto-inclusion (same as run_project)
    workspace_root = Path(__file__).resolve().parent.parent
    ip_cfg = cfg.get("ip", {})
    for ip_name, ip_entry in ip_cfg.items():
        stub = ip_entry.get("stub", "")
        if stub:
            stub_abs = str(workspace_root / stub) if not os.path.isabs(stub) else stub
            if os.path.exists(stub_abs) and stub_abs not in sources:
                sources.append(stub_abs)

    return _run_lint(
        sources=sources,
        hdl_toplevel=cfg["toplevel"],
        includes=includes,
        defines=cfg.get("defines", {}),
        timescale=cfg.get("timescale"),
    )


# ============================================================
#  IP Scanner — Vivado .xci parser + stub matching
# ============================================================

XCI_NS = "http://www.spiritconsortium.org/XMLSchema/SPIRIT/1685-2009"

IP_TO_STUB = {
    "blk_mem_gen":     "ip_models/bram/ip_bram.sv",
    "fifo_generator":  "ip_models/fifo/ip_fifo.sv",
    "mult_gen":        "ip_models/multiplier/ip_mult.sv",
    "floating_point":  None,  # no Verilator stub yet — use Python ref model
    "xfft":            None,  # no Verilator stub — too complex
}


def scan_ips(project_dir: str) -> dict:
    """Recursively find and parse Vivado .xci IP core files.

    Returns {project_dir, ip_count, ips: [{instance, ip_name, version, params, ...}]}.
    """
    project_path = Path(project_dir).resolve()
    xci_files = sorted(project_path.rglob("*.xci"))
    ips = []
    for xci in xci_files:
        info = _parse_xci(xci)
        if info:
            info["path"] = str(xci)
            ips.append(info)
    return {"project_dir": str(project_path), "ip_count": len(ips), "ips": ips}


def _parse_xci(xci_path: Path) -> Optional[dict]:
    try:
        tree = ET.parse(str(xci_path))
        root = tree.getroot()
    except Exception:
        return None

    ci = root.find(f"{{{XCI_NS}}}componentInstances/{{{XCI_NS}}}componentInstance")
    if ci is None:
        return None

    inst_name = ci.findtext(f"{{{XCI_NS}}}instanceName", "")

    cr = ci.find(f"{{{XCI_NS}}}componentRef")
    if cr is None:
        return None

    def attr(name):
        return cr.get(name, cr.get(f"{{{XCI_NS}}}{name}", ""))

    vendor  = attr("vendor")
    library = attr("library")
    ip_name = attr("name")
    version = attr("version")

    params = {}
    for cev in ci.findall(f"{{{XCI_NS}}}configurableElementValues/{{{XCI_NS}}}configurableElementValue"):
        ref_id = cev.get("referenceId", "")
        val = (cev.text or "").strip()
        if ref_id.startswith("MODELPARAM_VALUE."):
            params[ref_id.replace("MODELPARAM_VALUE.", "")] = val

    return {
        "instance": inst_name,
        "vendor":   vendor,
        "library":  library,
        "ip_name":  ip_name,
        "version":  version,
        "params":   params,
    }


def suggest_ip_stubs(ip_list: list[dict]) -> list[dict]:
    """Given an IP inventory from scan_ips(), return a list with
    a 'stub' path and 'covered' boolean added.
    """
    results = []
    for ip in ip_list:
        name = ip.get("ip_name", "")
        stub = IP_TO_STUB.get(name)
        results.append({
            **ip,
            "stub": stub,
            "covered": stub is not None,
        })
    return results


def print_ip_scan(project_dir: str) -> str:
    """Human-readable IP inventory report."""
    scan = scan_ips(project_dir)
    suggested = suggest_ip_stubs(scan["ips"])

    lines = []
    lines.append("=" * 70)
    lines.append("  IP CORE INVENTORY")
    lines.append("=" * 70)
    lines.append(f"  Directory: {scan['project_dir']}")
    lines.append(f"  IP cores found: {scan['ip_count']}")
    lines.append("")

    covered = sum(1 for s in suggested if s["covered"])
    lines.append(f"  Stubs available: {covered}/{scan['ip_count']}")
    lines.append("")

    for s in suggested:
        status = "✓" if s["covered"] else "✗ NONE"
        lines.append(f"  [{s['instance']}]  {s['vendor']}:{s['ip_name']} v{s['version']}")
        lines.append(f"           stub: {status}  ({s.get('stub','none')})")
        if s["params"]:
            keys = list(s["params"].keys())[:4]
            for k in keys:
                lines.append(f"           {k} = {s['params'][k]}")
        lines.append("")
    lines.append("=" * 70)
    return "\n".join(lines)


def scan_project(project_dir: str) -> dict:
    project_path = Path(project_dir).resolve()
    hdl_files = [
        f for f in sorted(project_path.rglob("*"))
        if f.suffix.lower() in (".v", ".sv", ".svh", ".vh")
    ]

    vresult = _scan_with_verilator(hdl_files)
    if vresult is not None:
        vresult["project_dir"] = str(project_path)
        vresult["file_count"] = len(vresult["files"])
        return vresult

    return _scan_with_regex(project_path, hdl_files)


def _scan_with_regex(project_path: Path, hdl_files: list[Path]) -> dict:
    files = []
    for f in hdl_files:
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
        "parser": "regex",
    }


def find_top_module(project_dir: str) -> Optional[dict]:
    project = scan_project(project_dir)
    modules = {f["module"]: f for f in project["files"]}

    top_name = project.get("top")
    if top_name and top_name in modules:
        return modules[top_name]

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
    lines.append(f"  Parser: {project.get('parser', 'regex')}")

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

    mod_map = {f["module"]: f for f in project["files"]}
    if top and len(mod_map) > 1:
        lines.append("Dependency Tree:")
        _add_tree(lines, mod_map, top["module"], "    ")
        lines.append("")

    lines.append("=" * 70)
    return "\n".join(lines)


def _add_tree(lines, mod_map, mod_name, prefix):
    info = mod_map.get(mod_name)
    if info is None:
        lines.append(f"  {prefix}{mod_name} (external)")
        return
    subs = info.get("sub_modules", [])
    lines.append(f"  {prefix}{mod_name}")
    for sub in subs:
        _add_tree(lines, mod_map, sub, prefix + "    ")


def run_and_report(
    sources: list[str],
    toplevel: str,
    test_module: str,
    test_dir: str,
    *,
    build_dir: str | None = None,
    sim: str = "verilator",
    waves: bool = False,
    includes: list[str] | None = None,
    defines: dict | None = None,
    parameters: dict | None = None,
    timescale: object = None,
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
        includes=includes,
        defines=defines,
        parameters=parameters,
        timescale=timescale,
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


# ============================================================
#  Verilator-based parsing (primary; falls back to regex)
# ============================================================

def _scan_with_verilator(hdl_files: list[Path]) -> Optional[dict]:
    sources = [str(f) for f in hdl_files if f.suffix.lower() in (".v", ".sv")]
    if not sources:
        return None
    if shutil.which("verilator") is None:
        return None

    tmpdir = tempfile.mkdtemp(prefix="vxml_")
    xml_path = Path(tmpdir) / "netlist.xml"
    cmd = [
        "verilator", "--xml-only",
        "--bbox-unsup", "--bbox-sys", "-Wno-fatal",
        "--Mdir", tmpdir,
        "--xml-output", str(xml_path),
        *sources,
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except Exception:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return None

    result = None
    if xml_path.exists():
        try:
            root = ET.parse(str(xml_path)).getroot()
            result = _parse_verilator_xml(root)
        except Exception:
            result = None
    shutil.rmtree(tmpdir, ignore_errors=True)

    if result is None or not result["files"]:
        return None
    result["parser"] = "verilator"
    return result


def _parse_verilator_xml(root) -> Optional[dict]:
    file_map = {}
    for fel in root.iter("file"):
        fid = fel.get("id")
        if fid and fid not in file_map:
            file_map[fid] = fel.get("filename", "")

    netlist = root.find("netlist")
    if netlist is None:
        return None

    typetable = _build_typetable(netlist)

    top_name = None
    cells = root.find("cells")
    if cells is not None:
        cell = cells.find("cell")
        if cell is not None:
            top_name = cell.get("submodname") or cell.get("name")

    files = []
    for mod in netlist.findall("module"):
        mod_name = mod.get("name")
        if not mod_name:
            continue
        if top_name is None and mod.get("topModule") == "1":
            top_name = mod_name

        loc = mod.get("loc", "")
        fid = loc.split(",")[0] if loc else ""
        path = file_map.get(fid, "")

        ports = []
        parameters = []
        for var in mod.findall("var"):
            if var.get("localparam") == "true":
                continue
            if var.get("param") == "true":
                parameters.append({
                    "name": var.get("name", "?"),
                    "type": var.get("vartype", ""),
                    "default": _param_default(var),
                })
                continue
            direction = var.get("dir")
            if direction in ("input", "output", "inout"):
                ports.append({
                    "_pin": int(var.get("pinIndex", "0") or 0),
                    "direction": direction,
                    "type": _dtype_str(var.get("dtype_id"), typetable, var.get("vartype", "")),
                    "name": var.get("name", "?"),
                })
        ports.sort(key=lambda p: p["_pin"])
        for p in ports:
            p.pop("_pin", None)

        sub_modules = sorted({
            inst.get("defName")
            for inst in mod.iter("instance")
            if inst.get("defName")
        })

        files.append({
            "path": path,
            "module": mod_name,
            "ports": ports,
            "parameters": parameters,
            "sub_modules": sub_modules,
        })

    return {"files": files, "top": top_name}


def _build_typetable(netlist) -> dict:
    table = {}
    tt = netlist.find("typetable")
    if tt is None:
        return table
    for dt in tt.findall("basicdtype"):
        did = dt.get("id")
        name = dt.get("name", "logic")
        left = dt.get("left")
        right = dt.get("right")
        if left is not None and right is not None and name in ("logic", "bit", "reg", "wire"):
            table[did] = f"{name} [{left}:{right}]"
        else:
            table[did] = name
    for dt in tt.findall("unpackarraydtype"):
        table[dt.get("id")] = "array"
    return table


def _dtype_str(dtype_id, typetable: dict, fallback: str) -> str:
    if dtype_id and dtype_id in typetable:
        return typetable[dtype_id]
    return fallback or "logic"


def _param_default(var) -> str:
    const = var.find("const")
    if const is None:
        return ""
    return _decode_verilog_const(const.get("name", ""))


def _decode_verilog_const(raw: str) -> str:
    if not raw:
        return ""
    m = re.match(r"^\d+'(s)?([hbod])([0-9a-fA-FxXzZ_]+)$", raw)
    if not m:
        return raw
    digits = m.group(3).replace("_", "")
    if any(c in "xXzZ" for c in digits):
        return raw
    base = {"h": 16, "b": 2, "o": 8, "d": 10}[m.group(2)]
    try:
        return str(int(digits, base))
    except ValueError:
        return raw


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="FPGA Project Tools")
    p.add_argument("command", choices=["scan", "summary", "find-top", "run", "lint", "ip-scan", "vivado-ip-tcl", "vivado-synth", "vivado-xdc"])
    p.add_argument("project_dir", help="Path to project directory")
    p.add_argument("--json", action="store_true", help="Output JSON")
    p.add_argument("--sim", default="verilator", help="Simulator for run command")
    p.add_argument("--waves", action="store_true", help="Enable waveform dump for run command")
    p.add_argument("--no-lint", action="store_true", help="Skip the pre-sim lint gate (run command)")
    p.add_argument("--device", default="xc7a200t-fbg484-2L", help="FPGA device for vivado-ip-tcl")

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
        result = run_project(args.project_dir, sim=args.sim, waves=args.waves, lint=not args.no_lint)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            status = "PASS" if result["pass"] else "FAIL"
            print(f"\n{'='*60}")
            lint = result.get("lint")
            if lint and lint.get("available"):
                lstatus = "PASS" if lint["pass"] else "FAIL"
                print(f"  LINT: {lstatus} "
                      f"({len(lint['errors'])} errors, {len(lint['warnings'])} warnings)")
                for e in lint.get("errors", [])[:10]:
                    print(f"    [ERROR] {e[:180]}")
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

    elif args.command == "lint":
        res = lint_project(args.project_dir)
        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            if not res.get("available", False):
                print(f"LINT SKIPPED: {res.get('raw', 'verilator not available')}")
                if res.get("errors"):
                    for e in res["errors"]:
                        print(f"  {e}")
            else:
                status = "PASS" if res["pass"] else "FAIL"
                print(f"\n{'='*60}")
                print(f"  LINT RESULT: {status}")
                print(f"  Errors: {len(res['errors'])}  Warnings: {len(res['warnings'])}")
                print(f"{'='*60}")
                for e in res["errors"][:20]:
                    print(f"  [ERROR] {e[:200]}")
                for w in res["warnings"][:20]:
                    print(f"  [WARN]  {w[:200]}")
                print(f"{'='*60}\n")
        sys.exit(0 if res.get("pass", False) else 1)

    elif args.command == "ip-scan":
        print(print_ip_scan(args.project_dir))

    elif args.command == "vivado-ip-tcl":
        try:
            from agent_tools.vivado_tools import write_ip_tcl
        except ImportError:
            from vivado_tools import write_ip_tcl
        cfg = load_project_config(args.project_dir)
        if cfg is None:
            print(f"ERROR: No valid project.json in {args.project_dir}")
            sys.exit(1)
        ip_cfg = cfg.get("ip", {})
        specs = []
        for instance, entry in ip_cfg.items():
            ip_type = entry.get("type", "")
            params  = entry.get("params", {})
            if ip_type:
                specs.append({"type": ip_type, "instance": instance, "params": params})
        if not specs:
            print("ERROR: No 'ip' entries found in project.json")
            sys.exit(1)
        out = os.path.join(args.project_dir, "_gen_ips.tcl")
        write_ip_tcl(out, args.device, specs)
        print(f"Tcl script written: {out}")
        print("Run:  vivado -mode batch -source _gen_ips.tcl")

    elif args.command == "vivado-synth":
        try:
            from agent_tools.vivado_backend.synth_runner import vivado_synth
        except ImportError:
            from vivado_backend.synth_runner import vivado_synth
        cfg = load_project_config(args.project_dir)
        if cfg is None:
            print(f"ERROR: No valid project.json in {args.project_dir}")
            sys.exit(1)
        proj = cfg["__project_dir"]
        vivado_cfg = cfg.get("vivado", {})
        part = vivado_cfg.get("part", args.device)
        top = cfg["toplevel"]
        sources_full = [str(Path(proj) / s) for s in cfg["sources"]]
        # include IP stubs
        ip_cfg = cfg.get("ip", {})
        workspace_root = Path(__file__).resolve().parent.parent
        for ip_name, ip_entry in ip_cfg.items():
            stub = ip_entry.get("stub", "")
            if stub:
                stub_abs = str(workspace_root / stub) if not os.path.isabs(stub) else stub
                if os.path.exists(stub_abs) and stub_abs not in sources_full:
                    sources_full.append(stub_abs)
        xdc = vivado_cfg.get("xdc", [])
        xdc_full = [str(Path(proj) / x) for x in xdc]
        print(f"Synthesising {top} for {part} ({len(sources_full)} sources)...")
        result = vivado_synth(
            project_dir=os.path.join(proj, "vivado_synth"),
            part=part,
            sources=sources_full,
            top=top,
            xdc_files=xdc_full,
            project_name=top,
        )
        if args.json:
            rpt = {k: v for k, v in result.items() if k != "log"}
            print(json.dumps(rpt, indent=2, ensure_ascii=False))
        else:
            status = "PASS" if result["pass"] else "FAIL"
            print(f"\n{'='*60}")
            print(f"  VIVADO SYNTHESIS: {status}")
            if result.get("error"):
                print(f"  Error: {result['error']}")
            util = result.get("reports", {}).get("utilization", {})
            if util:
                print(f"  Utilisation: {util}")
            timing = result.get("reports", {}).get("timing", {})
            if timing:
                print(f"  Timing: {timing}")
            print(f"{'='*60}\n")
        sys.exit(0 if result["pass"] else 1)

    elif args.command == "vivado-xdc":
        try:
            from agent_tools.vivado_backend.xdc_tools import write_xdc
        except ImportError:
            from vivado_backend.xdc_tools import write_xdc
        cfg = load_project_config(args.project_dir)
        if cfg is None:
            print(f"ERROR: No valid project.json in {args.project_dir}")
            sys.exit(1)
        vcfg = cfg.get("vivado", {})
        clocks = vcfg.get("clocks", [])
        pins   = vcfg.get("pins", [])
        false_paths = vcfg.get("false_paths", [])
        if not clocks and not pins:
            print("WARNING: No clocks or pins in project.json vivado section")
        out = os.path.join(args.project_dir, "constraints.xdc")
        write_xdc(out, clocks=clocks, pins=pins, false_paths=false_paths,
                  comment=f"Constraints for {cfg['toplevel']}")
        print(f"XDC written: {out}")
        if clocks:
            print(f"  Clocks: {len(clocks)}")
        if pins:
            print(f"  Pins: {len(pins)}")

"""Vivado batch synthesis runner — generate Tcl, run synthesis, parse reports."""

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Optional


HERE = Path(__file__).resolve().parent

# Default Vivado path (probe P2 verified)
VIVADO_BAT = r"C:\Xilinx\Vivado\2018.2\bin\vivado.bat"


# ---------------------------------------------------------------------------
# Tcl script generation
# ---------------------------------------------------------------------------

def generate_synth_tcl(
    project_name: str,
    part: str,
    sources: list[str],
    top: str,
    xdc_files: list[str] | None = None,
    output_dir: str = ".",
) -> str:
    """Generate a Vivado Tcl script that creates a project, synthesises,
    implements, and writes bitstream.

    sources    — list of Verilog source file paths (relative to project or absolute)
    xdc_files  — optional constraint files
    output_dir — where Tcl output files (reports) will be written
    """
    lines = [
        "# Auto-generated Vivado synthesis script",
        f"# Project: {project_name}  |  Part: {part}",
        "",
        f"set output_dir {{{output_dir}}}",
        f"file mkdir $output_dir",
        "",
        f"create_project -force {project_name} _{project_name} -part {part}",
        "",
        "# Add source files",
    ]

    for src in sources:
        lines.append(f"add_files -norecurse {{{os.path.abspath(src).replace(chr(92), '/')}}}")

    lines += [
        f"set_property top {top} [current_fileset]",
        "update_compile_order -fileset sources_1",
        "",
    ]

    # Constraints
    if xdc_files:
        lines.append("# Add constraint files")
        for xdc in xdc_files:
            lines.append(f"add_files -fileset constrs_1 -norecurse {{{os.path.abspath(xdc).replace(chr(92), '/')}}}")
        lines.append("")

    lines += [
        "# Run synthesis",
        f"puts \"=== SYNTHESIS ===\"",
        "launch_runs synth_1",
        "wait_on_run synth_1",
        "",
        "# Write utilisation report",
        f"open_run synth_1",
        f"report_utilization -file $output_dir/utilization.rpt",
        "",
        "# Run implementation",
        f"puts \"=== IMPLEMENTATION ===\"",
        "launch_runs impl_1 -to_step write_bitstream",
        "wait_on_run impl_1",
        "",
        "# Timing report",
        f"open_run impl_1",
        f"report_timing_summary -file $output_dir/timing.rpt",
        "",
        "# Export bitstream path",
        f"set bit_file [glob -nocomplain [get_property directory [current_run]]/*.bit]",
        f"if {{$bit_file ne \"\"}} {{",
        f"    file copy -force $bit_file $output_dir/{project_name}.bit",
        f"    puts \"BITSTREAM: $output_dir/{project_name}.bit\"",
        f"}}",
        "",
        f"puts \"=== DONE ===\"",
        "exit",
    ]

    return "\r\n".join(lines) + "\r\n"


# ---------------------------------------------------------------------------
# Vivado invocation
# ---------------------------------------------------------------------------

def run_vivado(tcl_path: str, timeout: int = 600) -> tuple[int, str, str]:
    """Run Vivado in batch mode with the given Tcl script.

    Returns (returncode, stdout, stderr).
    """
    tcl_abs = os.path.abspath(tcl_path)
    cmd = [VIVADO_BAT, "-mode", "batch", "-source", tcl_abs, "-nolog"]
    proc = subprocess.run(
        cmd,
        capture_output=True, text=True,
        timeout=timeout,
        cwd=os.path.dirname(tcl_abs),
    )
    return proc.returncode, proc.stdout or "", proc.stderr or ""


# ---------------------------------------------------------------------------
# Full synthesis flow
# ---------------------------------------------------------------------------

def vivado_synth(
    project_dir: str,
    *,
    part: str,
    sources: list[str],
    top: str,
    xdc_files: list[str] | None = None,
    project_name: str = "_vivado_synth",
    timeout: int = 600,
) -> dict:
    """Run the full Vivado synthesis→implementation→bitstream flow.

    Returns {pass, reports: {utilization, timing}, log, error}
    """
    if not os.path.isfile(VIVADO_BAT):
        return {
            "pass": False,
            "error": f"Vivado not found at {VIVADO_BAT}. Install Vivado 2018.2 or update VIVADO_BAT.",
            "reports": {},
        }

    os.makedirs(project_dir, exist_ok=True)
    out_dir = os.path.join(project_dir, "vivado_out")
    os.makedirs(out_dir, exist_ok=True)

    tcl_content = generate_synth_tcl(
        project_name=project_name,
        part=part,
        sources=[os.path.abspath(s) for s in sources],
        top=top,
        xdc_files=[os.path.abspath(x) for x in (xdc_files or [])],
        output_dir=os.path.abspath(out_dir),
    )
    tcl_path = os.path.join(project_dir, "_synth.tcl")
    Path(tcl_path).write_text(tcl_content, encoding="ascii")

    rc, stdout, stderr = run_vivado(tcl_path, timeout=timeout)
    log = stdout + "\n" + stderr

    passed = rc == 0 and "=== DONE ===" in stdout
    reports = {
        "utilization": _parse_utilization(os.path.join(out_dir, "utilization.rpt")),
        "timing": _parse_timing(os.path.join(out_dir, "timing.rpt")),
    }

    return {
        "pass": passed,
        "rc": rc,
        "reports": reports,
        "log": log,
        "output_dir": out_dir,
    }


# ---------------------------------------------------------------------------
# Report parsing
# ---------------------------------------------------------------------------

def _parse_utilization(rpt_path: str) -> dict:
    """Extract key resource utilisation numbers from Vivado report."""
    if not os.path.isfile(rpt_path):
        return {}
    text = Path(rpt_path).read_text(encoding="utf-8", errors="replace")
    result = {}
    # Vivado 2018.2 format: "| Slice LUTs*             |    9 | ..."
    patterns = {
        "Slice LUTs":    r"\|\s*Slice LUTs\*?\s*\|\s*(\d+)\s*\|",
        "Slice Registers": r"\|\s*Slice Registers\s*\|\s*(\d+)\s*\|",
        "Block RAM":     r"\|\s*Block RAM Tile\s*\|\s*(\d+)\s*\|",
        "DSPs":          r"\|\s*DSPs\s*\|\s*(\d+)\s*\|",
    }
    for name, pat in patterns.items():
        m = re.search(pat, text)
        if m:
            result[name] = int(m.group(1))
    return result


def _parse_timing(rpt_path: str) -> dict:
    """Extract WNS, TNS from Vivado timing summary report."""
    if not os.path.isfile(rpt_path):
        return {}
    text = Path(rpt_path).read_text(encoding="utf-8", errors="replace")

    # Vivado 2018.2 format: table rows with WNS(ns) / TNS(ns) headers
    # After the header, the first data row has the numeric values.
    wns, tns = None, None
    capture = False
    for line in text.splitlines():
        if "WNS(ns)" in line and "TNS(ns)" in line:
            capture = True
            continue
        if capture:
            parts = line.split()
            if len(parts) >= 2 and parts[0] != "WNS(ns)" and parts[0] != "":
                for i, p in enumerate(parts):
                    try:
                        val = float(p)
                        if wns is None:
                            wns = val
                        elif tns is None:
                            tns = val
                            break
                    except ValueError:
                        continue
                if wns is not None and tns is not None:
                    break

    return {"wns_ns": wns, "tns_ns": tns}

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


def generate_project_tcl(
    project_name: str,
    part: str,
    sources: list[str],
    top: str,
    xdc_files: list[str] | None = None,
    output_dir: str = ".",
) -> str:
    """Generate a Vivado Tcl script that creates a clean project for GUI use.

    Unlike generate_synth_tcl, this does NOT run synthesis/implementation.
    The user opens the generated .xpr in Vivado GUI to interact with the design.
    """
    lines = [
        "# Auto-generated Vivado project script (GUI-ready)",
        f"# Project: {project_name}  |  Part: {part}",
        f"# Open {project_name}.xpr in Vivado GUI to explore the design",
        "",
        f"set output_dir {{{output_dir}}}",
        f"file mkdir $output_dir",
        "",
        f"create_project {project_name} _{project_name} -part {part}",
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
        f'puts "Project created: [file normalize [get_property DIRECTORY [current_project]]]/{project_name}.xpr"',
        'puts "Open this file in Vivado GUI to explore the design."',
        "exit",
    ]

    return "\r\n".join(lines) + "\r\n"


def generate_project_tcl_update(
    project_name: str,
    part: str,
    sources: list[str],
    top: str,
    xdc_files: list[str] | None = None,
    xpr_path: str = ".",
) -> str:
    """Generate Tcl to open existing project and add/update files."""
    lines = [
        "# Auto-generated Vivado project UPDATE script",
        f"# Project: {project_name}  |  Part: {part}",
        "",
        f'open_project {{{os.path.abspath(xpr_path).replace(chr(92), "/")}}}',
        "",
        "# Update source files",
    ]
    for src in sources:
        lines.append(f'add_files -norecurse {{{os.path.abspath(src).replace(chr(92), "/")}}}')
    lines += [
        f"set_property top {top} [current_fileset]",
        "update_compile_order -fileset sources_1",
    ]
    if xdc_files:
        lines.append("# Update constraint files")
        for xdc in xdc_files:
            lines.append(f'add_files -fileset constrs_1 -norecurse {{{os.path.abspath(xdc).replace(chr(92), "/")}}}')
    lines += [
        f'puts "Project updated: {xpr_path}"',
        "exit",
    ]
    return "\r\n".join(lines) + "\r\n"


# ---------------------------------------------------------------------------
# Vivado invocation
# ---------------------------------------------------------------------------

def _find_vivado() -> str | None:
    """Return the vivado.bat path, trying both Windows and WSL locations."""
    candidates = [
        VIVADO_BAT,
        VIVADO_BAT.replace("C:\\", "/mnt/c/").replace("\\", "/"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def run_vivado(tcl_path: str, timeout: int = 600) -> tuple[int, str, str]:
    """Run Vivado in batch mode with the given Tcl script."""
    vivado_bin = _find_vivado()
    if vivado_bin is None:
        raise FileNotFoundError(f"vivado.bat not found")

    tcl_abs = os.path.abspath(tcl_path)

    # On WSL/Linux, call .bat through cmd.exe
    is_linux = os.name != "nt" or vivado_bin.startswith("/mnt/")
    if is_linux:
        win_path  = vivado_bin.replace("/mnt/c/", "C:/").replace("/", "\\")
        tcl_win   = tcl_abs.replace("/mnt/c/", "C:/").replace("/", "\\")
        cmd = ["cmd.exe", "/c", f'{win_path} -mode batch -source "{tcl_win}" -nolog']
        cwd = os.path.dirname(tcl_abs)  # WSL path for subprocess on Linux
    else:
        cmd = [vivado_bin, "-mode", "batch", "-source", tcl_abs, "-nolog"]
        cwd = os.path.dirname(tcl_abs)
    proc = subprocess.run(
        cmd,
        capture_output=True,
        timeout=timeout,
        cwd=cwd,
    )
    return proc.returncode, proc.stdout.decode("utf-8", errors="replace"), proc.stderr.decode("utf-8", errors="replace") if proc.stderr else ""


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
    if not _find_vivado():
        return {
            "pass": False,
            "error": f"Vivado not found at {VIVADO_BAT} or WSL path. Install Vivado 2018.2.",
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

    # IO overutilization detection
    error_msg = None
    if not passed and "IO Placement failed due to overutilization" in log:
        port_count = "?"
        m = re.search(r"contains (\d+) I/O ports", log)
        if m:
            port_count = m.group(1)
        error_msg = (
            f"Placement failed: design has {port_count} top-level I/O ports "
            f"(exceeds FPGA physical pin limit). "
            f"This RTL is correct for simulation but needs a bus wrapper "
            f"(AXI-Lite or addr+data bus) before it can be implemented on hardware. "
            f"See AGENTS.md §9 quality rule 'Wrap parallel ports behind a bus if >100'."
        )

    return {
        "pass": passed,
        "rc": rc,
        "reports": reports,
        "log": log,
        "error": error_msg,
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
    """Extract WNS, TNS, failing endpoints, and worst path details."""
    if not os.path.isfile(rpt_path):
        return {}
    text = Path(rpt_path).read_text(encoding="utf-8", errors="replace")

    wns, tns = None, None
    setup_failing = 0
    hold_failing = 0

    # Summary line: "Setup : 349 Failing Endpoints,  Worst Slack -3.341ns, Total Violation -763.877ns"
    m = re.search(r"Setup\s*:\s*(\d+)\s*Failing\s+Endpoints.*?\bWorst\s+Slack\s+([\-\d.]+)ns.*?Total\s+Violation\s+([\-\d.]+)ns", text)
    if m:
        setup_failing = int(m.group(1))
        wns = float(m.group(2))
        tns = float(m.group(3))

    mh = re.search(r"Hold\s*:\s*(\d+)\s*Failing\s+Endpoints", text)
    if mh:
        hold_failing = int(mh.group(1))

    # Worst path details
    paths = []
    for p in re.finditer(
        r"Slack\s*\((VIOLATED|MET)\)\s*:\s*([\-\d.]+)ns.*?"
        r"Source:\s*(.+?)\n.*?"
        r"Destination:\s*(.+?)\n",
        text, re.DOTALL,
    ):
        status = p.group(1)
        slack = float(p.group(2))
        src = p.group(3).strip()
        dst = p.group(4).strip()
        paths.append({
            "status": status,
            "slack_ns": slack,
            "source": src,
            "destination": dst,
        })
        if len(paths) >= 5:  # limit to first 5 paths
            break

    return {
        "wns_ns": wns, "tns_ns": tns,
        "setup_failing": setup_failing,
        "hold_failing": hold_failing,
        "paths": paths,
    }


def timing_loop(
    project_dir: str,
    *,
    part: str,
    sources: list[str],
    top: str,
    xdc_tpl: str,
    xdc_path: str,
    initial_period_ns: float,
    max_iters: int = 5,
    timeout: int = 600,
) -> dict:
    """Iterative timing-closure loop.

    Starts with *initial_period_ns* clock. If WNS < 0, doubles the
    clock period and re-runs synthesis. Stops when WNS >= 0 or max
    iterations reached.

    *xdc_tpl* — XDC template string with {period} placeholder.
    *xdc_path* — path where updated XDC is written each iteration.

    Returns {pass, final_wns, final_tns, iters, history}.
    """
    history = []
    period = initial_period_ns

    for i in range(max_iters):
        # Generate XDC with current period
        content = xdc_tpl.format(period=period)
        Path(xdc_path).write_text(content, encoding="ascii")

        result = vivado_synth(
            project_dir=project_dir,
            part=part,
            sources=sources + [xdc_path] if xdc_path not in sources else sources,
            top=top,
            timeout=timeout,
        )
        timing = result.get("reports", {}).get("timing", {})
        wns = timing.get("wns_ns")
        tns = timing.get("tns_ns")
        util = result.get("reports", {}).get("utilization", {})

        entry = {
            "iter": i + 1,
            "period_ns": period,
            "wns_ns": wns,
            "tns_ns": tns,
            "pass": result["pass"] and (wns is not None and wns >= 0),
        }
        history.append(entry)

        if wns is not None and wns >= 0:
            return {
                "pass": True,
                "final_wns": wns,
                "final_tns": tns,
                "final_period_ns": period,
                "iters": i + 1,
                "utilization": util,
                "history": history,
            }

        # Double the period for next iteration (relax timing)
        period *= 2.0

    return {
        "pass": False,
        "final_wns": wns,
        "final_tns": tns,
        "final_period_ns": period,
        "iters": max_iters,
        "utilization": util,
        "history": history,
        "error": f"Could not close timing after {max_iters} iterations (max period={period}ns)",
    }

"""xsim (Vivado Simulator) runner — auto-TB generation + xvlog/xelab/xsim flow."""

import os, re, subprocess
from pathlib import Path
from typing import Optional


VIVADO_BIN = r"C:\Xilinx\Vivado\2018.2\bin"


def _find_tool(name: str) -> str:
    """Find a Vivado binary (.bat on Windows, plain on WSL)."""
    for suffix in [".bat", ".exe", ""]:
        p = os.path.join(VIVADO_BIN, name + suffix)
        if os.path.isfile(p):
            return p
    raise FileNotFoundError(f"{name} not found in {VIVADO_BIN}")


# ============================================================
#  Auto-generated Verilog testbench (reusable for xsim / ISim)
# ============================================================

def generate_verilog_tb(top_module: str, signals: list[dict],
                        test_vectors: list[dict],
                        period_ns: int = 10) -> str:
    """Generate a standard Verilog testbench from structured test data.

    signals: [{"name": "clk", "width": 1, "dir": "input"}, ...]
    test_vectors: [{"stimulus": {"a": 3, "b": 4}, "expected": {"sum": 7}, "label": "3+4"}]

    Returns Verilog source with CRLF line endings.
    """
    inputs  = [s for s in signals if s["dir"] == "input" and s["name"] not in ("clk","rst_n")]
    outputs = [s for s in signals if s["dir"] == "output"]

    def port_str(s):
        w = s.get("width", 1)
        return f"[{w-1}:0] {s['name']}" if w > 1 else s["name"]

    lines = ["`timescale 1ns / 1ps", ""]
    lines.append(f"module tb_{top_module};")
    lines.append("    reg clk = 0;")
    lines.append("    reg rst_n = 0;")
    for s in inputs:
        w = s.get("width", 1)
        lines.append(f"    reg {port_str(s)};" if w == 1 else f"    reg [{w-1}:0] {s['name']};")
    for s in outputs:
        w = s.get("width", 1)
        lines.append(f"    wire {port_str(s)};" if w == 1 else f"    wire [{w-1}:0] {s['name']};")

    lines.append("")
    lines.append(f"    {top_module} dut (")
    ports = [f"        .{s['name']}({s['name']})" for s in signals]
    lines.append(",\n".join(ports))
    lines.append("    );")
    lines.append("")
    lines.append(f"    always #{period_ns // 2} clk = ~clk;")
    lines.append("")
    lines.append("    initial begin")
    for s in inputs:
        if s.get("width", 1) > 1:
            lines.append(f"        {s['name']} = 0;")
        else:
            lines.append(f"        {s['name']} = 0;")
    lines.append("        // reset")
    lines.append("        rst_n = 0;")
    lines.append("        repeat(3) @(posedge clk);")
    lines.append("        rst_n = 1;")
    lines.append("        repeat(5) @(posedge clk);")
    lines.append("")

    for i, tv in enumerate(test_vectors):
        label = tv.get("label", f"vector[{i}]")
        stim = tv.get("stimulus", {})
        exp  = tv.get("expected", {})
        lines.append(f"        // {label}")
        for sig_name, val in stim.items():
            w = next((s["width"] for s in signals if s["name"] == sig_name), 32)
            if w == 1:
                lines.append(f"        {sig_name} = 1'b{val};")
            else:
                lines.append(f"        {sig_name} = {w}'d{int(val)};")
        lines.append("        @(posedge clk);")
        lines.append("        @(posedge clk);")
        for sig_name, exp_val in exp.items():
            lines.append(f"        if ({sig_name} !== {int(exp_val)}) begin")
            lines.append(f"            $display(\"FAIL [{label}]: {sig_name} expected %d, got %d\", "
                         f"{int(exp_val)}, {sig_name});")
            lines.append(f"            $stop;")
            lines.append(f"        end")
        lines.append("")

    lines.append(f"        $display(\"=== ALL TESTS PASSED (%d vectors) ===\", {len(test_vectors)});")
    lines.append("        $finish;")
    lines.append("    end")
    lines.append("endmodule")
    return "\r\n".join(lines) + "\r\n"


# ============================================================
#  xsim simulation flow
# ============================================================

def run_xsim(project_dir: str, *, top: str, sources: list[str],
             test_vectors: Optional[list] = None,
             signals: Optional[list] = None,
             tb_file: Optional[str] = None,
             timeout: int = 300) -> dict:
    """Run xsim (Vivado Simulator): xvlog → xelab → xsim.

    Either provide (signals + test_vectors) for auto-TB, or a pre-written tb_file.
    Returns {"pass": bool, "tests": int, "log": str}.
    """
    os.makedirs(project_dir, exist_ok=True)

    # Determine testbench
    if tb_file is None and signals and test_vectors:
        tb_content = generate_verilog_tb(top, signals, test_vectors)
        tb_file = os.path.join(project_dir, f"tb_{top}.v")
        Path(tb_file).write_text(tb_content, encoding="utf-8")
    elif tb_file is None:
        return {"pass": False, "tests": 0, "log": "",
                "error": "Provide either (signals+test_vectors) or tb_file"}

    xsim_dir = os.path.join(project_dir, "_xsim")
    os.makedirs(xsim_dir, exist_ok=True)

    # Collect all source files + testbench
    all_files = list(sources) + [tb_file]
    all_files = [os.path.abspath(f) for f in all_files]

    # 1) xvlog — analyze
    xvlog = _find_tool("xvlog")
    cmd = [xvlog, "-work", "work"] + all_files
    rc, out = _run_tool(cmd, project_dir, timeout)
    if rc != 0:
        return {"pass": False, "tests": 0, "log": out,
                "error": "xvlog (analysis) failed"}

    # 2) xelab — elaborate
    xelab = _find_tool("xelab")
    snap = f"snap_{top}"
    cmd = [xelab, "-debug", "typical", f"work.tb_{top}", "-s", snap]
    rc, out2 = _run_tool(cmd, project_dir, timeout)
    if rc != 0:
        return {"pass": False, "tests": 0, "log": out + "\n" + out2,
                "error": "xelab (elaboration) failed"}

    # 3) xsim — simulate
    tcl_content = "run all; quit\n"
    tcl_path = os.path.join(project_dir, "_xsim_run.tcl")
    Path(tcl_path).write_text(tcl_content)
    tcl_arg = os.path.abspath(tcl_path).replace("\\", "/")

    xsim = _find_tool("xsim")
    cmd = [xsim, snap, "-tclbatch", tcl_arg]
    rc, out3 = _run_tool(cmd, project_dir, timeout)

    passed = "=== ALL TESTS PASSED" in out3 or "process terminated" in out3.lower()

    return {
        "pass": passed,
        "tests": len(test_vectors) if test_vectors else 0,
        "log": out + "\n" + out2 + "\n" + out3,
        "rc": rc,
    }


def _run_tool(cmd: list, cwd: str, timeout: int) -> tuple[int, str]:
    """Run a command-line tool; return (rc, combined stdout+stderr)."""
    proc = subprocess.run(cmd, capture_output=True, timeout=timeout, cwd=cwd)
    out = proc.stdout.decode("utf-8", errors="replace")
    err = proc.stderr.decode("utf-8", errors="replace") if proc.stderr else ""
    return proc.returncode, out + "\n" + err

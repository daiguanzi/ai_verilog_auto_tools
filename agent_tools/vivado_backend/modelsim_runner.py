"""ModelSim/Questa simulation runner — vlib → vlog → vsim."""

import os, re, subprocess, time
from pathlib import Path
from typing import Optional


MODELSIM_BIN = r"C:\modeltech64_10.4\win64"


def _find_tool(name: str) -> str:
    """Find a ModelSim binary. Accepts .exe or bare name."""
    for suffix in [".exe", ""]:
        p = os.path.join(MODELSIM_BIN, name + suffix)
        if os.path.isfile(p):
            return p
    raise FileNotFoundError(f"{name} not found in {MODELSIM_BIN}")


def run_modelsim(project_dir: str, *, top: str, sources: list[str],
                 test_vectors: Optional[list] = None,
                 signals: Optional[list] = None,
                 tb_file: Optional[str] = None,
                 timeout: int = 300) -> dict:
    """Run ModelSim: vlib → vlog → vsim.

    Returns {"pass": bool, "tests": int, "elapsed_s": float, "log": str}.
    """
    t0 = time.time()
    os.makedirs(project_dir, exist_ok=True)

    # Determine testbench — reuse xsim_runner's generator
    if tb_file is None and signals and test_vectors:
        try:
            from agent_tools.vivado_backend.xsim_runner import generate_verilog_tb
        except ImportError:
            from vivado_backend.xsim_runner import generate_verilog_tb
        tb_content = generate_verilog_tb(top, signals, test_vectors)
        tb_file = os.path.join(project_dir, f"tb_{top}.v")
        Path(tb_file).write_text(tb_content, encoding="utf-8")
    elif tb_file is None:
        return {"pass": False, "tests": 0, "elapsed_s": 0, "log": "",
                "error": "Provide either (signals+test_vectors) or tb_file"}

    all_files = [os.path.abspath(f) for f in sources] + [os.path.abspath(tb_file)]

    # 1) vlib — create library
    vlib = _find_tool("vlib")
    rc, out = _run_tool([vlib, "work"], project_dir, timeout)
    if rc != 0:
        return {"pass": False, "tests": 0, "elapsed_s": time.time() - t0,
                "log": out, "error": "vlib failed"}

    # 2) vlog — compile
    vlog = _find_tool("vlog")
    cmd = [vlog, "-sv", "-work", "work", "+acc", "-vopt", "-nocovercells"] + all_files
    rc, out2 = _run_tool(cmd, project_dir, timeout)
    if rc != 0:
        return {"pass": False, "tests": 0, "elapsed_s": time.time() - t0,
                "log": out + "\n" + out2, "error": "vlog (compile) failed"}

    # 3) vsim — simulate
    tcl = f"run -all; quit -f\n"
    tcl_name = "run_msim.do"
    tcl_path = os.path.join(project_dir, tcl_name)
    Path(tcl_path).write_text(tcl)

    vsim = _find_tool("vsim")
    cmd = [vsim, "-c", "-do", tcl_name, f"work.tb_{top}"]
    rc, out3 = _run_tool(cmd, project_dir, timeout)

    elapsed = time.time() - t0
    passed = "=== ALL TESTS PASSED" in out3

    return {
        "pass": passed,
        "tests": len(test_vectors) if test_vectors else 0,
        "elapsed_s": round(elapsed, 1),
        "log": out + "\n" + out2 + "\n" + out3,
        "rc": rc,
    }


def _run_tool(cmd: list, cwd: str, timeout: int) -> tuple[int, str]:
    proc = subprocess.run(cmd, capture_output=True, timeout=timeout, cwd=cwd)
    out = proc.stdout.decode("utf-8", errors="replace")
    err = proc.stderr.decode("utf-8", errors="replace") if proc.stderr else ""
    return proc.returncode, out + "\n" + err

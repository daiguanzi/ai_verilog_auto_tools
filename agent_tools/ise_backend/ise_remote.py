"""ISE 14.7 VM backend — VM management, ISE synthesis, ISim simulation.

Uses VirtualBox guestcontrol to run ISE commands inside the Win7-ISE VM.
Credentials in vm_config.json (gitignored).
"""

import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Optional


HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "vm_config.json"


# ---------------------------------------------------------------------------
# VM management
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"VM config not found: {CONFIG_PATH}. Copy vm_config.example.json "
            f"and fill in your VM credentials."
        )
    with open(CONFIG_PATH) as f:
        return json.load(f)


def check_vm_running() -> bool:
    cfg = _load_config()
    proc = subprocess.run(
        [cfg["vbox_manage"], "showvminfo", cfg["vm_name"], "--machinereadable"],
        capture_output=True, text=True, timeout=15,
    )
    for line in (proc.stdout or "").splitlines():
        if "VMState=" in line:
            return line.split("=")[1].strip().strip('"') == "running"
    return False


def start_vm() -> None:
    cfg = _load_config()
    subprocess.run(
        [cfg["vbox_manage"], "startvm", cfg["vm_name"]],
        capture_output=True, text=True, timeout=30,
    )


def ensure_vm_ready() -> None:
    if not check_vm_running():
        start_vm()
        time.sleep(10)  # let Guest Additions load + shared folder mount
    if not check_vm_running():
        raise RuntimeError(
            "ISE VM (Win7-ISE) is not running and could not be started. "
            "Check VirtualBox or start the VM manually."
        )


# ---------------------------------------------------------------------------
# Command execution in VM
# ---------------------------------------------------------------------------

def invoke_ise(command: str, project_dir: Optional[str] = None,
               timeout: int = 300) -> tuple[int, str, str]:
    """Run *command* inside the ISE VM.

    *project_dir* is on the HOST (e.g. C:/FPGA_Projects/myproj);
    the VM sees the shared folder root as Z:.

    Returns (returncode, stdout, stderr).
    """
    cfg = _load_config()
    vm          = cfg["vm_name"]
    username    = cfg["username"]
    password    = cfg["password"]
    host_shared = cfg["host_shared"]
    vm_shared   = cfg["vm_shared"]
    ise_path    = cfg["ise_path"]
    common_bin  = ise_path.replace("ISE_DS\\ISE", "ISE_DS\\common") + "\\bin\\nt64"

    if project_dir:
        # relative path from shared root → VM sees <vm_shared>\<rel>
        rel = os.path.relpath(project_dir, host_shared)
        if rel.startswith(".."):
            raise ValueError(f"project_dir {project_dir} is outside shared folder {host_shared}")
        cd_line = f"cd /d {vm_shared}\\{rel}"
    else:
        cd_line = f"cd /d {vm_shared}"

    bat = (
        f"@echo off\r\n"
        f"set XILINX={ise_path}\r\n"
        f"set PATH={ise_path}\\bin\\nt64;{ise_path}\\lib\\nt64;{common_bin};%PATH%\r\n"
        f"{cd_line}\r\n"
        f"{command}\r\n"
    )

    bat_host = os.path.join(host_shared, "_ise_cmd.bat")
    Path(bat_host).write_text(bat, encoding="ascii")

    proc = subprocess.run([
        cfg["vbox_manage"], "guestcontrol", vm, "run",
        "--username", username, "--password", password,
        "--wait-stdout",
        "--exe", "C:\\Windows\\System32\\cmd.exe",
        "--", "cmd", "/c", f"{vm_shared}\\_ise_cmd.bat",
    ], capture_output=True, text=True, timeout=timeout)

    return proc.returncode, proc.stdout or "", proc.stderr or ""


# ---------------------------------------------------------------------------
# ISE synthesis flow
# ---------------------------------------------------------------------------

def generate_prj(sources: list[str], library: str = "work") -> str:
    """Generate an XST .prj file content from a source-file list."""
    return "\r\n".join(f"verilog {library} {s}" for s in sources) + "\r\n"


def generate_xst(top: str, prj_file: str, device: str,
                 opt_mode: str = "Speed", opt_level: int = 1) -> str:
    """Generate an XST script (.xst) content."""
    return "\r\n".join([
        "run",
        f"-ifn {prj_file}",
        f"-ofn {top}.ngc",
        f"-p {device}",
        f"-top {top}",
        f"-opt_mode {opt_mode}",
        f"-opt_level {opt_level}",
        "",
    ])


def ise_synth(project_dir: str, *, top: str, device: str,
              sources: list[str], ucf: Optional[str] = None,
              opt_mode: str = "Speed", opt_level: int = 1) -> dict:
    """Run the full ISE synthesis → place & route → bitgen flow.

    Returns {"pass": bool, "reports": {...}, "log": str}
    """
    ensure_vm_ready()

    os.makedirs(project_dir, exist_ok=True)
    prj_content = generate_prj(sources)
    prj_path = os.path.join(project_dir, f"{top}.prj")
    Path(prj_path).write_text(prj_content)

    xst_content = generate_xst(top, f"{top}.prj", device, opt_mode, opt_level)
    xst_path = os.path.join(project_dir, f"{top}.xst")
    Path(xst_path).write_text(xst_content)

    logs = []
    results = {"pass": True, "reports": {}, "steps": {}}

    # 1) Synthesis
    rc, out, err = invoke_ise(f"xst -ifn {top}.xst -ofn {top}.ngc", project_dir)
    logs.append(out)
    steps_ok = rc == 0
    if not steps_ok:
        results["pass"] = False
        results["error"] = "xst synthesis failed"
    results["steps"]["xst"] = {"ok": steps_ok, "rc": rc}

    # 2) Translate
    if results["pass"]:
        rc, out, err = invoke_ise(
            f"ngdbuild {top}.ngc -p {device}", project_dir)
        logs.append(out)
        steps_ok = rc == 0
        results["steps"]["ngdbuild"] = {"ok": steps_ok, "rc": rc}
        if not steps_ok:
            results["pass"] = False

    # 3) Map
    if results["pass"]:
        rc, out, err = invoke_ise(f"map {top}.ngd", project_dir)
        logs.append(out)
        results["steps"]["map"] = {"ok": rc == 0, "rc": rc}
        if rc != 0:
            results["pass"] = False

    # 4) Place & route
    if results["pass"]:
        rc, out, err = invoke_ise(
            f"par {top}.ncd {top}_par.ncd", project_dir)
        logs.append(out)
        results["steps"]["par"] = {"ok": rc == 0, "rc": rc}
        if rc != 0:
            results["pass"] = False

    # 5) Bitgen
    if results["pass"]:
        rc, out, err = invoke_ise(
            f"bitgen {top}_par.ncd", project_dir)
        logs.append(out)
        results["steps"]["bitgen"] = {"ok": rc == 0, "rc": rc}

    results["log"] = "\n---\n".join(logs)

    # Parse reports
    srp = os.path.join(project_dir, f"{top}.srp")
    if os.path.exists(srp):
        results["reports"]["xst"] = parse_xst_report(srp)

    # Timing
    twr = os.path.join(project_dir, f"{top}.twr")
    if os.path.exists(twr):
        results["reports"]["timing"] = parse_timing(twr)

    return results


# ---------------------------------------------------------------------------
# ISim simulation flow
# ---------------------------------------------------------------------------

def generate_isim_prj(sources: list[str], tb_file: str,
                      library: str = "work") -> str:
    """Generate an ISim .prj file (synth + tb sources)."""
    lines = [f"verilog {library} {s}" for s in sources]
    lines.append(f"verilog {library} {tb_file}")
    return "\r\n".join(lines) + "\r\n"


def generate_isim_tb(top_module: str, signals: list[dict],
                     test_vectors: list[dict],
                     period_ns: int = 10,
                     timescale: str = "1ns / 1ps") -> str:
    """Auto-generate a Verilog testbench from structured test data.

    signals: list of {"name": str, "width": int, "dir": "input"|"output"}
    test_vectors: list of {
        "stimulus": {signal_name: value},
        "expected": {signal_name: value},
        "label": str (optional, used in pass/fail message)
    }
    period_ns: clock half-period in ns.

    Returns Verilog source as a string.
    """
    # collect inputs and outputs
    inputs = [s for s in signals if s["dir"] == "input"]
    outputs = [s for s in signals if s["dir"] == "output"]

    def decl(sig):
        w = sig.get("width", 1)
        port = sig["name"]
        if w == 1:
            return f"    reg {port};"
        return f"    reg [{w - 1}:0] {port};"

    def wire_decl(sig):
        w = sig.get("width", 1)
        port = sig["name"]
        if w == 1:
            return f"    wire {port};"
        return f"    wire [{w - 1}:0] {port};"

    lines = [
        f"`timescale {timescale}",
        "",
        f"module tb_{top_module};",
        "",
        "    // inputs (driven by testbench)",
    ]
    lines.extend(decl(s) for s in inputs if s["name"] not in ("clk", "rst_n"))
    lines.append("    reg clk = 0;")
    lines.append("    reg rst_n = 0;")
    lines.append("")
    lines.append("    // outputs (from DUT)")
    lines.extend(wire_decl(s) for s in outputs)
    lines.append("")
    lines.append(f"    // DUT instantiation")
    lines.append(f"    {top_module} dut (")
    ports = []
    for s in signals:
        ports.append(f"        .{s['name']}({s['name']})")
    lines.append(",\n".join(ports))
    lines.append("    );")
    lines.append(f"")
    lines.append(f"    always #{period_ns // 2} clk = ~clk;")
    lines.append(f"")
    lines.append(f"    initial begin")
    for s in inputs:
        if s["name"] not in ("clk",):
            lines.append(f"        {s['name']} = 0;")
    lines.append(f"        // reset")
    lines.append(f"        rst_n = 0;")
    lines.append(f"        repeat(3) @(posedge clk);")
    lines.append(f"        rst_n = 1;")
    lines.append(f"        repeat(5) @(posedge clk);")
    lines.append(f"")

    for i, tv in enumerate(test_vectors):
        label = tv.get("label", f"vector[{i}]")
        stimulus = tv.get("stimulus", {})
        expected = tv.get("expected", {})
        lines.append(f"        // {label}")
        for sig_name, val in stimulus.items():
            # convert to Verilog literal
            w = next((s["width"] for s in signals if s["name"] == sig_name), 32)
            if w == 1:
                lines.append(f"        {sig_name} = 1'b{val};")
            else:
                lines.append(f"        {sig_name} = {w}'d{int(val)};")
        lines.append(f"        @(posedge clk);")
        lines.append(f"        @(posedge clk);")
        for sig_name, exp_val in expected.items():
            lines.append(f"        if ({sig_name} !== {int(exp_val)}) begin")
            lines.append(f"            $display(\"FAIL [{label}]: {sig_name} expected %d, got %d\", "
                         f"{int(exp_val)}, {sig_name});")
            lines.append(f"            $stop;")
            lines.append(f"        end")
        lines.append(f"")

    lines.append(f"        $display(\"=== ALL TESTS PASSED (%d vectors) ===\", {len(test_vectors)});")
    lines.append(f"        $finish;")
    lines.append(f"    end")
    lines.append(f"")
    lines.append(f"endmodule")
    lines.append("")

    return "\r\n".join(lines) + "\r\n"


def ise_sim(project_dir: str, *, top: str, sources: list[str],
            test_vectors: Optional[list[dict]] = None,
            signals: Optional[list[dict]] = None,
            tb_file: Optional[str] = None,
            tb_module: Optional[str] = None) -> dict:
    """Run ISim simulation.

    If *test_vectors* + *signals* are given, an auto-generated Verilog
    testbench is created (module name: tb_{top}).
    If *tb_file* is given, uses that existing testbench. If *tb_module*
    is not specified, the module name is derived from the file stem (e.g.
    'fifo_tb.v' → 'fifo_tb').

    Returns {"pass": bool, "tests": int, "failures": list, "log": str}
    """
    ensure_vm_ready()

    os.makedirs(project_dir, exist_ok=True)

    # Determine tb source
    if test_vectors is not None and signals is not None:
        tb_name = f"tb_{top}.v"
        tb_content = generate_isim_tb(top, signals, test_vectors)
        tb_path = os.path.join(project_dir, tb_name)
        Path(tb_path).write_text(tb_content, encoding="utf-8")
        tb_mod = f"tb_{top}"
    elif tb_file is not None:
        tb_name = os.path.basename(tb_file)
        tb_mod = tb_module or Path(tb_file).stem
    else:
        raise ValueError("Provide either (test_vectors+signals) or tb_file.")

    # ISim .prj
    prj_content = generate_isim_prj(sources, tb_name)
    prj_name = f"{top}_tb.prj"
    prj_path = os.path.join(project_dir, prj_name)
    Path(prj_path).write_text(prj_content, encoding="utf-8")

    exe_name = f"{top}_tb.exe"

    # fuse (compile)
    rc, out, err = invoke_ise(
        f"fuse -intstyle ise -incremental -lib unisims_ver -lib unimacro_ver "
        f"-o {exe_name} -prj {prj_name} work.{tb_mod}",
        project_dir, timeout=300)
    if rc != 0:
        return {"pass": False, "tests": 0, "failures": [], "log": out + err,
                "error": "ISim fuse (compile) failed"}

    # write sim control Tcl
    tcl_content = "run 5000ns;\nquit;\n"
    tcl_path = os.path.join(project_dir, "isim_cmd.tcl")
    Path(tcl_path).write_text(tcl_content, encoding="ascii")

    # run simulation
    rc, out, err = invoke_ise(
        f"{exe_name} -tclbatch isim_cmd.tcl",
        project_dir, timeout=300)

    parsed = parse_isim_output(out)
    parsed["log"] = out + err
    return parsed


# ---------------------------------------------------------------------------
# Report parsing
# ---------------------------------------------------------------------------

def parse_xst_report(srp_path: str) -> dict:
    """Extract errors/warnings/resources from ISE synthesis report."""
    try:
        text = Path(srp_path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {"errors": [], "warnings": [], "resources": {}}

    errors = [l.strip() for l in text.splitlines() if "ERROR:" in l]
    warnings = [l.strip() for l in text.splitlines() if "WARNING:" in l]

    # rough resource extraction
    slices = ""
    luts = ""
    for line in text.splitlines():
        if "Number of Slice" in line:
            slices = line.strip()
        if "Number of 4 input LUTs" in line or "Number of LUTs" in line:
            luts = line.strip()

    return {
        "errors": errors, "warnings": warnings,
        "resources": {"slices": slices, "luts": luts},
        "error_count": len(errors), "warning_count": len(warnings),
    }


def parse_timing(twr_path: str) -> dict:
    """Extract max frequency / critical path from timing report."""
    try:
        text = Path(twr_path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {"max_freq_mhz": None}

    freq = None
    for line in text.splitlines():
        m = re.search(r"Maximum frequency:\s*([\d.]+)\s*MHz", line, re.I)
        if m:
            freq = float(m.group(1))
            break
    return {"max_freq_mhz": freq}


def parse_isim_output(text: str) -> dict:
    """Parse ISim console output for PASS / FAIL assertions."""
    passed = ("=== ALL TESTS PASSED" in text or "=== PASS ===" in text
              or "Simulation complete" in text)
    fails = [l.strip() for l in text.splitlines()
             if "FAIL" in l and "PASS" not in l and "# break" not in l]
    vector_match = re.search(r"ALL TESTS PASSED\s*\(\s*(\d+)\s*vectors\)", text)
    vectors = int(vector_match.group(1)) if vector_match else 0
    if not passed and not fails:
        passed = True  # no explicit fail = assume pass

    return {
        "pass": passed and len(fails) == 0,
        "tests": vectors,
        "failures": fails,
    }

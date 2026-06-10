import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def run_simulation(
    sources: list[str],
    hdl_toplevel: str,
    test_module: str,
    *,
    test_dir: str | None = None,
    build_dir: str = "sim_build",
    sim: str = "verilator",
    waves: bool = False,
    compile_args: list[str] | None = None,
    sim_args: list[str] | None = None,
) -> dict:
    sources_abs = [str(Path(s).resolve()) for s in sources]
    build_path = Path(build_dir).resolve()

    if test_dir is None:
        test_dir_path = Path.cwd()
    else:
        test_dir_path = Path(test_dir).resolve()

    try:
        from cocotb_tools.runner import get_runner
    except ImportError:
        return _error("cocotb_tools not found. Run: pip install cocotb")

    runner = get_runner(sim)

    try:
        runner.build(
            hdl_toplevel=hdl_toplevel,
            sources=sources_abs,
            build_dir=str(build_path),
            build_args=compile_args or [],
        )
    except Exception as e:
        return _error(f"Build failed: {str(e)[:500]}")

    results_xml = build_path / "results.xml"
    log_file = build_path / "sim.log"

    try:
        proc = runner.test(
            hdl_toplevel=hdl_toplevel,
            test_module=test_module,
            hdl_toplevel_library="work",
            results_xml=str(results_xml),
            test_dir=str(test_dir_path),
            log_file=str(log_file),
            waves=waves,
            test_args=sim_args or [],
        )
    except Exception as e:
        return _error(f"Simulation error: {str(e)[:500]}")

    raw_log = ""
    if log_file.exists():
        raw_log = log_file.read_text(encoding="utf-8", errors="replace")

    if results_xml.exists():
        parsed = _parse_results_xml(results_xml)
        if parsed["tests_total"] == 0:
            parsed["pass"] = False
            parsed["error"] = "No tests discovered. Check that test_module name and test_dir are correct."
        parsed["raw_log"] = raw_log
        return parsed

    return _error("Results XML not generated. Simulation may have failed.", raw_log)


def _error(msg: str, raw_log: str = "") -> dict:
    return {
        "pass": False,
        "error": msg,
        "raw_log": raw_log,
        "tests_total": 0,
        "tests_pass": 0,
        "tests_fail": 0,
        "tests_skip": 0,
        "tests": [],
    }


def _parse_results_xml(xml_path: Path) -> dict:
    tree = ET.parse(str(xml_path))
    root = tree.getroot()

    tests_total = 0
    tests_fail = 0
    tests_skip = 0
    tests = []
    sim_time_ns = 0.0

    for suite in root.iter("testsuite"):
        tests_skip += int(suite.get("skipped", 0))

        for case in suite.iter("testcase"):
            tests_total += 1
            name = case.get("name", "unknown")
            classname = case.get("classname", "unknown")

            sns = case.get("sim_time_ns", "")
            if sns:
                try:
                    sim_time_ns += float(sns)
                except ValueError:
                    pass

            failure = case.find("failure")
            err_el = case.find("error")
            if failure is not None or err_el is not None:
                tests_fail += 1
                msg = ""
                if failure is not None:
                    msg = failure.get("message", "")
                    if not msg and failure.text:
                        msg = failure.text
                if err_el is not None and not msg:
                    msg = err_el.get("message", "")
                    if not msg and err_el.text:
                        msg = err_el.text
                tests.append({
                    "name": name,
                    "classname": classname,
                    "passed": False,
                    "failure": msg.strip()[:2000],
                })
            else:
                tests.append({
                    "name": name,
                    "classname": classname,
                    "passed": True,
                })

    tests_pass = tests_total - tests_fail - tests_skip

    return {
        "pass": tests_fail == 0 and tests_total > 0,
        "tests_total": tests_total,
        "tests_pass": tests_pass,
        "tests_fail": tests_fail,
        "tests_skip": tests_skip,
        "sim_time_ns": sim_time_ns,
        "tests": tests,
    }


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="FPGA Simulation Driver")
    p.add_argument("--sources", nargs="+", required=True, help="HDL source files")
    p.add_argument("--toplevel", required=True, help="Top-level module name")
    p.add_argument("--test", required=True, help="Python test module name")
    p.add_argument("--test-dir", default=None, help="Directory containing test modules")
    p.add_argument("--build-dir", default="sim_build")
    p.add_argument("--sim", default="verilator", choices=["verilator", "icarus", "questa", "ghdl"])
    p.add_argument("--waves", action="store_true")
    p.add_argument("--json-only", action="store_true")

    args = p.parse_args()

    result = run_simulation(
        sources=args.sources,
        hdl_toplevel=args.toplevel,
        test_module=args.test,
        test_dir=args.test_dir,
        build_dir=args.build_dir,
        sim=args.sim,
        waves=args.waves,
    )

    if args.json_only:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        status = "PASS" if result["pass"] else "FAIL"
        print(f"\n{'='*60}")
        print(f"  SIMULATION RESULT: {status}")
        print(f"  Tests: {result['tests_total']} total, "
              f"{result['tests_pass']} pass, "
              f"{result['tests_fail']} fail, "
              f"{result['tests_skip']} skip")
        print(f"{'='*60}")
        for t in result.get("tests", []):
            flag = "PASS" if t["passed"] else "FAIL"
            print(f"  [{flag}] {t['classname']}.{t['name']}")
            if not t["passed"]:
                print(f"         {t.get('failure', '')[:200]}")
        print(f"{'='*60}\n")
        if result.get("error"):
            print(f"  ERROR: {result['error']}")

    sys.exit(0 if result["pass"] else 1)

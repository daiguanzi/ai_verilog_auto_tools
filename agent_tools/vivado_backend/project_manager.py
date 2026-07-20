"""Vivado project manager (.xpr) — Tcl-based open/backup/modify/save."""

import os, subprocess
from datetime import datetime
from pathlib import Path


VIVADO_BAT = r"C:\Xilinx\Vivado\2018.2\bin\vivado.bat"


def _vivado_tcl(tcl_content: str, cwd: str = None, timeout: int = 120) -> tuple[int, str, str]:
    """Run a Tcl script in Vivado batch mode; return (rc, stdout, stderr)."""
    tcl_file = os.path.join(cwd or os.getcwd(), "_proj_.tcl")
    Path(tcl_file).write_text("\r\n".join(tcl_content) + "\r\n", encoding="ascii")

    # Try both paths (Windows + WSL)
    vivado = VIVADO_BAT
    is_linux = os.name != "nt"
    if is_linux:
        vivado = VIVADO_BAT.replace("C:\\", "/mnt/c/").replace("\\", "/")
        if not os.path.isfile(vivado):
            vivado = VIVADO_BAT

    if is_linux:
        tcl_win = tcl_file.replace("/mnt/c/", "C:/").replace("/", "\\")
        cmd = ["cmd.exe", "/c", f"{VIVADO_BAT} -mode batch -source \"{tcl_win}\" -nolog"]
    else:
        cmd = [vivado, "-mode", "batch", "-source", os.path.abspath(tcl_file), "-nolog"]

    proc = subprocess.run(cmd, capture_output=True, timeout=timeout, cwd=cwd or ".")
    return proc.returncode, proc.stdout.decode("utf-8", errors="replace"), proc.stderr.decode("utf-8", errors="replace")


def backup_project(xpr_path: str) -> str:
    """Backup a Vivado project (.xpr) and its source tree.
    
    Copies the project directory to a timestamped backup.
    Git commit the current state before backup.
    Returns the backup path.
    """
    xpr = Path(xpr_path).resolve()
    proj_dir = xpr.parent
    backup_dir = proj_dir.parent / f"{proj_dir.name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # git commit current state if repo
    import shutil
    try:
        subprocess.run(["git", "add", "-A"], cwd=str(proj_dir), capture_output=True, timeout=30)
        subprocess.run(["git", "commit", "-m", f"backup before agent modification {datetime.now().isoformat()}"],
                       cwd=str(proj_dir), capture_output=True, timeout=30)
    except Exception:
        pass  # not a git repo or git not available
    
    shutil.copytree(str(proj_dir), str(backup_dir), ignore=shutil.ignore_patterns(
        "*.cache", "*.hw", "*.runs", "*.sim", "sim_build", "__pycache__"))
    return str(backup_dir)


def open_project_modify(xpr_path: str, add_sources: list[str] = None,
                        add_xdc: list[str] = None,
                        set_top: str = None,
                        part: str = None) -> dict:
    """Open a Vivado .xpr project, add/update sources, save.
    
    Returns {"success": bool, "log": str}.
    """
    xpr_abs = os.path.abspath(xpr_path)
    lines = []
    lines.append(f"open_project {{{xpr_abs}}}")
    
    if add_sources:
        for src in add_sources:
            src_abs = os.path.abspath(src)
            lines.append(f"add_files -norecurse {{{src_abs}}}")
        lines.append("update_compile_order -fileset sources_1")
    
    if add_xdc:
        for xdc in add_xdc:
            xdc_abs = os.path.abspath(xdc)
            lines.append(f"add_files -fileset constrs_1 -norecurse {{{xdc_abs}}}")
    
    if set_top:
        lines.append(f"set_property top {{{set_top}}} [current_fileset]")
    
    if part:
        lines.append(f"set_property part {{{part}}} [current_project]")
    
    lines.append("close_project -save")
    lines.append("exit")
    
    rc, stdout, stderr = _vivado_tcl(lines, cwd=os.path.dirname(xpr_abs))
    return {
        "success": rc == 0,
        "rc": rc,
        "log": stdout + "\n" + stderr,
    }


def create_vivado_project(project_dir: str, project_name: str, part: str,
                          sources: list[str], top: str,
                          xdc_files: list[str] = None) -> dict:
    """Create a new Vivado project with sources and constraints.
    
    Returns {"success": bool, "xpr_path": str, "log": str}.
    """
    proj_dir = os.path.abspath(project_dir)
    os.makedirs(proj_dir, exist_ok=True)
    
    lines = []
    lines.append(f"create_project -force {project_name} {{{proj_dir}}} -part {part}")
    
    for src in sources:
        src_abs = os.path.abspath(src)
        lines.append(f"add_files -norecurse {{{src_abs}}}")
    lines.append(f"set_property top {{{top}}} [current_fileset]")
    lines.append("update_compile_order -fileset sources_1")
    
    if xdc_files:
        for xdc in xdc_files:
            xdc_abs = os.path.abspath(xdc)
            lines.append(f"add_files -fileset constrs_1 -norecurse {{{xdc_abs}}}")
    
    lines.append("close_project -save")
    lines.append("exit")
    
    rc, stdout, stderr = _vivado_tcl(lines, cwd=proj_dir)
    xpr_path = os.path.join(proj_dir, f"{project_name}.xpr")
    
    return {
        "success": rc == 0 and os.path.isfile(xpr_path),
        "xpr_path": xpr_path if os.path.isfile(xpr_path) else None,
        "rc": rc,
        "log": stdout + "\n" + stderr,
    }

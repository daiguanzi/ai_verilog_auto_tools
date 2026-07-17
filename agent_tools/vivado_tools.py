"""Vivado Tcl script generator — create/configure IP cores from project.json ip section."""

import json
from pathlib import Path


# ---------------------------------------------------------------------------
# IP parameter presets (common defaults from the user's reference projects)
# ---------------------------------------------------------------------------

IP_PRESETS = {
    "fifo_generator": {
        "fifo_implementation": "Independent_Clocks_Block_RAM",
        "input_data_width":   512,
        "output_data_width":  64,
        "input_depth":        16,
        "output_depth":       128,
    },
    "blk_mem_gen": {
        "memory_type":        "Simple_Dual_Port",
        "write_width_a":      32,
        "read_width_b":       32,
        "write_depth_a":      512,
        "read_depth_b":       512,
        "operating_mode_a":   "WRITE_FIRST",
        "operating_mode_b":   "WRITE_FIRST",
    },
    "mult_gen": {
        "portawidth": 12,
        "portbwidth": 12,
        "signed":     0,
    },
    "floating_point": {
        "operation_type":       "Multiply",
        "a_precision_type":     "Single",
        "result_precision_type":"Single",
        "maximum_latency":      False,
        "has_aclken":           True,
    },
}


def build_ip_spec(ip_type: str, instance: str, custom_params: dict = None) -> dict:
    """Build a spec dict for one IP instance, merging a preset with custom params."""
    preset = IP_PRESETS.get(ip_type, {}).copy()
    if custom_params:
        for k, v in custom_params.items():
            if v is not None:
                preset[k] = v
    return {"type": ip_type, "instance": instance, "params": preset}


def generate_ip_tcl(device: str, part: str, ip_specs: list[dict]) -> str:
    """Generate a Vivado Tcl script that creates and configures the given IPs.

    *device*  — e.g. "xc7a200t-fbg484-2L" (used for -part)
    *part*    — same as device (legacy)
    *ip_specs*— list of dicts: {"type": "fifo_generator", "instance": "my_fifo",
                                 "params": {"input_data_width": 32, ...}}

    Returns the Tcl script as a string.
    """
    lines = [
        "# Auto-generated Vivado IP creation script",
        "# Run: vivado -mode batch -source this_script.tcl",
        "",
        f"set device {{ {device} }}",
        "",
        f"create_project -force _ip_gen _ip_gen -part {device}",
        "",
    ]

    for spec in ip_specs:
        ip_type   = spec["type"]
        instance  = spec["instance"]
        params    = spec.get("params", {})

        lines.append(f"puts \"=== Creating {ip_type} : {instance} ===\"")
        lines.append(f"create_ip -name {ip_type} -vendor xilinx.com "
                     f"-library ip -module_name {instance}")

        props = []
        for key, val in params.items():
            props.append(f"    CONFIG.{key} {{{val}}}")
        prop_lines = " \\\n".join(props)
        lines.append(f"set_property -dict [list \\\n{prop_lines} \\\n] [get_ips {instance}]")
        lines.append(f"generate_target all [get_files {instance}.xci]")
        lines.append(f"export_simulation -of_objects [get_files {instance}.xci] "
                     f"-force -directory ./{instance}_sim")
        lines.append("")

    lines.append("puts \"=== ALL IPs GENERATED ===\"")
    lines.append("exit")
    return "\r\n".join(lines) + "\r\n"


def write_ip_tcl(output_path: str, device: str, ip_specs: list[dict]) -> str:
    """Generate and write a Vivado IP-creation Tcl script to *output_path*."""
    content = generate_ip_tcl(device, device, ip_specs)
    Path(output_path).write_text(content, encoding="ascii")
    return str(output_path)

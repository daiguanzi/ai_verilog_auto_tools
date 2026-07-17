"""Vivado XDC constraint generator — auto-generate clock, pin, and timing constraints."""

from pathlib import Path


def generate_xdc(
    *,
    clocks: list[dict] | None = None,
    pins: list[dict] | None = None,
    false_paths: list[dict] | None = None,
    comment: str = "",
) -> str:
    """Generate a Vivado XDC constraint file from structured specs.

    clocks:
        {"name": "clk", "port": "clk", "period_ns": 10.0, "jitter_ns": None}
    pins:
        {"name": "led0", "port": "led[0]", "loc": "P15", "standard": "LVCMOS33",
         "drive": None, "slew": None}
    false_paths:
        {"from": "clk_a", "to": "clk_b"}  — set_false_path between domains

    Returns XDC content as a string (CRLF line endings).
    """
    lines = [
        "# Auto-generated XDC constraints",
    ]
    if comment:
        lines.append(f"# {comment}")
    lines.append("")

    # Clock constraints
    if clocks:
        lines.append("# ---- Clock constraints ----")
        for clk in clocks:
            name = clk.get("name", "clk")
            port = clk.get("port", "clk")
            period = clk.get("period_ns", 10.0)
            lines.append(f"create_clock -name {name} -period {period} "
                         f"[get_ports {{{port}}}]")
            jitter = clk.get("jitter_ns")
            if jitter is not None:
                lines.append(f"set_input_jitter [get_clocks {name}] {jitter}")
        lines.append("")

    # Pin constraints
    if pins:
        lines.append("# ---- Pin assignments ----")
        for pin in pins:
            port = pin.get("port", "")
            loc = pin.get("loc", "")
            standard = pin.get("standard", "LVCMOS33")
            if loc:
                lines.append(f"set_property -dict {{")
                lines.append(f"    PACKAGE_PIN {{{loc}}}")
                lines.append(f"    IOSTANDARD {{{standard}}}")
                drive = pin.get("drive")
                if drive:
                    lines.append(f"    DRIVE {{{drive}}}")
                slew = pin.get("slew")
                if slew:
                    lines.append(f"    SLEW {{{slew}}}")
                lines.append(f"}} [get_ports {{{port}}}]")
                lines.append("")
        # If last block ended with blank, already accounted
        if not lines[-1] == "":
            lines.append("")

    # False paths (CDC)
    if false_paths:
        lines.append("# ---- CDC / false path ----")
        for fp in false_paths:
            src = fp.get("from", "")
            dst = fp.get("to", "")
            lines.append(f"set_false_path -from [get_clocks {{{src}}}] "
                         f"-to [get_clocks {{{dst}}}]")
        lines.append("")

    return "\r\n".join(lines) + "\r\n"


def write_xdc(output_path: str, **kwargs) -> str:
    """Generate and write an XDC file. Kwargs same as generate_xdc()."""
    content = generate_xdc(**kwargs)
    Path(output_path).write_text(content, encoding="ascii")
    return str(output_path)

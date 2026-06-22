import cocotb
from cocotb.triggers import Timer


@cocotb.test()
async def test_param_override(dut):
    """WIDTH overridden to 4 -> maxval is 4 bits all-ones = 15 (not 255)."""
    await Timer(1, "ns")
    val = int(dut.maxval.value)
    assert val == 15, f"parameter override failed: expected 15 (WIDTH=4), got {val}"
    cocotb.log.info("PASSED: parameter override (WIDTH=4)")


@cocotb.test()
async def test_define_and_include(dut):
    """EXTRA define + included `MAGIC -> tag = 0xA5 (not 0x00)."""
    await Timer(1, "ns")
    tag = int(dut.tag.value)
    assert tag == 0xA5, f"define/include failed: expected 0xA5, got {hex(tag)}"
    cocotb.log.info("PASSED: define + include")

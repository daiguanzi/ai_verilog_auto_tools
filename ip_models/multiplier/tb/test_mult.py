import cocotb
from cocotb.triggers import RisingEdge, Timer, ClockCycles
from cocotb.clock import Clock


async def reset_dut(dut):
    dut.rst_n.value = 0
    dut.a.value = 0
    dut.b.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)


@cocotb.test()
async def test_basic_multiply(dut):
    """3 * 7 = 21."""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)

    dut.a.value = 3
    dut.b.value = 7
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    assert int(dut.p.value) == 21, f"3*7 expected 21, got {int(dut.p.value)}"


@cocotb.test()
async def test_zero(dut):
    """a * 0 = 0."""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)

    dut.a.value = 1234
    dut.b.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    assert int(dut.p.value) == 0


@cocotb.test()
async def test_signed_max(dut):
    """Max signed positive 12-bit: 2047 * 2047 = 4190209."""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)

    dut.a.value = 2047
    dut.b.value = 2047
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    assert int(dut.p.value) == 4190209, \
        f"2047*2047 expected 4190209, got {int(dut.p.value)}"


@cocotb.test()
async def test_signed_multiply(dut):
    """(-3) * 7 = -21 in 12-bit signed. IS_SIGNED=1 must be set in project.json."""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)

    # -3 = 0xFFD in 12-bit two's complement
    dut.a.value = 0xFFD
    dut.b.value = 7
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    val = int(dut.p.value)
    assert val == 16777195, f"(-3)*7 expected 16777195 (0xFFFFEB), got {val}"


@cocotb.test()
async def test_commutative(dut):
    """a * b == b * a."""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)

    dut.a.value = 100
    dut.b.value = 200
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    ab = int(dut.p.value)

    dut.a.value = 200
    dut.b.value = 100
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    ba = int(dut.p.value)
    assert ab == ba, f"commutativity: {ab} != {ba}"

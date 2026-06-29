import cocotb
from cocotb.triggers import RisingEdge
from cocotb.clock import Clock


async def reset_dut(dut):
    dut.rst_n.value = 0
    dut.enable.value = 0
    dut.a.value = 0
    dut.b.value = 0
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    for _ in range(3):
        await RisingEdge(dut.clk)


async def one_mac(dut, a, b):
    """Single-cycle MAC: assert enable/a/b for 1 cycle, sample accum after."""
    dut.a.value = a
    dut.b.value = b
    dut.enable.value = 1
    await RisingEdge(dut.clk)
    dut.enable.value = 0
    await RisingEdge(dut.clk)
    result = int(dut.accum.value)
    await RisingEdge(dut.clk)
    return result


@cocotb.test()
async def test_single_multiply_accumulate(dut):
    """One product: a=3,b=4 → accum=12."""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)
    val = await one_mac(dut, 3, 4)
    assert val == 12, f"expected 12, got {val}"


@cocotb.test()
async def test_accumulate_sequence(dut):
    """Accumulate 3 steps: 2*3 + 4*5 + 6*7 = 6+20+42 = 68."""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)
    v1 = await one_mac(dut, 2, 3)
    assert v1 == 6
    v2 = await one_mac(dut, 4, 5)
    assert v2 == 26
    v3 = await one_mac(dut, 6, 7)
    assert v3 == 68


@cocotb.test()
async def test_enable_gate(dut):
    """enable=0 → accum does not change."""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)
    v1 = await one_mac(dut, 5, 5)
    assert v1 == 25
    v2 = await one_mac(dut, 3, 3)
    assert v2 == 34, f"5*5=25 + 3*3=9 = 34, got {v2}"

    dut.enable.value = 0
    dut.a.value = 10
    dut.b.value = 10
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    assert int(dut.accum.value) == 34, "no enable → accum unchanged"


@cocotb.test()
async def test_reset_clears_accum(dut):
    """rst_n=0 clears accumulator."""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)
    v = await one_mac(dut, 10, 10)
    assert v == 100
    dut.rst_n.value = 0
    for _ in range(3):
        await RisingEdge(dut.clk)
    assert int(dut.accum.value) == 0, "reset should clear to 0"

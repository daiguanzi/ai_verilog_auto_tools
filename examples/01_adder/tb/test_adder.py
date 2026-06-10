import cocotb
from cocotb.triggers import RisingEdge
from cocotb.clock import Clock


async def reset_dut(dut):
    dut.rst_n.value = 0
    for _ in range(5):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    for _ in range(5):
        await RisingEdge(dut.clk)


async def tick(dut, n=1):
    for _ in range(n):
        await RisingEdge(dut.clk)


@cocotb.test()
async def test_adder_basic(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_dut(dut)
    cocotb.log.info("=== BASIC ADD ===")

    dut.a.value = 10
    dut.b.value = 20
    await tick(dut, 2)
    assert int(dut.sum.value) == 30, f"10+20 got {int(dut.sum.value)}"

    dut.a.value = 255
    dut.b.value = 1
    await tick(dut, 2)
    assert int(dut.sum.value) == 256, f"255+1 got {int(dut.sum.value)}"

    dut.a.value = 0
    dut.b.value = 0
    await tick(dut, 2)
    assert int(dut.sum.value) == 0, f"0+0 got {int(dut.sum.value)}"

    cocotb.log.info("PASSED")


@cocotb.test()
async def test_adder_reset(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_dut(dut)
    cocotb.log.info("=== RESET BEHAVIOR ===")

    dut.a.value = 100
    dut.b.value = 200
    await tick(dut, 2)
    assert int(dut.sum.value) == 300, "100+200 expected"

    dut.rst_n.value = 0
    for _ in range(5):
        await RisingEdge(dut.clk)
    assert int(dut.sum.value) == 0, "reset should zero sum"

    dut.rst_n.value = 1
    for _ in range(5):
        await RisingEdge(dut.clk)
    assert int(dut.sum.value) == 300, "after reset release, should be 300"

    cocotb.log.info("PASSED")

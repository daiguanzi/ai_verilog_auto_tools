import cocotb
from cocotb.triggers import Timer, RisingEdge
from cocotb.clock import Clock


@cocotb.test()
async def test_adder_basic(dut):
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    dut.rst_n.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1

    dut.a.value = 10
    dut.b.value = 20
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert dut.sum.value == 30, f"10+20 failed: got {dut.sum.value}"

    dut.a.value = 255
    dut.b.value = 1
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert dut.sum.value == 256, f"255+1 failed: got {dut.sum.value}"

    dut.a.value = 0
    dut.b.value = 0
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert dut.sum.value == 0, f"0+0 failed: got {dut.sum.value}"

    cocotb.log.info("ALL TESTS PASSED")


@cocotb.test()
async def test_adder_reset(dut):
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    dut.rst_n.value = 0
    dut.a.value = 100
    dut.b.value = 200
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert dut.sum.value == 0, f"Reset failed: got {dut.sum.value}"

    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert dut.sum.value == 300, f"After reset failed: got {dut.sum.value}"

import cocotb
from cocotb.triggers import RisingEdge
from cocotb.clock import Clock


async def reset_dut(dut):
    dut.rst_n.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)


def clear_inputs(dut):
    """Clear all control inputs. Extend for your design."""
    pass


async def insert_input(dut, **kwargs):
    """Drive inputs, wait for registered output to settle.
    
    Standard 3-edge pattern. See docs/SIMULATOR_GUIDE.md.
    """
    for name, val in kwargs.items():
        getattr(dut, name).value = val
    await RisingEdge(dut.clk)
    clear_inputs(dut)
    await RisingEdge(dut.clk)
    result = {}
    await RisingEdge(dut.clk)
    return result


@cocotb.test()
async def test_basic(dut):
    """Basic functionality test."""
    clock = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)
    clear_inputs(dut)

    await RisingEdge(dut.clk)

    # TODO: Write your test here

    cocotb.log.info("TEST PASSED")

import cocotb
from cocotb.triggers import RisingEdge
from cocotb.clock import Clock


async def reset_dut(dut):
    """Hold reset for 5+ edges then release for 5+ edges."""
    dut.rst_n.value = 0
    for _ in range(5):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    for _ in range(5):
        await RisingEdge(dut.clk)


async def reset_and_clear(dut):
    """Reset + clear ALL control inputs. Prevents cross-test GPI contamination."""
    await reset_dut(dut)
    # TODO: zero all your control signals here, e.g.:
    # dut.enable.value = 0
    # dut.my_input.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)


async def tick(dut, n=1):
    """Advance N clock cycles."""
    for _ in range(n):
        await RisingEdge(dut.clk)


def log_state(dut, label):
    """Log DUT state. Customize with your design's signals."""
    cocotb.log.info(f"  [{label}]")


async def apply_and_settle(dut, signal, value):
    """Set a LEVEL control. 2-edge settle. Use for: enable, up_down, mode."""
    signal.value = value
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)


async def drive_pulse(dut, signal, value):
    """Single-cycle PULSE. 3-edge pattern. Use for: send, wr_en, rd_en, coin."""
    signal.value = value
    await RisingEdge(dut.clk)
    signal.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)


@cocotb.test()
async def test_basic(dut):
    """Core functionality test."""
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)

    # TODO: Write your test here

    cocotb.log.info("PASSED")

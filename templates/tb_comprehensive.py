import cocotb
from cocotb.triggers import RisingEdge
from cocotb.clock import Clock


# ============================================================
#  Standard Helpers — keep in every testbench
# ============================================================

async def reset_dut(dut):
    """Hold reset for 5+ edges then release. Async reset needs long hold."""
    dut.rst_n.value = 0
    for _ in range(5):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    for _ in range(5):
        await RisingEdge(dut.clk)


async def reset_and_clear(dut):
    """
    Reset + settle ALL control inputs to known values.
    Prevents GPI contamination from previous tests crossing over.
    See knowledge/patterns/robust_test_reset.md
    """
    await reset_dut(dut)
    # TODO: Zero all your control inputs:
    # dut.enable.value = 0
    # await RisingEdge(dut.clk)
    # await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)


async def tick(dut, n=1):
    """Advance N clock cycles (idle waiting)."""
    for _ in range(n):
        await RisingEdge(dut.clk)


def log_state(dut, label):
    """Print DUT state. Customize with your signals."""
    cocotb.log.info(f"  [{label}]")


async def apply_and_settle(dut, signal, value):
    """
    Set a LEVEL control signal and wait for GPI settle (2 edges).
    Use for signals that STAY asserted: enable, up_down, mode, button_in.
    WARNING: The second edge causes one "side effect" (e.g. enable=1
    increments counter by 1 during settle). Account for this in assertions.
    See knowledge/simulator/verilator_cocotb.md
    """
    signal.value = value
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)


async def drive_pulse(dut, signal, value):
    """
    Drive a single-cycle PULSE and wait for registers to settle (3 edges).
    Use for ACTION triggers: send, wr_en, rd_en, coin, strobe.
    The signal is asserted, then cleared on the next edge to prevent
    double-counting. Registered outputs are sampled on edge 3.
    See knowledge/patterns/delayed_input_signal.md
    """
    signal.value = value
    await RisingEdge(dut.clk)
    signal.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)


# ============================================================
#  Test Scenarios — one @cocotb.test() per scenario
# ============================================================

@cocotb.test()
async def test_reset_behavior(dut):
    """Verify reset initializes outputs correctly."""
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)

    # TODO: Assert post-reset output values
    # assert int(dut.count.value) == 0, "reset should zero count"

    cocotb.log.info("PASSED: reset behavior")


@cocotb.test()
async def test_normal_operation(dut):
    """Verify the primary functional path."""
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)

    # TODO: Test normal operation
    # - For pulsed inputs: use drive_pulse(dut, dut.send, 1)
    # - For level controls: use apply_and_settle(dut, dut.enable, 1)
    # - For waiting: use tick(dut, n)

    cocotb.log.info("PASSED: normal operation")


@cocotb.test()
async def test_boundary_conditions(dut):
    """Verify edge cases (min/max values, overflow, timing bounds)."""
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)

    # TODO: Test boundary conditions
    # - Min/max data values (0x00, 0xFF)
    # - Maximum counter/pointer values
    # - Exactly-at-threshold timing

    cocotb.log.info("PASSED: boundary conditions")


@cocotb.test()
async def test_error_handling(dut):
    """Verify correct behavior on invalid/unexpected inputs."""
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)

    # TODO: Test error handling
    # - Overflow/underflow prevention
    # - Invalid command sequences
    # - Back-to-back rapid operations

    cocotb.log.info("PASSED: error handling")

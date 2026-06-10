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


async def drive_signal(dut, signal_name, value, duration=1):
    """Drive a signal, wait for it to propagate through the pipeline.
    
    Standard 3-edge pattern for Verilator+cocotb:
    1. Set signal
    2. Edge 1: signal enters model
    3. Clear immediately (prevent double-counting)
    4. Edge 2: registers update
    5. Sample results
    6. Edge 3: settle
    """
    sig = getattr(dut, signal_name)
    sig.value = value
    await RisingEdge(dut.clk)
    clear_inputs(dut)
    await RisingEdge(dut.clk)
    # Sample point — read registered outputs here
    await RisingEdge(dut.clk)
    # Settled


@cocotb.test()
async def test_reset_behavior(dut):
    """Test that reset properly initializes the design."""
    clock = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)
    clear_inputs(dut)

    await RisingEdge(dut.clk)
    # TODO: assert reset values
    cocotb.log.info("RESET TEST PASSED")


@cocotb.test()
async def test_normal_operation(dut):
    """Test normal functional operation."""
    clock = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)
    clear_inputs(dut)

    await RisingEdge(dut.clk)
    # TODO: test normal operation
    cocotb.log.info("NORMAL OPERATION TEST PASSED")


@cocotb.test()
async def test_boundary_conditions(dut):
    """Test edge cases and boundary conditions."""
    clock = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)
    clear_inputs(dut)

    await RisingEdge(dut.clk)
    # TODO: test boundary conditions
    cocotb.log.info("BOUNDARY TEST PASSED")


@cocotb.test()
async def test_error_handling(dut):
    """Test error handling and invalid inputs."""
    clock = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)
    clear_inputs(dut)

    await RisingEdge(dut.clk)
    # TODO: test error conditions
    cocotb.log.info("ERROR HANDLING TEST PASSED")

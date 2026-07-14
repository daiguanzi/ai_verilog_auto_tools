import cocotb
from cocotb.triggers import RisingEdge, Timer, ClockCycles
from cocotb.clock import Clock


async def reset_fifo(dut):
    """Clear all control signals, assert reset, settle."""
    dut.wr_en.value = 0
    dut.din.value = 0
    dut.rd_en.value = 0
    dut.wr_rst_n.value = 0
    dut.rd_rst_n.value = 0
    await ClockCycles(dut.wr_clk, 3)
    await ClockCycles(dut.rd_clk, 3)
    dut.wr_rst_n.value = 1
    dut.rd_rst_n.value = 1
    await ClockCycles(dut.wr_clk, 5)
    await ClockCycles(dut.rd_clk, 5)


async def do_write(dut, data):
    """Single-cycle write with GPI-safe timing."""
    dut.din.value = data
    dut.wr_en.value = 1
    await RisingEdge(dut.wr_clk)
    dut.wr_en.value = 0
    await RisingEdge(dut.wr_clk)


async def do_read(dut):
    """Single-cycle read returning the read data (GPI-safe)."""
    dut.rd_en.value = 1
    await RisingEdge(dut.rd_clk)
    dut.rd_en.value = 0
    await RisingEdge(dut.rd_clk)  # output register latency
    val = int(dut.dout.value)
    await RisingEdge(dut.rd_clk)
    return val


@cocotb.test()
async def test_single_write_read(dut):
    """Write one word, read it back."""
    cocotb.start_soon(Clock(dut.wr_clk, 10, "ns").start())
    cocotb.start_soon(Clock(dut.rd_clk, 10, "ns").start())
    await reset_fifo(dut)

    assert int(dut.empty.value) == 1, "initially empty"
    assert int(dut.full.value) == 0, "initially not full"

    await do_write(dut, 0xAB)
    assert int(dut.empty.value) == 0, "not empty after write"

    val = await do_read(dut)
    assert val == 0xAB, f"expected 0xAB, got {hex(val)}"
    assert int(dut.empty.value) == 1, "empty after read"


@cocotb.test()
async def test_full_empty_flags(dut):
    """Fill to DEPTH, verify full; drain, verify empty."""
    cocotb.start_soon(Clock(dut.wr_clk, 10, "ns").start())
    cocotb.start_soon(Clock(dut.rd_clk, 10, "ns").start())
    await reset_fifo(dut)

    depth = 16  # WRITE_DEPTH
    assert int(dut.empty.value) == 1

    for i in range(depth):
        await do_write(dut, i)

    assert int(dut.full.value) == 1, "should be full after fill"
    assert int(dut.empty.value) == 0

    for i in range(depth):
        val = await do_read(dut)
        assert val == i, f"expected {i}, got {val}"

    assert int(dut.empty.value) == 1, "should be empty after drain"
    assert int(dut.full.value) == 0


@cocotb.test()
async def test_wraparound(dut):
    """Write DEPTH+8 entries while reading one per write."""
    cocotb.start_soon(Clock(dut.wr_clk, 10, "ns").start())
    cocotb.start_soon(Clock(dut.rd_clk, 10, "ns").start())
    await reset_fifo(dut)

    depth = 16
    for i in range(depth + 8):
        w = 0x80 | i
        await do_write(dut, w)
        val = await do_read(dut)
        assert val == w, f"round {i}: expected {hex(w)}, got {hex(val)}"

    assert int(dut.empty.value) == 1, "should be empty at end"


@cocotb.test()
async def test_overflow_prevention(dut):
    """Writing when full should be ignored."""
    cocotb.start_soon(Clock(dut.wr_clk, 10, "ns").start())
    cocotb.start_soon(Clock(dut.rd_clk, 10, "ns").start())
    await reset_fifo(dut)

    depth = 16
    for i in range(depth):
        await do_write(dut, i)

    assert int(dut.full.value) == 1

    # attempt overflow write
    await do_write(dut, 0xFF)

    val = await do_read(dut)
    assert val == 0, "overflow should not overwrite: first entry still 0"


@cocotb.test()
async def test_underflow_prevention(dut):
    """Reading when empty returns last data; empty stays."""
    cocotb.start_soon(Clock(dut.wr_clk, 10, "ns").start())
    cocotb.start_soon(Clock(dut.rd_clk, 10, "ns").start())
    await reset_fifo(dut)

    assert int(dut.empty.value) == 1

    await do_write(dut, 0x42)
    val = await do_read(dut)
    assert val == 0x42

    # read from empty FIFO
    val = await do_read(dut)
    assert val == 0x42, "empty read holds last value"
    assert int(dut.empty.value) == 1

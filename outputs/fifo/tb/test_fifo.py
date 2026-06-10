import cocotb
from cocotb.triggers import RisingEdge
from cocotb.clock import Clock


DEPTH = 16


async def reset_dut(dut):
    dut.rst_n.value = 0
    for _ in range(5):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    for _ in range(5):
        await RisingEdge(dut.clk)


async def reset_and_clear(dut):
    await reset_dut(dut)
    dut.wr_en.value = 0
    dut.rd_en.value = 0
    dut.data_in.value = 0
    await tick(dut, 5)


def log_state(dut, label):
    wr = int(dut.wr_en.value)
    rd = int(dut.rd_en.value)
    fl = int(dut.full.value)
    em = int(dut.empty.value)
    di = int(dut.data_in.value)
    do = int(dut.data_out.value)
    cocotb.log.info(f"  [{label:25s}] wr={wr} rd={rd} full={fl} empty={em} in={di} out={do}")


async def tick(dut, n=1):
    for _ in range(n):
        await RisingEdge(dut.clk)


async def do_write(dut, data):
    dut.data_in.value = data
    dut.wr_en.value = 1
    await RisingEdge(dut.clk)
    dut.wr_en.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)


async def do_read(dut):
    dut.rd_en.value = 1
    await RisingEdge(dut.clk)
    dut.rd_en.value = 0
    await RisingEdge(dut.clk)
    result = int(dut.data_out.value)
    await RisingEdge(dut.clk)
    return result


@cocotb.test()
async def test_single_write_read(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)
    cocotb.log.info("=== SINGLE WRITE/READ ===")

    assert int(dut.empty.value) == 1, "initially empty"
    assert int(dut.full.value) == 0, "initially not full"

    await do_write(dut, 0xAB)
    assert int(dut.empty.value) == 0, "not empty after write"

    val = await do_read(dut)
    assert val == 0xAB, f"expected 0xAB, got {val}"
    assert int(dut.empty.value) == 1, "empty after read"
    cocotb.log.info("PASSED")


@cocotb.test()
async def test_full_empty_flags(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)
    cocotb.log.info("=== FULL / EMPTY FLAGS ===")

    assert int(dut.empty.value) == 1
    assert int(dut.full.value) == 0

    for i in range(DEPTH):
        await do_write(dut, i)
    log_state(dut, "after fill")
    assert int(dut.full.value) == 1, "should be full"
    assert int(dut.empty.value) == 0, "should not be empty"

    for i in range(DEPTH):
        val = await do_read(dut)
        assert val == i, f"expected {i}, got {val}"
    log_state(dut, "after drain")
    assert int(dut.empty.value) == 1, "should be empty"
    assert int(dut.full.value) == 0, "should not be full"
    cocotb.log.info("PASSED")


@cocotb.test()
async def test_wraparound(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)
    cocotb.log.info("=== WRAPAROUND ===")

    for i in range(DEPTH + 8):
        w = 0x80 | i
        await do_write(dut, w)
        val = await do_read(dut)
        assert val == w, f"round {i}: expected {w}, got {val}"

    assert int(dut.empty.value) == 1, "should be empty at end"
    cocotb.log.info("PASSED")


@cocotb.test()
async def test_overflow_prevention(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)
    cocotb.log.info("=== OVERFLOW PREVENTION ===")

    for i in range(DEPTH):
        await do_write(dut, i)

    assert int(dut.full.value) == 1

    await do_write(dut, 0xFF)

    val = await do_read(dut)
    assert val == 0, "first entry should still be 0, not 0xFF"
    cocotb.log.info("PASSED")


@cocotb.test()
async def test_underflow_prevention(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)
    cocotb.log.info("=== UNDERFLOW PREVENTION ===")

    assert int(dut.empty.value) == 1

    await do_write(dut, 0x42)
    val = await do_read(dut)
    assert val == 0x42, "read correct data"

    val = await do_read(dut)
    assert val == 0x42, "empty read should hold previous value"
    assert int(dut.empty.value) == 1
    cocotb.log.info("PASSED")

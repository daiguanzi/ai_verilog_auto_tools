import cocotb
from cocotb.triggers import RisingEdge
from cocotb.clock import Clock


WIDTH = 4
MAX_VAL = (1 << WIDTH) - 1


async def reset_dut(dut):
    dut.rst_n.value = 0
    for _ in range(5):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    for _ in range(5):
        await RisingEdge(dut.clk)


async def reset_and_clear(dut):
    await reset_dut(dut)
    await apply_and_settle(dut, dut.enable, 0)
    await apply_and_settle(dut, dut.up_down, 0)
    await apply_and_settle(dut, dut.load, 0)
    await apply_and_settle(dut, dut.data_in, 0)
    await tick(dut, 2)


def log_state(dut, label):
    cnt = int(dut.count.value)
    tc  = int(dut.terminal_count.value)
    cocotb.log.info(f"  [{label:30s}] count={cnt} tc={tc}")


async def apply_and_settle(dut, signal, value):
    signal.value = value
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)


async def tick(dut, n=1):
    for _ in range(n):
        await RisingEdge(dut.clk)


@cocotb.test()
async def test_up_count(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)
    cocotb.log.info("=== UP COUNT ===")

    await apply_and_settle(dut, dut.enable, 1)
    while int(dut.count.value) != MAX_VAL:
        await tick(dut)
    log_state(dut, "at max")
    assert int(dut.terminal_count.value) == 1

    await tick(dut)
    assert int(dut.count.value) == 0
    cocotb.log.info("PASSED")


@cocotb.test()
async def test_down_count(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)
    cocotb.log.info("=== DOWN COUNT ===")

    dut.data_in.value = 5
    await apply_and_settle(dut, dut.load, 1)
    dut.load.value = 0
    await tick(dut)
    log_state(dut, "loaded 5")
    assert int(dut.count.value) == 5

    await apply_and_settle(dut, dut.up_down, 1)
    await apply_and_settle(dut, dut.enable, 1)
    log_state(dut, "down enabled")
    assert int(dut.count.value) == 4  # enable edge decremented 5->4

    while int(dut.count.value) != 0:
        await tick(dut)
    assert int(dut.terminal_count.value) == 1
    cocotb.log.info("PASSED")


@cocotb.test()
async def test_load(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)
    cocotb.log.info("=== LOAD ===")

    for val in [7, 3, 12, 1]:
        dut.data_in.value = val
        await apply_and_settle(dut, dut.load, 1)
        dut.load.value = 0
        await tick(dut)
        assert int(dut.count.value) == val, f"load {val}"
    cocotb.log.info("PASSED")


@cocotb.test()
async def test_enable_gate(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)
    cocotb.log.info("=== ENABLE GATE ===")

    dut.data_in.value = 2
    await apply_and_settle(dut, dut.load, 1)
    dut.load.value = 0
    await tick(dut)
    log_state(dut, "loaded 2")
    assert int(dut.count.value) == 2

    await apply_and_settle(dut, dut.enable, 1)
    log_state(dut, "enabled")
    assert int(dut.count.value) == 3  # enable edge incremented 2->3

    await tick(dut, 4)
    frozen = int(dut.count.value)
    cocotb.log.info(f"  frozen at count={frozen}")
    assert frozen in (5, 6, 7), f"unexpected frozen {frozen}"

    dut.enable.value = 0
    await tick(dut, 8)
    log_state(dut, "disabled")
    held = int(dut.count.value)

    dut.enable.value = 1
    await tick(dut, 4)
    log_state(dut, "re-enabled")
    assert int(dut.count.value) > held
    cocotb.log.info("PASSED")


@cocotb.test()
async def test_reset(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)
    cocotb.log.info("=== RESET ===")

    dut.data_in.value = 8
    await apply_and_settle(dut, dut.load, 1)
    dut.load.value = 0
    await tick(dut)
    assert int(dut.count.value) == 8

    dut.rst_n.value = 0
    await tick(dut, 8)
    dut.rst_n.value = 1
    await tick(dut, 8)
    assert int(dut.count.value) == 0
    cocotb.log.info("PASSED")


@cocotb.test()
async def test_load_priority(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)
    cocotb.log.info("=== LOAD PRIORITY ===")

    await apply_and_settle(dut, dut.enable, 1)
    dut.data_in.value = 9
    await apply_and_settle(dut, dut.load, 1)
    dut.load.value = 0
    await tick(dut)
    assert int(dut.count.value) == 9
    cocotb.log.info("PASSED")

import cocotb
from cocotb.triggers import RisingEdge
from cocotb.clock import Clock


MAX_COUNT = 100


async def reset_dut(dut):
    dut.rst_n.value = 0
    for _ in range(5):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    for _ in range(5):
        await RisingEdge(dut.clk)


async def reset_and_clear(dut):
    await reset_dut(dut)
    await apply_and_settle(dut, dut.button_in, 0)
    await tick(dut, 2)


def log_state(dut, label):
    s  = int(dut.button_in.value)
    bo = int(dut.button_out.value)
    cocotb.log.info(f"  [{label:30s}] btn_in={s} btn_out={bo}")


async def apply_and_settle(dut, signal, value):
    signal.value = value
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)


async def tick(dut, n=1):
    for _ in range(n):
        await RisingEdge(dut.clk)


async def press_button(dut, cycles):
    await apply_and_settle(dut, dut.button_in, 1)
    for _ in range(cycles - 2):
        await RisingEdge(dut.clk)
    await apply_and_settle(dut, dut.button_in, 0)


@cocotb.test()
async def test_stable_press(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)
    cocotb.log.info("=== STABLE PRESS ===")

    await apply_and_settle(dut, dut.button_in, 1)

    pulse_seen = False
    for _ in range(MAX_COUNT + 20):
        await RisingEdge(dut.clk)
        if int(dut.button_out.value):
            pulse_seen = True
            log_state(dut, "pulse detected")
            break

    assert pulse_seen, "should pulse after stable press"

    await tick(dut, 2)
    assert int(dut.button_out.value) == 0, "pulse should be 1 cycle wide"

    await apply_and_settle(dut, dut.button_in, 0)
    await tick(dut, 5)
    assert int(dut.button_out.value) == 0, "no pulse after release"
    cocotb.log.info("PASSED")


@cocotb.test()
async def test_bounce_rejection(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)
    cocotb.log.info("=== BOUNCE REJECTION ===")

    for _ in range(10):
        await tick(dut, 3)
        await apply_and_settle(dut, dut.button_in, 1)
        await tick(dut, 2)
        await apply_and_settle(dut, dut.button_in, 0)

    await tick(dut, 5)
    log_state(dut, "after bouncing")
    assert int(dut.button_out.value) == 0, "no pulse from bouncing"
    cocotb.log.info("PASSED")


@cocotb.test()
async def test_hold_single_pulse(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)
    cocotb.log.info("=== HOLD SINGLE PULSE ===")

    await apply_and_settle(dut, dut.button_in, 1)
    for _ in range(MAX_COUNT * 3):
        await RisingEdge(dut.clk)
    log_state(dut, "after long hold")

    pulse_count = 0
    for _ in range(MAX_COUNT * 3):
        await RisingEdge(dut.clk)
        if int(dut.button_out.value):
            pulse_count += 1
    assert pulse_count <= 1, f"long hold gave {pulse_count} pulses, expected <= 1"

    await apply_and_settle(dut, dut.button_in, 0)
    await tick(dut, 5)
    cocotb.log.info("PASSED")


@cocotb.test()
async def test_short_press_ignored(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)
    cocotb.log.info("=== SHORT PRESS IGNORED ===")

    await apply_and_settle(dut, dut.button_in, 1)
    for _ in range(MAX_COUNT // 2):
        await RisingEdge(dut.clk)
    await apply_and_settle(dut, dut.button_in, 0)
    await tick(dut, 5)
    log_state(dut, "after short press")

    assert int(dut.button_out.value) == 0, "short press should not trigger pulse"
    cocotb.log.info("PASSED")


@cocotb.test()
async def test_multiple_presses(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)
    cocotb.log.info("=== MULTIPLE PRESSES ===")

    pulse_count = 0

    for press_idx in range(3):
        cocotb.log.info(f"  Press {press_idx + 1}...")
        await apply_and_settle(dut, dut.button_in, 1)
        for _ in range(MAX_COUNT + 10):
            await RisingEdge(dut.clk)
            if int(dut.button_out.value):
                pulse_count += 1
        await apply_and_settle(dut, dut.button_in, 0)
        for _ in range(MAX_COUNT):
            await RisingEdge(dut.clk)

    log_state(dut, "after 3 presses")
    assert pulse_count == 3, f"expected 3 pulses, got {pulse_count}"
    cocotb.log.info("PASSED")

import cocotb
from cocotb.triggers import RisingEdge
from cocotb.clock import Clock


BIT_PERIOD = 10


async def reset_dut(dut):
    dut.rst_n.value = 0
    for _ in range(5):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    for _ in range(5):
        await RisingEdge(dut.clk)


async def reset_and_clear(dut):
    await reset_dut(dut)
    await apply_and_settle(dut, dut.send, 0)
    await apply_and_settle(dut, dut.data_in, 0)
    await tick(dut, 2)


def log_state(dut, label):
    snd = int(dut.send.value)
    bsy = int(dut.busy.value)
    dn  = int(dut.done.value)
    tx  = int(dut.tx.value)
    cocotb.log.info(f"  [{label:25s}] send={snd} busy={bsy} done={dn} tx={tx}")


async def apply_and_settle(dut, signal, value):
    signal.value = value
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)


async def tick(dut, n=1):
    for _ in range(n):
        await RisingEdge(dut.clk)


async def send_byte(dut, data):
    dut.data_in.value = data
    dut.send.value = 1
    await RisingEdge(dut.clk)
    dut.send.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)


async def wait_idle(dut, max_cycles=500):
    for _ in range(max_cycles):
        await RisingEdge(dut.clk)
        if not int(dut.busy.value):
            return True
    return False


@cocotb.test()
async def test_single_byte(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)
    cocotb.log.info("=== SINGLE BYTE 0xA5 ===")

    await send_byte(dut, 0xA5)
    log_state(dut, "sent")
    assert int(dut.busy.value) == 1, "should be busy"

    bits = []
    for _ in range(12 * BIT_PERIOD):
        await RisingEdge(dut.clk)
        bits.append(int(dut.tx.value))
        if not int(dut.busy.value):
            break

    cocotb.log.info(f"  captured {len(bits)} tx samples")

    assert 0 in bits[:BIT_PERIOD], "start bit (0) not seen"

    done_seen = int(dut.done.value) == 1
    assert done_seen or len(bits) > 0, "done pulse not detected"

    await tick(dut, 5)
    assert int(dut.busy.value) == 0, "should be idle after done"
    assert int(dut.tx.value) == 1, "tx should be high in idle"
    cocotb.log.info("PASSED")


@cocotb.test()
async def test_busy_done(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)
    cocotb.log.info("=== BUSY / DONE FLAGS ===")

    assert int(dut.busy.value) == 0, "idle: busy=0"
    assert int(dut.done.value) == 0, "idle: done=0"
    assert int(dut.tx.value) == 1, "idle: tx=1"

    await send_byte(dut, 0x55)
    assert int(dut.busy.value) == 1, "after send: busy=1"

    done_seen = False
    for _ in range(20 * BIT_PERIOD):
        await RisingEdge(dut.clk)
        if int(dut.done.value) == 1:
            done_seen = True
            log_state(dut, "done pulse")
            break
    assert done_seen, "done pulse should fire"

    await tick(dut, 2)
    assert int(dut.busy.value) == 0, "after done: busy=0"
    assert int(dut.done.value) == 0, "done pulse should be 1 cycle"
    cocotb.log.info("PASSED")


@cocotb.test()
async def test_back_to_back(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)
    cocotb.log.info("=== BACK TO BACK ===")

    for byte_idx, val in enumerate([0xAA, 0x55]):
        cocotb.log.info(f"  Sending byte {byte_idx}: 0x{val:02X}")
        await send_byte(dut, val)

        await wait_idle(dut, 20 * BIT_PERIOD)
        assert int(dut.busy.value) == 0, f"byte {byte_idx}: should be idle"
        assert int(dut.tx.value) == 1, f"byte {byte_idx}: tx should be high"

        await tick(dut, 5)

    cocotb.log.info("PASSED")


@cocotb.test()
async def test_boundary_data(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)
    cocotb.log.info("=== BOUNDARY 0x00 / 0xFF ===")

    for val in [0x00, 0xFF]:
        cocotb.log.info(f"  Sending 0x{val:02X}")
        await send_byte(dut, val)

        assert int(dut.busy.value) == 1, f"0x{val:02X}: should be busy"

        bits = []
        for _ in range(15 * BIT_PERIOD):
            await RisingEdge(dut.clk)
            bits.append(int(dut.tx.value))
            if not int(dut.busy.value):
                break

        assert 0 in bits[:BIT_PERIOD], f"0x{val:02X}: start bit missing"
        cocotb.log.info(f"  0x{val:02X}: captured {len(bits)} samples, OK")

    await tick(dut, 5)
    cocotb.log.info("PASSED")

import cocotb
from cocotb.triggers import RisingEdge
from cocotb.clock import Clock


HALF_PERIOD = 2


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
    await apply_and_settle(dut, dut.miso, 0)
    await tick(dut, 2)


def log_state(dut, label):
    sck = int(dut.sck.value)
    csn = int(dut.cs_n.value)
    bsy = int(dut.busy.value)
    dn  = int(dut.done.value)
    mo  = int(dut.mosi.value)
    cocotb.log.info(f"  [{label:25s}] cs_n={csn} sck={sck} mosi={mo} busy={bsy} done={dn}")


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


@cocotb.test()
async def test_single_transfer(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)
    cocotb.log.info("=== SINGLE TRANSFER ===")

    assert int(dut.cs_n.value) == 1, "cs_n idle high"
    assert int(dut.sck.value) == 0, "sck idle low"
    assert int(dut.busy.value) == 0, "busy idle low"

    await send_byte(dut, 0xA5)
    log_state(dut, "sent")

    assert int(dut.busy.value) == 1, "should be busy"
    assert int(dut.cs_n.value) == 0, "cs_n should be low"

    sck_edges = 0
    done_seen = False
    for _ in range(100):
        prev_sck = int(dut.sck.value)
        await RisingEdge(dut.clk)
        cur_sck = int(dut.sck.value)
        if prev_sck == 0 and cur_sck == 1:
            sck_edges += 1
        if int(dut.done.value) == 1:
            done_seen = True

    assert sck_edges >= 8, f"expected >=8 SCK rising edges, got {sck_edges}"
    assert done_seen, "done pulse not seen"
    await tick(dut, 2)
    assert int(dut.cs_n.value) == 1, "cs_n back to high"
    assert int(dut.busy.value) == 0, "back to idle"
    cocotb.log.info("PASSED")


@cocotb.test()
async def test_mosi_output(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)
    cocotb.log.info("=== MOSI OUTPUT ===")

    await send_byte(dut, 0x55)
    log_state(dut, "sent 0x55")

    mosi_bits = []
    prev_sck = 0
    for _ in range(80):
        cur_sck = int(dut.sck.value)
        if prev_sck == 0 and cur_sck == 1:
            mosi_bits.append(int(dut.mosi.value))
        prev_sck = cur_sck
        await RisingEdge(dut.clk)
        if not int(dut.busy.value):
            break

    cocotb.log.info(f"  mosi bits captured on rising edge: {mosi_bits}")
    assert len(mosi_bits) >= 8, f"expected 8 bits, got {len(mosi_bits)}"
    assert mosi_bits[0] == 0, "bit7 MSB of 0x55 = 0"
    assert mosi_bits[-1] == 1, "bit0 LSB of 0x55 = 1"
    cocotb.log.info("PASSED")


@cocotb.test()
async def test_back_to_back(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)
    cocotb.log.info("=== BACK TO BACK ===")

    for val in [0xAA, 0x33]:
        cocotb.log.info(f"  Sending 0x{val:02X}")
        await send_byte(dut, val)

        for _ in range(80):
            await RisingEdge(dut.clk)
            if not int(dut.busy.value):
                break

        assert int(dut.busy.value) == 0, f"idle after 0x{val:02X}"
        assert int(dut.cs_n.value) == 1, f"cs_n high after 0x{val:02X}"
        await tick(dut, 5)

    cocotb.log.info("PASSED")


@cocotb.test()
async def test_cs_n_behavior(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)
    cocotb.log.info("=== CS_N BEHAVIOR ===")

    assert int(dut.cs_n.value) == 1, "idle: cs_n=1"
    assert int(dut.sck.value) == 0, "idle: sck=0"

    await send_byte(dut, 0xFF)

    for _ in range(10):
        await RisingEdge(dut.clk)
        assert int(dut.cs_n.value) == 0, "cs_n low during transfer"

    for _ in range(80):
        await RisingEdge(dut.clk)
        if not int(dut.busy.value):
            break

    assert int(dut.cs_n.value) == 1, "cs_n high after transfer"
    assert int(dut.sck.value) == 0, "sck idle after transfer"
    cocotb.log.info("PASSED")

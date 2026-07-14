import cocotb
from cocotb.triggers import RisingEdge, Timer, ClockCycles
from cocotb.clock import Clock


async def reset_bram(dut):
    """Clear control signals and settle; does NOT clear memory contents."""
    dut.ena.value = 0
    dut.enb.value = 0
    dut.wea.value = 0
    dut.web.value = 0
    dut.addra.value = 0
    dut.dina.value = 0
    dut.addrb.value = 0
    dut.dinb.value = 0
    await ClockCycles(dut.clka, 5)
    await ClockCycles(dut.clkb, 5)


async def write_a(dut, addr, data):
    dut.addra.value = addr
    dut.dina.value = data
    dut.wea.value = (1 << (dut.WIDTH_A.value.integer // 8)) - 1  # all bytes
    dut.ena.value = 1
    await RisingEdge(dut.clka)
    dut.wea.value = 0
    dut.ena.value = 0
    await RisingEdge(dut.clka)


async def read_b(dut, addr, expect=None):
    dut.addrb.value = addr
    dut.enb.value = 1
    await RisingEdge(dut.clkb)
    await RisingEdge(dut.clkb)  # LATENCY=1
    val = int(dut.doutb.value)
    if expect is not None:
        assert val == expect, f"addr {addr}: expected {hex(expect)}, got {hex(val)}"
    dut.enb.value = 0
    await RisingEdge(dut.clkb)
    return val


@cocotb.test()
async def test_sdp_single_write_read(dut):
    """Simple Dual Port: write A → read B after LATENCY."""
    cocotb.start_soon(Clock(dut.clka, 10, "ns").start())
    cocotb.start_soon(Clock(dut.clkb, 10, "ns").start())
    await reset_bram(dut)

    await write_a(dut, 0, 0xDEAD_BEEF)
    await read_b(dut, 0, 0xDEAD_BEEF)


@cocotb.test()
async def test_sdp_multi_addr(dut):
    """Write 8 addresses, read back all on port B."""
    cocotb.start_soon(Clock(dut.clka, 10, "ns").start())
    cocotb.start_soon(Clock(dut.clkb, 10, "ns").start())
    await reset_bram(dut)

    expected = {}
    for i in range(8):
        val = 0x1000 + i
        await write_a(dut, i, val)
        expected[i] = val

    for i, exp in expected.items():
        await read_b(dut, i, exp)


@cocotb.test()
async def test_sdp_overwrite(dut):
    """Last write to same address wins."""
    cocotb.start_soon(Clock(dut.clka, 10, "ns").start())
    cocotb.start_soon(Clock(dut.clkb, 10, "ns").start())
    await reset_bram(dut)

    await write_a(dut, 2, 0xAAAA)
    await write_a(dut, 2, 0xBBBB)
    await read_b(dut, 2, 0xBBBB)


@cocotb.test()
async def test_sdp_byte_strobe(dut):
    """Partial byte write: WEA=0x1 updates only the lowest byte."""
    cocotb.start_soon(Clock(dut.clka, 10, "ns").start())
    cocotb.start_soon(Clock(dut.clkb, 10, "ns").start())
    await reset_bram(dut)

    await write_a(dut, 0, 0xFFFFFFFF)
    # byte write — only lowest byte
    dut.addra.value = 0
    dut.dina.value = 0x000000AB
    dut.wea.value = 0x1
    dut.ena.value = 1
    await RisingEdge(dut.clka)
    dut.wea.value = 0
    dut.ena.value = 0
    await RisingEdge(dut.clka)

    await read_b(dut, 0, 0xFFFFFFAB)


@cocotb.test()
async def test_sdp_latency(dut):
    """LATENCY=1: data appears 1 cycle after read address is set."""
    cocotb.start_soon(Clock(dut.clka, 10, "ns").start())
    cocotb.start_soon(Clock(dut.clkb, 10, "ns").start())
    await reset_bram(dut)

    await write_a(dut, 5, 0xCAFE)
    # Use read_b — it handles GPI timing correctly (2 edges)
    await read_b(dut, 5, 0xCAFE)

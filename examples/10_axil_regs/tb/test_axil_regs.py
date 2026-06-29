import cocotb
from cocotb.triggers import ClockCycles
from cocotb.clock import Clock
from cocotbext.axi import AxiLiteBus, AxiLiteMaster


def to_bytes(val):
    return val.to_bytes(4, "little")

def from_bytes(b):
    return int.from_bytes(b, "little")


@cocotb.test()
async def test_single_write_read(dut):
    """Write one register, read it back."""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())

    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    bus = AxiLiteBus.from_prefix(dut, "s_axil")
    master = AxiLiteMaster(bus, dut.clk, dut.rst_n, reset_active_level=False)

    await master.write(0x00, to_bytes(0xDEAD_BEEF))
    val = from_bytes(await master.read(0x00, 4))
    assert val == 0xDEAD_BEEF, f"expected 0xDEAD_BEEF, got {hex(val)}"


@cocotb.test()
async def test_multi_reg_read_write(dut):
    """Write and read all 4 registers."""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())

    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    bus = AxiLiteBus.from_prefix(dut, "s_axil")
    master = AxiLiteMaster(bus, dut.clk, dut.rst_n, reset_active_level=False)

    for i in range(4):
        await master.write(i * 4, to_bytes(0x1000 + i))

    for i in range(4):
        val = from_bytes(await master.read(i * 4, 4))
        assert val == 0x1000 + i, f"reg[{i}]: expected {hex(0x1000 + i)}, got {hex(val)}"


@cocotb.test()
async def test_write_overwrite(dut):
    """Write, overwrite, read to confirm last write wins."""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())

    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    bus = AxiLiteBus.from_prefix(dut, "s_axil")
    master = AxiLiteMaster(bus, dut.clk, dut.rst_n, reset_active_level=False)

    await master.write(0x04, to_bytes(0xAAAA))
    await master.write(0x04, to_bytes(0xBBBB))
    val = from_bytes(await master.read(0x04, 4))
    assert val == 0xBBBB, f"overwrite: expected 0xBBBB, got {hex(val)}"

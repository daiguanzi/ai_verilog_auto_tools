import cocotb
from cocotb.triggers import RisingEdge, ClockCycles
from cocotb.clock import Clock
from cocotbext.axi import AxiLiteBus, AxiLiteMaster

TAPS = 8
CTRL_ADDR = TAPS * 2 * 4
RES_ADDR  = (TAPS * 2 + 1) * 4

@cocotb.test()
async def debug_test(dut):
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    dut.rst_n.value = 0; await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1; await ClockCycles(dut.clk, 5)
    bus = AxiLiteBus.from_prefix(dut, "s_axil")
    m = AxiLiteMaster(bus, dut.clk, dut.rst_n, reset_active_level=False)
    coeffs = [1 << i for i in range(TAPS)]
    for i, c in enumerate(coeffs):
        await m.write(i * 4, c.to_bytes(4, "little"))
    for i in range(TAPS):
        await m.write((TAPS + i) * 4, (1).to_bytes(4, "little"))
    await m.write(CTRL_ADDR, (1).to_bytes(4, "little"))
    for _ in range(100):
        data = await m.read(CTRL_ADDR, 4)
        if int.from_bytes(data, "little") & 1:
            break
        await RisingEdge(dut.clk)
    data = await m.read(RES_ADDR, 4)
    raw = int.from_bytes(data, "little")
    exp = sum(coeffs)
    cocotb.log.info(f"Expected 0x{exp:08X} ({exp}), Got 0x{raw:08X} ({raw})")
    assert abs(raw - exp) <= 2, f"Mismatch: {raw} vs {exp}"

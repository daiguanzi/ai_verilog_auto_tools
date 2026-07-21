import cocotb
from cocotb.triggers import RisingEdge, ClockCycles
from cocotb.clock import Clock
from cocotbext.axi import AxiLiteBus, AxiLiteMaster


class Scoreboard:
    def __init__(self, name="sb"):
        self.name = name
        self.passed = 0
        self.failed = 0
        self.failures = []

    def check(self, label, exp, got):
        if exp == got:
            self.passed += 1
        else:
            self.failed += 1
            self.failures.append(f"{label}: expected {exp}, got {got}")

    def report(self):
        total = self.passed + self.failed
        cocotb.log.info(f"  [{self.name}] {self.passed}/{total} checks passed")
        assert self.failed == 0, f"{self.name}: {self.failed} fails"


async def reset_dut(dut):
    dut.rst_n.value = 0
    dut.s_axis_tvalid.value = 0
    dut.s_axis_tdata.value = 0
    dut.s_axis_tlast.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)


async def send_stream(dut, data, last=False):
    dut.s_axis_tvalid.value = 1
    dut.s_axis_tdata.value = data
    dut.s_axis_tlast.value = 1 if last else 0
    await RisingEdge(dut.clk)
    dut.s_axis_tvalid.value = 0
    await RisingEdge(dut.clk)


@cocotb.test()
async def test_stream_to_axil(dut):
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)
    bus = AxiLiteBus.from_prefix(dut, "s_axil")
    m = AxiLiteMaster(bus, dut.clk, dut.rst_n, reset_active_level=False)

    # Send 4 stream words: [0xAA, 0xBB, 0xCC, 0xDD with tlast]
    values = [0xAA, 0xBB, 0xCC]
    for v in values:
        await send_stream(dut, v)
    await send_stream(dut, 0xDD, last=True)

    # Read back via AXI-Lite
    sb = Scoreboard("stream")
    for i in range(3):
        data = await m.read(i * 4, 4)
        val = int.from_bytes(data, "little")
        sb.check(f"reg[{i}]", values[i], val)
    # Last reg (idx 3) is 0xDD
    data = await m.read(12, 4)
    sb.check("reg[3]", 0xDD, int.from_bytes(data, "little"))
    sb.report()

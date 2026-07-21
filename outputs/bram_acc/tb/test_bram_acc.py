import cocotb
from cocotb.triggers import RisingEdge, ClockCycles
from cocotb.clock import Clock


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
    dut.wr_en.value = 0
    dut.addr.value = 0
    dut.din.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)


@cocotb.test()
async def test_bram_write_read(dut):
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)

    # Write unique values to BRAM
    data = [i * 111 for i in range(16)]
    for i, v in enumerate(data):
        dut.addr.value = i
        dut.din.value = v
        dut.wr_en.value = 1
        await RisingEdge(dut.clk)
        dut.wr_en.value = 0
        await RisingEdge(dut.clk)

    sb = Scoreboard("bram")
    for i in range(16):
        dut.addr.value = i
        await ClockCycles(dut.clk, 3)  # LATENCY=1 + setup
        val = int(dut.dout.value)
        cocotb.log.info(f"  addr[{i}] = {val} (expected {data[i]})")
        sb.check(f"addr[{i}]", data[i], val)

    sb.report()

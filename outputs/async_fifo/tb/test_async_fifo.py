import cocotb, random
from cocotb.triggers import RisingEdge, ClockCycles, Timer
from cocotb.clock import Clock


DEPTH = 8
DW = 16
MAX_FILL = DEPTH - 1


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
        assert self.failed == 0, f"{self.name}: {self.failed} fails: " + "; ".join(self.failures[:5])


async def reset_fifo(dut):
    dut.wrst_n.value = 0
    dut.rrst_n.value = 0
    dut.wr_en.value = 0
    dut.rd_en.value = 0
    dut.din.value = 0
    await ClockCycles(dut.wclk, 5)
    await ClockCycles(dut.rclk, 5)
    dut.wrst_n.value = 1
    dut.rrst_n.value = 1
    await ClockCycles(dut.wclk, 5)
    await ClockCycles(dut.rclk, 5)


async def write_fifo(dut, data):
    dut.wr_en.value = 1
    dut.din.value = data
    await RisingEdge(dut.wclk)
    dut.wr_en.value = 0
    await RisingEdge(dut.wclk)


async def read_fifo(dut):
    dut.rd_en.value = 1
    await RisingEdge(dut.rclk)
    dut.rd_en.value = 0
    await RisingEdge(dut.rclk)
    return int(dut.dout.value)


@cocotb.test()
async def test_write_read(dut):
    wclk = Clock(dut.wclk, 10, "ns")
    rclk = Clock(dut.rclk, 12, "ns")
    cocotb.start_soon(wclk.start())
    cocotb.start_soon(rclk.start())
    await reset_fifo(dut)

    assert int(dut.empty.value) == 1
    assert int(dut.full.value) == 0

    sb = Scoreboard("wr")
    for i in range(MAX_FILL):
        await write_fifo(dut, i * 100)

    await ClockCycles(dut.rclk, 5)  # CDC settle

    for i in range(MAX_FILL):
        val = await read_fifo(dut)
        sb.check(f"data[{i}]", i * 100, val)

    assert int(dut.empty.value) == 1
    sb.report()


@cocotb.test()
async def test_full_empty(dut):
    wclk = Clock(dut.wclk, 10, "ns")
    rclk = Clock(dut.rclk, 12, "ns")
    cocotb.start_soon(wclk.start())
    cocotb.start_soon(rclk.start())
    await reset_fifo(dut)

    sb = Scoreboard("flags")
    sb.check("init empty", 1, int(dut.empty.value))

    for _ in range(MAX_FILL):
        await write_fifo(dut, 0xAAAA)
    await ClockCycles(dut.wclk, 3)
    sb.check("full", 1, int(dut.full.value))

    for _ in range(MAX_FILL):
        await read_fifo(dut)
    await ClockCycles(dut.rclk, 3)
    sb.check("empty", 1, int(dut.empty.value))

    sb.report()


@cocotb.test()
async def test_random(dut):
    wclk = Clock(dut.wclk, 10, "ns")
    rclk = Clock(dut.rclk, 12, "ns")
    cocotb.start_soon(wclk.start())
    cocotb.start_soon(rclk.start())
    await reset_fifo(dut)

    random.seed(42)
    sb = Scoreboard("rand")
    expected = []

    for _ in range(3):
        for j in range(random.randint(2, MAX_FILL)):
            v = random.randint(0, 65535)
            expected.append(v)
            await write_fifo(dut, v)
        for j in range(len(expected)):
            val = await read_fifo(dut)
            sb.check(f"rand", expected[j], val)
        expected = []

    sb.report()

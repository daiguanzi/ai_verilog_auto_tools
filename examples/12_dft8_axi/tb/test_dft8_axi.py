import cocotb, random, math
from cocotb.triggers import RisingEdge, ClockCycles
from cocotb.clock import Clock
from cocotbext.axi import AxiLiteBus, AxiLiteMaster


# ============================================================
#  Reference model — manual 8-point DFT (no numpy dependency)
# ============================================================

def dft_reference(samples):
    N = 8
    result = []
    for k in range(N):
        acc_r = 0.0
        acc_i = 0.0
        for n in range(N):
            angle = -2.0 * math.pi * k * n / N
            sr, si = samples[n]
            tw_r = math.cos(angle) * 32768.0
            tw_i = math.sin(angle) * 32768.0
            mr = sr * tw_r - si * tw_i
            mi = sr * tw_i + si * tw_r
            acc_r += mr
            acc_i += mi
        val_r = int(acc_r / 32768.0 + (0.5 if acc_r > 0 else -0.5))
        val_i = int(acc_i / 32768.0 + (0.5 if acc_i > 0 else -0.5))
        val_r = max(-32768, min(32767, val_r))
        val_i = max(-32768, min(32767, val_i))
        result.append((val_r & 0xFFFF, val_i & 0xFFFF))
    return result


# ============================================================
#  Scoreboard
# ============================================================

class Scoreboard:
    def __init__(self, name="sb"):
        self.name = name
        self.passed = 0
        self.failed = 0
        self.failures = []

    def check(self, label, exp, got):
        if abs(exp - got) <= 1:
            self.passed += 1
        else:
            self.failed += 1
            self.failures.append(f"{label}: expected {exp}, got {got}")

    def report(self):
        total = self.passed + self.failed
        cocotb.log.info(f"  [{self.name}] {self.passed}/{total} checks passed")
        assert self.failed == 0, f"{self.name}: {self.failed} fails: " + "; ".join(self.failures[:5])


# ============================================================
#  AXI helpers
# ============================================================

CTRL_ADDR = 16 * 4
OUT_BASE  = 24 * 4


async def write_inputs(master, samples):
    for i, (re, im) in enumerate(samples):
        val = ((im & 0xFFFF) << 16) | (re & 0xFFFF)
        await master.write(i * 4, val.to_bytes(4, "little"))


async def start_dft(master):
    await master.write(CTRL_ADDR, (1).to_bytes(4, "little"))


async def wait_done(master, clk, timeout=200):
    for _ in range(timeout):
        data = await master.read(CTRL_ADDR, 4)
        if int.from_bytes(data, "little") & 1:
            return
        await RisingEdge(clk)
    assert False, "DFT did not finish within timeout"


def u16(val):
    return val & 0xFFFF


async def read_outputs(master):
    result = []
    for i in range(8):
        data = await master.read(OUT_BASE + i * 4, 4)
        raw = int.from_bytes(data, "little")
        result.append((u16(raw), u16(raw >> 16)))
    return result


async def run_dft_axi(master, clk, samples):
    await write_inputs(master, samples)
    await start_dft(master)
    await wait_done(master, clk)
    return await read_outputs(master)


# ============================================================
#  Reset helper
# ============================================================

async def reset_dut(dut):
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)


# ============================================================
#  Tests
# ============================================================

@cocotb.test()
async def test_dc_input(dut):
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)

    bus = AxiLiteBus.from_prefix(dut, "s_axil")
    master = AxiLiteMaster(bus, dut.clk, dut.rst_n, reset_active_level=False)

    samples = [(3277, 0)] * 8
    result = await run_dft_axi(master, dut.clk, samples)
    expected = dft_reference(samples)

    sb = Scoreboard("dc")
    for i in range(8):
        sb.check(f"bin[{i}] re", expected[i][0], result[i][0])
        sb.check(f"bin[{i}] im", expected[i][1], result[i][1])
    sb.report()


@cocotb.test()
async def test_single_freq(dut):
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)

    bus = AxiLiteBus.from_prefix(dut, "s_axil")
    master = AxiLiteMaster(bus, dut.clk, dut.rst_n, reset_active_level=False)

    samples = [(int(100 * math.sin(2 * math.pi * n / 8)), 0) for n in range(8)]
    result = await run_dft_axi(master, dut.clk, samples)
    expected = dft_reference(samples)

    sb = Scoreboard("freq1")
    for i in range(8):
        sb.check(f"bin[{i}] re", expected[i][0], result[i][0])
        sb.check(f"bin[{i}] im", expected[i][1], result[i][1])
    sb.report()


@cocotb.test()
async def test_all_zeros(dut):
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)

    bus = AxiLiteBus.from_prefix(dut, "s_axil")
    master = AxiLiteMaster(bus, dut.clk, dut.rst_n, reset_active_level=False)

    samples = [(0, 0)] * 8
    result = await run_dft_axi(master, dut.clk, samples)

    sb = Scoreboard("zeros")
    for i in range(8):
        sb.check(f"bin[{i}] re", 0, result[i][0])
        sb.check(f"bin[{i}] im", 0, result[i][1])
    sb.report()


@cocotb.test()
async def test_random(dut):
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)

    bus = AxiLiteBus.from_prefix(dut, "s_axil")
    master = AxiLiteMaster(bus, dut.clk, dut.rst_n, reset_active_level=False)

    random.seed(42)
    sb = Scoreboard("rand")

    for t in range(5):
        samples = [(random.randint(-500, 500), random.randint(-500, 500))
                    for _ in range(8)]
        result = await run_dft_axi(master, dut.clk, samples)
        expected = dft_reference(samples)
        for i in range(8):
            sb.check(f"t{t} bin[{i}] re", expected[i][0], result[i][0])
            sb.check(f"t{t} bin[{i}] im", expected[i][1], result[i][1])

    sb.report()

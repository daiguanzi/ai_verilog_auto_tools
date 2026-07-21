import cocotb, random
from cocotb.triggers import RisingEdge, ClockCycles
from cocotb.clock import Clock
from cocotbext.axi import AxiLiteBus, AxiLiteMaster


TAPS = 8
DW   = 16
CTRL_ADDR = TAPS * 2 * 4
RES_ADDR  = (TAPS * 2 + 1) * 4


def fir_reference(samples, coeffs):
    result = 0
    for i in range(TAPS):
        result += samples[i] * coeffs[i]
    return result & 0xFFFFFFFF


class Scoreboard:
    def __init__(self, name="sb"):
        self.name = name
        self.passed = 0
        self.failed = 0
        self.failures = []

    def check(self, label, exp, got, tol=1):
        if abs(exp - got) <= tol:
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
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)


async def write_coeffs(master, coeffs):
    for i, c in enumerate(coeffs):
        v = c & 0xFFFF
        await master.write(i * 4, v.to_bytes(4, "little"))


async def write_samples(master, samples):
    for i, s in enumerate(samples):
        v = s & 0xFFFF
        await master.write((TAPS + i) * 4, v.to_bytes(4, "little"))


async def start_fir(master):
    await master.write(CTRL_ADDR, (1).to_bytes(4, "little"))


async def wait_done(master, clk, timeout=200):
    for _ in range(timeout):
        data = await master.read(CTRL_ADDR, 4)
        if int.from_bytes(data, "little") & 1:
            return
        await RisingEdge(clk)
    assert False, "FIR did not finish"


async def read_result(master):
    data = await master.read(RES_ADDR, 4)
    return int.from_bytes(data, "little")


async def run_fir(master, clk, samples, coeffs):
    await write_coeffs(master, coeffs)
    await write_samples(master, samples)
    await start_fir(master)
    await wait_done(master, clk)
    return await read_result(master)


@cocotb.test()
async def test_dc(dut):
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)
    bus = AxiLiteBus.from_prefix(dut, "s_axil")
    master = AxiLiteMaster(bus, dut.clk, dut.rst_n, reset_active_level=False)

    coeffs = [1000] * TAPS
    samples = [100] * TAPS
    result = await run_fir(master, dut.clk, samples, coeffs)
    expected = fir_reference(samples, coeffs)

    sb = Scoreboard("dc")
    sb.check("fir", expected, result)
    sb.report()


@cocotb.test()
async def test_impulse(dut):
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)
    bus = AxiLiteBus.from_prefix(dut, "s_axil")
    master = AxiLiteMaster(bus, dut.clk, dut.rst_n, reset_active_level=False)

    coeffs = [i * 100 for i in range(TAPS)]
    samples = [0] * TAPS
    samples[0] = 1

    result = await run_fir(master, dut.clk, samples, coeffs)
    expected = fir_reference(samples, coeffs)
    assert expected == coeffs[0], f"impulse: {expected} != {coeffs[0]}"

    sb = Scoreboard("impulse")
    sb.check("fir", expected, result)
    sb.report()


@cocotb.test()
async def test_all_zeros(dut):
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)
    bus = AxiLiteBus.from_prefix(dut, "s_axil")
    master = AxiLiteMaster(bus, dut.clk, dut.rst_n, reset_active_level=False)

    coeffs = [42] * TAPS
    samples = [0] * TAPS
    result = await run_fir(master, dut.clk, samples, coeffs)

    sb = Scoreboard("zeros")
    sb.check("fir", 0, result)
    sb.report()


@cocotb.test()
async def test_random(dut):
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)
    bus = AxiLiteBus.from_prefix(dut, "s_axil")
    master = AxiLiteMaster(bus, dut.clk, dut.rst_n, reset_active_level=False)

    random.seed(42)
    sb = Scoreboard("rand")

    for _ in range(5):
        coeffs = [random.randint(-1000, 1000) for _ in range(TAPS)]
        samples = [random.randint(-500, 500) for _ in range(TAPS)]
        result = await run_fir(master, dut.clk, samples, coeffs)
        expected = fir_reference(samples, coeffs)
        sb.check("fir", expected, result, tol=2)

    sb.report()

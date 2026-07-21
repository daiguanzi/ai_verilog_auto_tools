import cocotb, random
from cocotb.triggers import RisingEdge, ClockCycles
from cocotb.clock import Clock
from collections import deque
import math


# ============================================================
#  Reference model — manual 8-point DFT (no numpy dependency)
# ============================================================

def dft_reference(samples):
    """Compute 8-point DFT of a list of 8 complex tuples (real, imag).
    Returns list of 8 (real, imag) tuples.
    Uses twiddle factors scaled by 32768, same as RTL.
    """
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
            # complex multiply: (sr + j*si) * (tw_r + j*tw_i)
            mr = sr * tw_r - si * tw_i
            mi = sr * tw_i + si * tw_r
            acc_r += mr
            acc_i += mi
        # rescale (>>15) and round
        val_r = int(acc_r / 32768.0 + (0.5 if acc_r > 0 else -0.5))
        val_i = int(acc_i / 32768.0 + (0.5 if acc_i > 0 else -0.5))
        # clamp to 16-bit signed
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
        if abs(exp - got) <= 1:  # allow 1-LSB rounding difference
            self.passed += 1
        else:
            self.failed += 1
            self.failures.append(f"{label}: expected {exp}, got {got}")

    def report(self):
        total = self.passed + self.failed
        cocotb.log.info(f"  [{self.name}] {self.passed}/{total} checks passed")
        assert self.failed == 0, f"{self.name}: {self.failed} fails: " + "; ".join(self.failures[:5])


# ============================================================
#  Helpers
# ============================================================

async def reset_dut(dut):
    dut.rst_n.value = 0
    dut.start.value = 0
    for s in ['sr0','sr1','sr2','sr3','sr4','sr5','sr6','sr7',
              'si0','si1','si2','si3','si4','si5','si6','si7']:
        getattr(dut, s).value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)


def set_samples(dut, samples):
    """Drive 8 complex samples into DUT ports, assert start, wait for done."""
    for i in range(8):
        getattr(dut, f"sr{i}").value = samples[i][0]
        getattr(dut, f"si{i}").value = samples[i][1]
    dut.start.value = 1


def to_s16(val):
    """Convert int to 16-bit signed cocotb value."""
    return val & 0xFFFF


async def run_dft(dut, samples):
    set_samples(dut, samples)
    await RisingEdge(dut.clk)
    dut.start.value = 0
    # wait for done
    for _ in range(100):  # max 64 compute cycles + overhead
        await RisingEdge(dut.clk)
        if int(dut.done.value):
            break
    assert int(dut.done.value) == 1, "DFT did not finish"
    result = []
    for i in range(8):
        result.append((int(getattr(dut, f"fr{i}").value) & 0xFFFF,
                        int(getattr(dut, f"fi{i}").value) & 0xFFFF))
    return result


# ============================================================
#  Tests
# ============================================================

@cocotb.test()
async def test_dc_input(dut):
    """DC signal — all samples = (3277, 0). Only bin 0 should be non-zero."""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)

    samples = [(3277, 0)] * 8
    result = await run_dft(dut, samples)
    expected = dft_reference(samples)

    sb = Scoreboard("dc")
    for i in range(8):
        sb.check(f"bin[{i}] real", to_s16(expected[i][0]), to_s16(result[i][0]))
        sb.check(f"bin[{i}] imag", to_s16(expected[i][1]), to_s16(result[i][1]))
    sb.report()


@cocotb.test()
async def test_single_freq(dut):
    """Pure 1Hz sine (1 cycle across 8 samples). Should light up bin 1."""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)

    # sin(2*pi*n/8), n=0..7, scaled by 100
    samples = [(int(100 * math.sin(2 * math.pi * n / 8)), 0) for n in range(8)]
    result = await run_dft(dut, samples)
    expected = dft_reference(samples)

    sb = Scoreboard("freq1")
    for i in range(8):
        sb.check(f"bin[{i}] real", to_s16(expected[i][0]), to_s16(result[i][0]))
        sb.check(f"bin[{i}] imag", to_s16(expected[i][1]), to_s16(result[i][1]))
    sb.report()


@cocotb.test()
async def test_all_zeros(dut):
    """All zeros → all bins zero."""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)

    samples = [(0, 0)] * 8
    result = await run_dft(dut, samples)
    sb = Scoreboard("zeros")
    for i in range(8):
        sb.check(f"bin[{i}] real", 0, result[i][0] & 0xFFFF)
        sb.check(f"bin[{i}] imag", 0, result[i][1] & 0xFFFF)
    sb.report()


@cocotb.test()
async def test_random(dut):
    """Random complex inputs verified against Python reference model."""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await reset_dut(dut)

    random.seed(42)
    sb = Scoreboard("rand")

    for t in range(5):  # 5 random test vectors
        samples = [(random.randint(-500, 500), random.randint(-500, 500))
                    for _ in range(8)]
        result = await run_dft(dut, samples)
        expected = dft_reference(samples)
        for i in range(8):
            sb.check(f"t{t} bin[{i}] real", to_s16(expected[i][0]),
                     to_s16(result[i][0]))
            sb.check(f"t{t} bin[{i}] imag", to_s16(expected[i][1]),
                     to_s16(result[i][1]))

    sb.report()

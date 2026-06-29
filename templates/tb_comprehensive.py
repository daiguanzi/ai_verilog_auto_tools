import cocotb
from cocotb.triggers import RisingEdge
from cocotb.clock import Clock
from collections import deque
import random


# ============================================================
#  Standard Helpers — keep in every testbench
# ============================================================

async def reset_dut(dut):
    """Hold reset for 5+ edges then release. Async reset needs long hold."""
    dut.rst_n.value = 0
    for _ in range(5):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    for _ in range(5):
        await RisingEdge(dut.clk)


async def reset_and_clear(dut):
    """
    Reset + settle ALL control inputs to known values.
    Prevents GPI contamination from previous tests crossing over.
    See knowledge/patterns/robust_test_reset.md
    """
    await reset_dut(dut)
    # TODO: Zero all your control inputs:
    # dut.enable.value = 0
    # await RisingEdge(dut.clk)
    # await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)


async def tick(dut, n=1):
    """Advance N clock cycles (idle waiting)."""
    for _ in range(n):
        await RisingEdge(dut.clk)


def log_state(dut, label):
    """Print DUT state. Customize with your signals."""
    cocotb.log.info(f"  [{label}]")


async def apply_and_settle(dut, signal, value):
    """
    Set a LEVEL control signal and wait for GPI settle (2 edges).
    Use for signals that STAY asserted: enable, up_down, mode, button_in.
    WARNING: The second edge causes one "side effect" (e.g. enable=1
    increments counter by 1 during settle). Account for this in assertions.
    See knowledge/simulator/verilator_cocotb.md
    """
    signal.value = value
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)


async def drive_pulse(dut, signal, value):
    """
    Drive a single-cycle PULSE and wait for registers to settle (3 edges).
    Use for ACTION triggers: send, wr_en, rd_en, coin, strobe.
    The signal is asserted, then cleared on the next edge to prevent
    double-counting. Registered outputs are sampled on edge 3.
    See knowledge/patterns/delayed_input_signal.md
    """
    signal.value = value
    await RisingEdge(dut.clk)
    signal.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)


# ============================================================
#  Reference Model + Scoreboard
#  For non-trivial DUTs, don't hand-write asserts per case.
#  Compute expected values from a SPEC-based golden model and let
#  the scoreboard compare them against the DUT automatically.
# ============================================================

def reference_model(inputs: dict) -> dict:
    """Golden model: expected outputs from inputs, INDEPENDENT of the RTL.

    Write this from the SPEC (not by reading the RTL) — it is the source of
    truth the scoreboard checks the DUT against. Keep it pure Python.

    Example (8-bit adder with 9-bit sum):
        return {"sum": (inputs["a"] + inputs["b"]) & 0x1FF}
    """
    # TODO: implement expected behavior
    return {}


def random_test_sequence(n: int, **ranges):
    """Generate N random test vectors within given ranges.

    Each kwarg key=signal_name, value=(min, max). Yields dicts compatible
    with reference_model() for scoreboard comparison.

    Example:
        seed = 42  # optional: random.seed(seed) for reproducibility
        for vec in random_test_sequence(500, a=(0, 255), b=(0, 255)):
            dut.a.value = vec["a"]
            dut.b.value = vec["b"]
            await RisingEdge(dut.clk)
            await RisingEdge(dut.clk)
            exp = reference_model(vec)["sum"]
            sb.check(f"a={vec['a']},b={vec['b']}", exp, dut.sum.value)
        sb.report()
    """
    for _ in range(n):
        yield {k: random.randint(v[0], v[1]) for k, v in ranges.items()}


class Scoreboard:
    """Compare DUT outputs against reference-model expectations.

    Two usage styles:
      1. Direct  — compare a known expected vs actual right now:
            sb.check("a=1,b=2", expected, dut.sum.value)
      2. Queue   — for streaming/pipelined DUTs, decouple producer/consumer:
            sb.expect(value)     # push expected (e.g. from reference_model)
            sb.observe(value)    # push observed DUT output; pops & compares

    Call sb.report() at the END of a test to assert overall pass/fail.
    """

    def __init__(self, dut=None, name="scoreboard"):
        self.dut = dut
        self.name = name
        self.passed = 0
        self.failed = 0
        self.failures = []
        self._expected = deque()

    def check(self, label, expected, actual):
        exp, act = int(expected), int(actual)
        if act == exp:
            self.passed += 1
            cocotb.log.info(f"  [{self.name}] OK  {label}: {act}")
        else:
            self.failed += 1
            msg = f"{label}: expected {exp}, got {act}"
            self.failures.append(msg)
            cocotb.log.error(f"  [{self.name}] MISMATCH  {msg}")
        return self

    def expect(self, value):
        """Queue an expected value (typically from reference_model)."""
        self._expected.append(int(value))

    def observe(self, actual):
        """Compare an observed DUT output against the oldest queued expected."""
        idx = self.passed + self.failed
        if not self._expected:
            self.failed += 1
            self.failures.append(f"stream[{idx}]: unexpected output {int(actual)} (queue empty)")
            cocotb.log.error(f"  [{self.name}] unexpected output {int(actual)}")
            return
        self.check(f"stream[{idx}]", self._expected.popleft(), actual)

    def report(self):
        total = self.passed + self.failed
        cocotb.log.info(f"  [{self.name}] {self.passed}/{total} checks passed")
        if self._expected:
            cocotb.log.warning(f"  [{self.name}] {len(self._expected)} expected value(s) never observed")
        assert self.failed == 0 and not self._expected, (
            f"{self.name}: {self.failed} mismatch(es): " + "; ".join(self.failures[:10])
        )


# ============================================================
#  Test Scenarios — one @cocotb.test() per scenario
# ============================================================

@cocotb.test()
async def test_reset_behavior(dut):
    """Verify reset initializes outputs correctly."""
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)

    # TODO: Assert post-reset output values
    # assert int(dut.count.value) == 0, "reset should zero count"

    cocotb.log.info("PASSED: reset behavior")


@cocotb.test()
async def test_normal_operation(dut):
    """Verify the primary functional path."""
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)

    # TODO: Test normal operation
    # - For pulsed inputs: use drive_pulse(dut, dut.send, 1)
    # - For level controls: use apply_and_settle(dut, dut.enable, 1)
    # - For waiting: use tick(dut, n)

    cocotb.log.info("PASSED: normal operation")


@cocotb.test()
async def test_boundary_conditions(dut):
    """Verify edge cases (min/max values, overflow, timing bounds)."""
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)

    # TODO: Test boundary conditions
    # - Min/max data values (0x00, 0xFF)
    # - Maximum counter/pointer values
    # - Exactly-at-threshold timing

    cocotb.log.info("PASSED: boundary conditions")


@cocotb.test()
async def test_error_handling(dut):
    """Verify correct behavior on invalid/unexpected inputs."""
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)

    # TODO: Test error handling
    # - Overflow/underflow prevention
    # - Invalid command sequences
    # - Back-to-back rapid operations

    cocotb.log.info("PASSED: error handling")


@cocotb.test()
async def test_against_reference_model(dut):
    """Drive a sequence and check each DUT output against reference_model()."""
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)

    sb = Scoreboard(dut, "ref_check")

    # TODO: replace with real stimulus, signals, and sampling timing.
    # for a, b in [(1, 2), (255, 1), (100, 100)]:
    #     dut.a.value = a
    #     dut.b.value = b
    #     await RisingEdge(dut.clk)
    #     await RisingEdge(dut.clk)          # sample registered outputs here
    #     exp = reference_model({"a": a, "b": b})["sum"]
    #     sb.check(f"a={a},b={b}", exp, dut.sum.value)

    sb.report()
    cocotb.log.info("PASSED: reference-model checks")


@cocotb.test()
async def test_randomized(dut):
    """Random stress test: scoreboard-verify a large number of random inputs.

    Use a fixed seed for reproducibility across CI runs, or set seed=None
    for variation. Pair with reference_model() + Scoreboard().
    """
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_and_clear(dut)

    random.seed(42)  # reproducible
    sb = Scoreboard(dut, "random_seed42")

    # TODO: replace ranges with your DUT signal bounds
    # for vec in random_test_sequence(1000, a=(0, 255), b=(0, 255)):
    #     dut.a.value = vec["a"]
    #     dut.b.value = vec["b"]
    #     await RisingEdge(dut.clk)
    #     await RisingEdge(dut.clk)
    #     exp = reference_model(vec)["sum"]
    #     sb.check(f"a={vec['a']},b={vec['b']}", exp, dut.sum.value)

    sb.report()
    cocotb.log.info("PASSED: randomized test (N vectors via random_test_sequence)")

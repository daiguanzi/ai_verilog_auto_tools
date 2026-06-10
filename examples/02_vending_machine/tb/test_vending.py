import cocotb
from cocotb.triggers import RisingEdge
from cocotb.clock import Clock


A05 = 5
A10 = 10
A15 = 15
A20 = 20


def a(v):
    return int(v)


def log_state(dut, label):
    am = a(dut.amount.value)
    di = a(dut.dispense.value)
    cv = a(dut.change_valid.value)
    ch = a(dut.change.value)
    cocotb.log.info(
        f"  [{label:30s}] amount={am:2d}({am*0.1:.1f}) "
        f"disp={di} cv={cv} chg={ch:2d}({ch*0.1:.1f})"
    )


async def reset_dut(dut):
    dut.rst_n.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)


def clear_inputs(dut):
    dut.coin_05.value = 0
    dut.coin_1.value = 0
    dut.coin_2.value = 0
    dut.cancel.value = 0


async def insert_coin(dut, coin_05=0, coin_1=0, coin_2=0):
    dut.coin_05.value = coin_05
    dut.coin_1.value = coin_1
    dut.coin_2.value = coin_2
    await RisingEdge(dut.clk)
    clear_inputs(dut)
    await RisingEdge(dut.clk)
    disp = a(dut.dispense.value)
    chv = a(dut.change_valid.value)
    chg = a(dut.change.value)
    amt = a(dut.amount.value)
    await RisingEdge(dut.clk)
    return {
        "dispense": disp, "change_valid": chv, "change": chg, "amount": amt,
    }


async def press_cancel(dut):
    dut.cancel.value = 1
    await RisingEdge(dut.clk)
    dut.cancel.value = 0
    await RisingEdge(dut.clk)
    chv = a(dut.change_valid.value)
    chg = a(dut.change.value)
    amt = a(dut.amount.value)
    await RisingEdge(dut.clk)
    return {
        "change_valid": chv, "change": chg, "amount": amt,
    }


@cocotb.test()
async def test_exact_payment(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_dut(dut)
    clear_inputs(dut)
    cocotb.log.info("=== Exact payment (0.5+0.5+0.5=1.5) ===")

    await RisingEdge(dut.clk)
    log_state(dut, "init")

    r = await insert_coin(dut, coin_05=1)
    log_state(dut, "after 1st 0.5 coin")
    assert r["amount"] == A05, f"want 5, got {r['amount']}"
    assert r["dispense"] == 0

    r = await insert_coin(dut, coin_05=1)
    log_state(dut, "after 2nd 0.5 coin (1.0)")
    assert r["amount"] == A10, f"want 10, got {r['amount']}"
    assert r["dispense"] == 0

    r = await insert_coin(dut, coin_05=1)
    log_state(dut, "after 3rd 0.5 coin (1.5)")
    assert r["amount"] == 0, "amount reset"
    assert r["dispense"] == 1, "dispense should fire"
    assert r["change_valid"] == 0, "exact, no change"

    cocotb.log.info("PASSED: exact payment")


@cocotb.test()
async def test_overpayment_2(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_dut(dut)
    clear_inputs(dut)
    cocotb.log.info("=== Overpayment 2.0 ===")

    await RisingEdge(dut.clk)
    r = await insert_coin(dut, coin_2=1)
    log_state(dut, "after 2.0 coin")
    assert r["dispense"] == 1
    assert r["change_valid"] == 1
    assert r["change"] == A05
    assert r["amount"] == 0

    cocotb.log.info("PASSED: overpayment 2.0")


@cocotb.test()
async def test_overpayment_mixed(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_dut(dut)
    clear_inputs(dut)
    cocotb.log.info("=== Overpayment (1.0+1.0=2.0) ===")

    await RisingEdge(dut.clk)
    r = await insert_coin(dut, coin_1=1)
    log_state(dut, "after 1st 1.0 coin")
    assert r["amount"] == A10
    assert r["dispense"] == 0

    r = await insert_coin(dut, coin_1=1)
    log_state(dut, "after 2nd 1.0 coin (>=1.5)")
    assert r["dispense"] == 1
    assert r["change"] == A05
    assert r["amount"] == 0

    cocotb.log.info("PASSED: overpayment mixed")


@cocotb.test()
async def test_cancel_refund(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_dut(dut)
    clear_inputs(dut)
    cocotb.log.info("=== Cancel refund (0.5, then cancel) ===")

    await RisingEdge(dut.clk)
    r = await insert_coin(dut, coin_05=1)
    log_state(dut, "after 0.5 coin")
    assert r["amount"] == A05

    r2 = await press_cancel(dut)
    log_state(dut, "after cancel")
    assert r2["change_valid"] == 1, "refund should fire"
    assert r2["change"] == A05, "refund 0.5"
    assert r2["amount"] == 0, "amount reset"

    cocotb.log.info("PASSED: cancel refund")


@cocotb.test()
async def test_cancel_when_zero(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_dut(dut)
    clear_inputs(dut)
    cocotb.log.info("=== Cancel when zero ===")

    await RisingEdge(dut.clk)
    r = await press_cancel(dut)
    log_state(dut, "cancel pressed")
    assert r["change_valid"] == 0, "no refund when empty"
    assert r["amount"] == 0

    cocotb.log.info("PASSED: cancel when zero")


@cocotb.test()
async def test_two_drinks(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_dut(dut)
    clear_inputs(dut)
    cocotb.log.info("=== Two consecutive drinks ===")

    await RisingEdge(dut.clk)
    r = await insert_coin(dut, coin_2=1)
    log_state(dut, "drink 1: 2.0 coin")
    assert r["dispense"] == 1
    assert r["change"] == A05
    assert r["amount"] == 0

    await RisingEdge(dut.clk)
    r = await insert_coin(dut, coin_1=1)
    log_state(dut, "drink 2: 1.0 coin")
    assert r["dispense"] == 0
    assert r["amount"] == A10

    r = await insert_coin(dut, coin_05=1)
    log_state(dut, "drink 2: 0.5 coin (tot 1.5)")
    assert r["dispense"] == 1
    assert r["change_valid"] == 0
    assert r["amount"] == 0

    cocotb.log.info("PASSED: two drinks")


@cocotb.test()
async def test_pulse_width(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_dut(dut)
    clear_inputs(dut)
    cocotb.log.info("=== Pulse width ===")

    await RisingEdge(dut.clk)
    r = await insert_coin(dut, coin_2=1)
    log_state(dut, "after dispense")
    assert r["dispense"] == 1

    await RisingEdge(dut.clk)
    log_state(dut, "next cycle")
    assert a(dut.dispense.value) == 0, "pulse over"

    cocotb.log.info("PASSED: pulse width")


@cocotb.test()
async def test_simultaneous_coins(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_dut(dut)
    clear_inputs(dut)
    cocotb.log.info("=== Simultaneous 0.5+1.0 ===")

    await RisingEdge(dut.clk)
    r = await insert_coin(dut, coin_05=1, coin_1=1)
    log_state(dut, "after 0.5+1.0")
    assert r["dispense"] == 1
    assert r["change_valid"] == 0
    assert r["amount"] == 0

    cocotb.log.info("PASSED: simultaneous coins")


@cocotb.test()
async def test_cancel_after_partial(dut):
    c = Clock(dut.clk, 10, "ns")
    cocotb.start_soon(c.start())
    await reset_dut(dut)
    clear_inputs(dut)
    cocotb.log.info("=== Cancel after 1.0 ===")

    await RisingEdge(dut.clk)
    r = await insert_coin(dut, coin_1=1)
    log_state(dut, "after 1.0 coin")
    assert r["amount"] == A10

    r2 = await press_cancel(dut)
    log_state(dut, "after cancel")
    assert r2["change_valid"] == 1, "refund"
    assert r2["change"] == A10, "refund 1.0"
    assert r2["amount"] == 0

    cocotb.log.info("PASSED: cancel after partial")

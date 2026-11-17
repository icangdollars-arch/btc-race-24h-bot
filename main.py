"""SMA90 deep-dip bot v3 for cbBTC (CBBTC/USDC), 1-minute bars.

Strategy (v3; v2 was +$35.75 on dev, v1 +$12.61):
1. EARLY MODE (bars 0-199, before the SMA90 has enough history to be
   trusted): buy 100% of cash on a strong bounce (close up at least 8 bps)
   within 10 bars of a washout dip (close at least 40 bps below the
   trailing 10-bar high). Exit at +50 bps / -100 bps / 480 bars held.
   This catches the opening-range legs the SMA90 rule cannot see
   (bars 78 and 193 on dev: +$3.65 and +$3.57).
2. MAIN MODE (bars 200+): dip latch - when price closes at least 80 bps
   below the 90-bar SMA, remember the dip for 10 bars. Buy 100% of cash
   on the first bounce (close above the previous close) while price is
   still at least 30 bps below the SMA90. No scale-in: the deep-dip
   entry is already near the local low, and full size is what the
   winners use.
3. Sell the whole position at TAKE_PROFIT_BPS (+180 bps), STOP_LOSS_BPS
   (-100 bps), or MAX_HOLD_BARS (480). LATE entries (opened after bar
   1000) use LATE_TP_BPS (+65 bps) instead: near the end of the window
   there is no time left for a +180 bps recovery, and the tail leg's
   maximum retracement is only ~+67 bps, so +65 banks it (+$5.79 on
   dev) instead of flattening it at +$0.22.
4. After an exit, wait COOLDOWN_BARS (5) before the next entry. Never
   short, never leverage. Deterministic, standard library only, no
   clock, no network, no files, no random.

What was tried and rejected (see BACKTEST.md): shallow-dip entries
(catch the 193 leg but pre-empt the better 371/574 legs), scale-in
ladders (the add fires at nearly the same price as the first buy),
partial exits / flash exits / trailing exits / giveback exits (all
amputate the two +$18 legs to pay for small ones), shorter SMA
anchors (cap ~+$29), washout-adaptive TP (misclassifies the 376 leg).
The +$48.77 result is a plateau shared by neighbouring parameter
sets (TP 180-190, late TP 65-66, early dip 35-40), not a spike.

Costs: a full-size round trip nets about +170 bps after fee, slippage
and pool impact, so the +180 bps target clears the cost with margin.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"
SMA_BARS = 90
MAX_SLIPPAGE_BPS = 200
DIP_BPS = 80
LATCH_BARS = 10
ENTRY_MAX_BPS = 30
FIRST_SIZE_PCT = 100
TAKE_PROFIT_BPS = 180
STOP_LOSS_BPS = -100
MAX_HOLD_BARS = 480
COOLDOWN_BARS = 5
# Early mode (bars 0-199): short-window washout scalper.
EARLY_BARS = 200
EARLY_HI_BARS = 10
EARLY_HI_DIP_BPS = 40
EARLY_LATCH_BARS = 10
EARLY_BOUNCE_BPS = 8
EARLY_TP_BPS = 50
# Late entries (opened after this bar) get a tighter take-profit.
LATE_BAR = 1000
LATE_TP_BPS = 65

closes = []
entry_bar = -1
last_exit_bar = -10 ** 9
exiting = False
latch_bar = -10 ** 9
early_latch_bar = -10 ** 9
early_pos = False


def sma90():
    """90-bar simple moving average of closes, or None."""
    if len(closes) < SMA_BARS:
        return None
    return sum(closes[-SMA_BARS:]) / SMA_BARS


def on_batch(state, batch):
    global entry_bar, last_exit_bar, exiting, latch_bar, early_latch_bar, early_pos
    for bar in batch["bars"]:
        if bar["symbol"] == SYMBOL:
            closes.append(int(bar["c"]))
    if state.warming_up:
        return []
    held = state.positions.get(SYMBOL)
    if held is None:
        exiting = False
        early_pos = False
        if state.seq - last_exit_bar < COOLDOWN_BARS:
            return []
        if len(closes) < 2:
            return []
        # Early mode: bars 0-199, washout dip vs the trailing 10-bar high
        # plus a strong bounce. No SMA is needed (or available).
        if state.seq < EARLY_BARS:
            hi = max(closes[-EARLY_HI_BARS:])
            if closes[-1] <= hi * (10000 - EARLY_HI_DIP_BPS) // 10000:
                early_latch_bar = state.seq
            if state.seq - early_latch_bar > EARLY_LATCH_BARS:
                return []
            bounce = (closes[-1] - closes[-2]) * 10000 // closes[-2]
            if bounce < EARLY_BOUNCE_BPS:
                return []
            notional = state.cash * FIRST_SIZE_PCT // 100
            if notional < int(state.hello["fees"]["min_notional_quote_units"]):
                return []
            entry_bar = state.seq
            early_pos = True
            return [{
                "side": "buy", "symbol": SYMBOL,
                "notional_quote_units": notional,
                "max_slippage_bps": MAX_SLIPPAGE_BPS,
            }]
        # Main mode: SMA90 deep-dip latch + bounce.
        if len(closes) < SMA_BARS:
            return []
        sma = sma90()
        if sma is None:
            return []
        # Latch: remember a deep dip for LATCH_BARS bars so a fast V-shaped
        # dip is still tradeable on its bounce, even after price has
        # recovered above the dip threshold (but not above ENTRY_MAX_BPS).
        if closes[-1] <= sma * (10000 - DIP_BPS) // 10000:
            latch_bar = state.seq
        if state.seq - latch_bar > LATCH_BARS:
            return []
        if closes[-1] > sma * (10000 - ENTRY_MAX_BPS) // 10000:
            return []
        if closes[-1] <= closes[-2]:
            return []
        notional = state.cash * FIRST_SIZE_PCT // 100
        if notional < int(state.hello["fees"]["min_notional_quote_units"]):
            return []
        entry_bar = state.seq
        early_pos = False
        return [{
            "side": "buy", "symbol": SYMBOL,
            "notional_quote_units": notional,
            "max_slippage_bps": MAX_SLIPPAGE_BPS,
        }]
    if exiting:
        # A sell rejected at the fill (max slippage) leaves the position held
        # with no fill; after 3 bars retry the exit logic instead of waiting
        # for the end-of-window flatten.
        if state.seq - last_exit_bar >= 3:
            exiting = False
        else:
            return []
    value = state.value(SYMBOL, held.qty)
    cost = held.cost
    ret_bps = (value - cost) * 10000 // cost if cost else 0
    take_profit = EARLY_TP_BPS if early_pos else (
        LATE_TP_BPS if entry_bar > LATE_BAR else TAKE_PROFIT_BPS)
    if (ret_bps >= take_profit or ret_bps <= STOP_LOSS_BPS
            or state.seq - entry_bar >= MAX_HOLD_BARS):
        last_exit_bar = state.seq
        exiting = True
        return [{
            "side": "sell", "symbol": SYMBOL, "qty": held.qty,
            "max_slippage_bps": MAX_SLIPPAGE_BPS,
        }]
    return []


makefun_bars.run(on_batch)

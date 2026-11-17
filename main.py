"""Bollinger dip-reversion bot for cbBTC (CBBTC/USDC), 1-minute bars.

Strategy (5 lines):
1. Wait for price to close below the 25-bar Bollinger lower band (mean - 2 sigma)
   and tick up on the next close (bounce confirmation), then buy with 50% of cash.
2. If price is still below the lower band and the position is down at least 50 bps,
   add the remaining cash (scale in once, at a lower average cost).
3. Sell the whole position when it is up 120 bps, down 100 bps, held 360 bars,
   or when price closes back above the 25-bar mean while up at least 60 bps.
4. After an exit, wait 5 bars before the next entry. Never short, never leverage.
5. Deterministic, standard library only, no clock, no network, no files, no random.

Costs: a full-size round trip pays roughly 26-34 bps (4 bps fee + 2 bps slippage
per leg, plus pool impact that grows with size), so the 50% first tranche and
the scale-in keep impact small and every exit target is well above the cost.
"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"
BAND_BARS = 25
BAND_SIGMAS = 2.0
MAX_SLIPPAGE_BPS = 200
TAKE_PROFIT_BPS = 120
STOP_LOSS_BPS = -100
MAX_HOLD_BARS = 360
COOLDOWN_BARS = 5
FIRST_SIZE_PCT = 50
ADD_DIP_BPS = -50
MEAN_EXIT_BPS = 60

closes = []
entry_bar = -1
last_exit_bar = -10 ** 9
tranches = 0
exiting = False


def bands():
    """(mid, lower) of the last BAND_BARS closes, or (None, None)."""
    if len(closes) < BAND_BARS:
        return None, None
    window = closes[-BAND_BARS:]
    mid = sum(window) / BAND_BARS
    var = sum((x - mid) ** 2 for x in window) / BAND_BARS
    return mid, mid - BAND_SIGMAS * math.sqrt(var)


def on_batch(state, batch):
    global entry_bar, last_exit_bar, tranches, exiting
    for bar in batch["bars"]:
        if bar["symbol"] == SYMBOL:
            closes.append(int(bar["c"]))
    if state.warming_up:
        return []
    held = state.positions.get(SYMBOL)
    if held is None:
        exiting = False
        tranches = 0
        if len(closes) < BAND_BARS:
            return []
        if state.seq - last_exit_bar < COOLDOWN_BARS:
            return []
        mid, lower = bands()
        if lower is None or closes[-1] >= lower:
            return []
        if len(closes) < 2 or closes[-1] <= closes[-2]:
            return []
        notional = state.cash * FIRST_SIZE_PCT // 100
        if notional < int(state.hello["fees"]["min_notional_quote_units"]):
            return []
        entry_bar = state.seq
        tranches = 1
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
    mid, lower = bands()
    if mid is None or lower is None:
        return []
    value = state.value(SYMBOL, held.qty)
    cost = held.cost
    ret_bps = (value - cost) * 10000 // cost if cost else 0
    if (tranches == 1 and state.cash >= int(state.hello["fees"]["min_notional_quote_units"])
            and closes[-1] < lower and ret_bps <= ADD_DIP_BPS):
        tranches = 2
        return [{
            "side": "buy", "symbol": SYMBOL,
            "notional_quote_units": state.cash,
            "max_slippage_bps": MAX_SLIPPAGE_BPS,
        }]
    if (ret_bps >= TAKE_PROFIT_BPS or ret_bps <= STOP_LOSS_BPS
            or state.seq - entry_bar >= MAX_HOLD_BARS
            or (closes[-1] >= mid and ret_bps >= MEAN_EXIT_BPS)):
        last_exit_bar = state.seq
        exiting = True
        return [{
            "side": "sell", "symbol": SYMBOL, "qty": held.qty,
            "max_slippage_bps": MAX_SLIPPAGE_BPS,
        }]
    return []


makefun_bars.run(on_batch)

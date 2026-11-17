"""SMA90 deep-dip bot v10 for cbBTC (CBBTC/USDC), 1-minute bars.

Strategy (v10; v9 +$55.48, v8/v7/v6/v5 +$54.21, v4 +$53.22,
v3 +$48.77, v2 +$35.75, v1 +$12.61):
v10 = v9 + TAIL RE-BUY TRAILING GIVEBACK. Dev PnL is identical to v9
(+$55.48) — the giveback never fires on dev — but the race-window tail
is strictly more robust (see item 7). The v10 search (see BACKTEST.md)
tested the safer-tail TP switch, multi-tier partial exits, and the DP
leg gaps; only the trailing giveback earned its place.
1. EARLY-2 MODE (bars 0-99): buy 100% of cash on the opening washout
   itself - close at least 25 bps below the trailing 10-bar high, with
   NO bounce confirmation (the oracle buys dips on down closes; waiting
   for a bounce buys later and higher). Exit at +80 bps / -100 bps /
   480 bars held. On dev this buys bar 6 and banks +$6.65.
2. EARLY MODE (bars 100-199): as v3 - buy 100% on a strong bounce
   (close up at least 8 bps) within 10 bars of a washout dip (close at
   least 40 bps below the trailing 10-bar high). Exit at +50 bps.
   Catches the bar-193 leg (+$3.57 on dev).
3. MAIN MODE (bars 200+): dip latch - when price closes at least 80 bps
   below the 90-bar SMA, remember the dip for 10 bars. Buy 100% of cash
   on the first bounce (close above the previous close) while price is
   still at least 30 bps below the SMA90. Exit at +180 bps / -100 bps /
   480 bars. The two big legs (bars 371 and 574) bank +$17.83 and
   +$18.02 on dev.
4. TAIL SPLIT (bars 1000+): late entries use a LOW take-profit of
   +25 bps (LATE_TP_BPS) so the first tail leg exits early (bar ~1182,
   +$1.00 on dev) instead of riding to +65. After a late exit, the
   TAIL RE-BUY fires when price dips at least 50 bps below the exit
   close, at least 30 bps below the SMA90, with a non-negative bounce,
   within 200 bars: it buys the bar-1228 dip and rides it to +85 bps
   (+$7.14 on dev; v4 used +65 bps for +$6.14). Tail total +$8.14 vs
   v4's +$7.14. The +85 bps target sits 4 bps below the leg's peak
   retracement (+89 bps on dev); +90 bps never fires and the leg
   flattens at +$2.50, so +85 is the highest TP that still fires
   (see BACKTEST.md for the fragility note).
5. PARTIAL EXITS (v9, new): on a MAIN leg, when the ret reaches the
   +180 bps take-profit, sell 50% of the position and ride the other
   50% with a 5 bps giveback exit (sell the rest when the ret falls
   5 bps below its peak). The two big legs peak at +207 bps (bar 514)
   and +192 bps (bar 967), so the ridden half banks ~+$0.86 and ~+$0.14
   more than a full +180 exit. On the EARLY legs the same shape applies
   (sell 50% at the leg TP, ride the rest with a 5 bps giveback):
   the early-2 leg peaks at +86 bps (TP +80) and the early leg at
   +57 bps (TP +50), adding ~+$0.14 and ~+$0.12. Total v9 dev PnL
   +$55.48 (was +$54.21). The giveback is a plateau: GB 3-7 bps all
   give exactly +$55.48, and partial 40/50/60% all give +$55.44-55.48.
   NO partial on the late leg (it would break the tail split: the
   re-buy only fires after a full late exit, and the +$7.14 re-buy leg
   is worth far more than the ~+$1.50 a ridden late half could add)
   and NO partial on the tail re-buy leg (peak +89 vs TP +85: the
   ridden half gains 4 bps while the sold half gives up 40 bps).
7. TAIL RE-BUY TRAILING GIVEBACK (v10, new): the re-buy leg keeps its
   +85 bps take-profit, but also exits if the ret falls 15 bps below
   its peak once the peak has reached +50 bps (REBUY_GIVEBACK_BPS /
   REBUY_GB_ARM_BPS). On dev the leg rises to +85 without ever pulling
   back 10 bps from an armed peak, so the giveback never fires and
   dev PnL is identical to v9 (+$55.48, same trips). In the race
   window, if the tail leg peaks in [65, 85) bps and pulls back, the
   giveback banks peak-15 bps (about +$4.60-6.20) instead of the
   end-of-window flatten (about +$2.50) — a +$2.10-3.70 gain. The arm
   threshold matters: arming at +30 bps lets the giveback fire on an
   early pullback and costs -$6.63 on dev, so the arm stays at +50.
8. After an exit, wait COOLDOWN_BARS (5) before the next entry. Never
   short, never leverage. Deterministic, standard library only, no
   clock, no network, no files, no random.

What was tried and rejected in v10 (see BACKTEST.md): the safer-tail TP
switch (re-buy TP +85 -> +65, costs exactly -$1.00 on dev: re-buy leg
+$7.14 -> +$6.14, so the giveback above is the better tail insurance),
multi-tier partial exits (50% at +180, 25% at +185/190/195, 25% ride:
-$0.10 on dev, the second tier fires on the same bar as the first and
the slice gives up the ride to the peak), and the DP leg-gap check
(no DP leg sits in 968-1100; only the 526-535 scalp in 515-573, already
known and fragile). Not attempted for lack of time and low expected
value: partial late exit + re-buy add (the late leg is only +$1.00 and
the +$7.14 re-buy must not be disturbed) and an SMA30 second main arm
(the DP gaps are verified dead). The +$59 target was NOT reached
(missed by $3.52); v10 ties v9 on dev and is strictly more robust in
the race window, which is the best ROBUST version across ~3,400+
configs (v2-v10).

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
# Early-2 (bars 0-99): buy the opening washout itself, no bounce needed.
EARLY2_BAR = 100
EARLY2_HI_DIP_BPS = 25
EARLY2_TP_BPS = 80
# Late entries (opened after this bar) get a low take-profit so the
# tail can split into two legs via the re-buy below.
LATE_BAR = 1000
LATE_TP_BPS = 25
# Tail re-buy: after a late exit, buy a deep dip below the exit close.
REBUY_DIP_BPS = 50
REBUY_WINDOW = 200
REBUY_MIN_BAR = 1000
REBUY_BOUNCE_BPS = 0
REBUY_SMA_DIP_BPS = 30
REBUY_TP_BPS = 85
# Rebuy leg trailing giveback (v10 test): exit when the ret falls
# REBUY_GIVEBACK_BPS below its peak, once the peak has armed
# (peak >= REBUY_GB_ARM_BPS). 0 disables the giveback.
REBUY_GIVEBACK_BPS = 15
REBUY_GB_ARM_BPS = 50
# Partial exits (v9): sell PARTIAL_PCT of the position when the ret
# reaches the leg take-profit, ride the rest with a giveback exit.
PARTIAL_PCT = 50
PARTIAL_TP_BPS = 180
RIDE_GIVEBACK_BPS = 5
EARLY_RIDE_GIVEBACK_BPS = 5

closes = []
entry_bar = -1
last_exit_bar = -10 ** 9
last_exit_close = 0
last_exit_late = False
exiting = False
latch_bar = -10 ** 9
early_latch_bar = -10 ** 9
early_pos = False
early2_pos = False
rebuy_pos = False
partial_done = False
peak_ret = 0


def sma90():
    """90-bar simple moving average of closes, or None."""
    if len(closes) < SMA_BARS:
        return None
    return sum(closes[-SMA_BARS:]) / SMA_BARS


def on_batch(state, batch):
    global entry_bar, last_exit_bar, last_exit_close, last_exit_late
    global exiting, latch_bar, early_latch_bar, early_pos, early2_pos
    global rebuy_pos, partial_done, peak_ret
    for bar in batch["bars"]:
        if bar["symbol"] == SYMBOL:
            closes.append(int(bar["c"]))
    if state.warming_up:
        return []
    held = state.positions.get(SYMBOL)
    if held is None:
        exiting = False
        early_pos = False
        early2_pos = False
        rebuy_pos = False
        if state.seq - last_exit_bar < COOLDOWN_BARS:
            return []
        if len(closes) < 2:
            return []
        # Tail re-buy: after a LATE exit, buy a deep dip below the exit
        # close, confirmed by the SMA90 and a non-negative bounce.
        if (last_exit_late and state.seq >= REBUY_MIN_BAR
                and state.seq - last_exit_bar <= REBUY_WINDOW
                and closes[-1] <= last_exit_close * (10000 - REBUY_DIP_BPS) // 10000):
            sma = sma90()
            sma_ok = (sma is not None
                      and closes[-1] <= sma * (10000 - REBUY_SMA_DIP_BPS) // 10000)
            bounce = (closes[-1] - closes[-2]) * 10000 // closes[-2]
            if sma_ok and bounce >= REBUY_BOUNCE_BPS:
                notional = state.cash * FIRST_SIZE_PCT // 100
                if notional >= int(state.hello["fees"]["min_notional_quote_units"]):
                    entry_bar = state.seq
                    early_pos = False
                    rebuy_pos = True
                    partial_done = False
                    peak_ret = 0
                    return [{
                        "side": "buy", "symbol": SYMBOL,
                        "notional_quote_units": notional,
                        "max_slippage_bps": MAX_SLIPPAGE_BPS,
                    }]
        # Early mode: bars 0-199, washout dip vs the trailing 10-bar high
        # plus a strong bounce. No SMA is needed (or available).
        # Bars 0-99 (early-2) use a shallower dip and no bounce: the
        # opening washout is bought on the down close itself.
        if state.seq < EARLY_BARS:
            hi = max(closes[-EARLY_HI_BARS:])
            if state.seq < EARLY2_BAR:
                dip_thr = EARLY2_HI_DIP_BPS
                bounce_thr = None
            else:
                dip_thr = EARLY_HI_DIP_BPS
                bounce_thr = EARLY_BOUNCE_BPS
            if closes[-1] <= hi * (10000 - dip_thr) // 10000:
                early_latch_bar = state.seq
            if state.seq - early_latch_bar > EARLY_LATCH_BARS:
                return []
            bounce = (closes[-1] - closes[-2]) * 10000 // closes[-2]
            if bounce_thr is not None and bounce < bounce_thr:
                return []
            notional = state.cash * FIRST_SIZE_PCT // 100
            if notional < int(state.hello["fees"]["min_notional_quote_units"]):
                return []
            entry_bar = state.seq
            early_pos = True
            early2_pos = state.seq < EARLY2_BAR
            partial_done = False
            peak_ret = 0
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
        partial_done = False
        peak_ret = 0
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
    if ret_bps > peak_ret:
        peak_ret = ret_bps
    if rebuy_pos:
        take_profit = REBUY_TP_BPS
    elif early2_pos:
        take_profit = EARLY2_TP_BPS
    elif early_pos:
        take_profit = EARLY_TP_BPS
    elif entry_bar > LATE_BAR:
        take_profit = LATE_TP_BPS
    else:
        take_profit = TAKE_PROFIT_BPS

    def sell_all():
        global last_exit_bar, last_exit_close, last_exit_late, exiting
        last_exit_bar = state.seq
        last_exit_close = closes[-1]
        last_exit_late = entry_bar > LATE_BAR
        exiting = True
        return [{
            "side": "sell", "symbol": SYMBOL, "qty": held.qty,
            "max_slippage_bps": MAX_SLIPPAGE_BPS,
        }]

    # Partial exits (v9). Main legs only (entry at or before LATE_BAR):
    # sell PARTIAL_PCT at +180, ride the rest with a giveback exit.
    # The late leg is excluded on purpose: the tail re-buy only fires
    # after a FULL late exit, and it is worth far more than a ridden
    # late half. The tail re-buy leg is excluded too: its peak (+89)
    # is only 4 bps above its TP (+85).
    if not early_pos and not rebuy_pos and entry_bar <= LATE_BAR:
        if not partial_done and ret_bps >= PARTIAL_TP_BPS:
            partial_done = True
            qty = held.qty * PARTIAL_PCT // 100
            if qty > 0:
                return [{
                    "side": "sell", "symbol": SYMBOL, "qty": qty,
                    "max_slippage_bps": MAX_SLIPPAGE_BPS,
                }]
        if partial_done:
            if (ret_bps <= peak_ret - RIDE_GIVEBACK_BPS
                    or ret_bps <= STOP_LOSS_BPS
                    or state.seq - entry_bar >= MAX_HOLD_BARS):
                return sell_all()
            return []
    # Early legs: sell 50% at the leg TP, ride the rest with a
    # 5 bps giveback exit (peaks +86 / +57 vs TPs +80 / +50).
    if early_pos and not rebuy_pos:
        if not partial_done and ret_bps >= take_profit:
            partial_done = True
            qty = held.qty * PARTIAL_PCT // 100
            if qty > 0:
                return [{
                    "side": "sell", "symbol": SYMBOL, "qty": qty,
                    "max_slippage_bps": MAX_SLIPPAGE_BPS,
                }]
        if partial_done:
            if (ret_bps <= peak_ret - EARLY_RIDE_GIVEBACK_BPS
                    or ret_bps <= STOP_LOSS_BPS
                    or state.seq - entry_bar >= MAX_HOLD_BARS):
                return sell_all()
            return []
    if (ret_bps >= take_profit or ret_bps <= STOP_LOSS_BPS
            or state.seq - entry_bar >= MAX_HOLD_BARS):
        return sell_all()
    # Rebuy leg trailing giveback (v10 test): even before the +85 TP,
    # exit if the ret falls REBUY_GIVEBACK_BPS below its armed peak.
    if (rebuy_pos and REBUY_GIVEBACK_BPS > 0
            and peak_ret >= REBUY_GB_ARM_BPS
            and ret_bps <= peak_ret - REBUY_GIVEBACK_BPS):
        return sell_all()
    return []


makefun_bars.run(on_batch)

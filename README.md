[![make.fun · btc-race-24h-20261117-0603](https://make.fun/badge/btc-race-24h-20261117-0603.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)
[![rank](https://make.fun/badge/btc-race-24h-20261117-0603/icangdollars-arch/btc-race-24h-bot/rank.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)
[![reward](https://make.fun/badge/btc-race-24h-20261117-0603/icangdollars-arch/btc-race-24h-bot/reward.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)

# BTC Race Bot v10 — SMA90 Deep-Dip + Early-2 + Tail Split + Partial Exits + Tail Giveback (CBBTC/USDC)

> **v10 = v9 + tail re-buy trailing giveback: +$55.48 on dev** (identical
> to v9 — the giveback never fires on dev). The re-buy leg keeps its
> +85 bps take-profit but also exits if the ret falls 15 bps below its
> peak once the peak has reached +50 bps: in the race window, if the
> tail leg peaks in [65, 85) bps, v10 banks peak−15 bps (~+$4.60–6.20)
> instead of the end-of-window flatten (~+$2.50). The safer-tail TP
> switch (+85 → +65) was tested and rejected: it costs exactly −$1.00
> on dev, while the giveback insures the same band for free.
> Multi-tier partial exits were also tested (−$0.10) and rejected.
> Target +$59 was missed by $3.52. See `BACKTEST.md` for the full
> numbers and the recommendation to submit v10.

Entry for make.fun competition `btc-race-24h-20261117-0603`: a long-only
trading bot for cbBTC against USDC on 1-minute bars, speaking
`agent-fun/bars-replay/v1` (NDJSON on stdin/stdout).

## Strategy

1. **Early-2 mode (bars 0–99):** buy 100% of cash on the opening
   washout itself — close ≥ 25 bps below the trailing 10-bar high,
   with NO bounce confirmation (the oracle buys dips on down closes;
   waiting for a bounce buys later and higher). Exit at +80 bps /
   −100 bps / 480 bars held. On dev this buys bar 6 and banks +$6.65,
   replacing v3's bounce-confirmed bar-78 leg (+$3.65).
2. **Early mode (bars 100–199):** buy 100% of cash on a strong bounce
   (close up ≥ 8 bps) within 10 bars of a washout dip (close ≥ 40 bps
   below the trailing 10-bar high). Exit at +50 bps / −100 bps /
   480 bars held. Catches the bar-193 leg (+$3.57 on dev).
3. **Main mode (bars 200+):** dip latch — when price closes at least
   80 bps below the 90-bar SMA, remember the dip for 10 bars. Buy 100%
   of cash on the first bounce (close above the previous close) while
   price is still at least 30 bps below the SMA90. No scale-in: the
   deep-dip entry is already near the local low, and full size is what
   the winners use. Sell at +180 bps / −100 bps / 480 bars held. The
   two big legs (bars 371 and 574) bank +$17.83 and +$18.02 on dev.
4. **Tail split (bars 1000+):** late entries use a LOW take-profit of
   +25 bps, so the first tail leg exits early (bar ~1182, +$1.00 on
   dev). After a late exit, the **tail re-buy** fires when price dips
   ≥ 50 bps below the exit close, ≥ 30 bps below the SMA90, with a
   non-negative bounce, within 200 bars: it buys the bar-1228 dip and
   rides it to +85 bps (+$7.14 on dev; v4 used +65 bps for +$6.14).
   Tail total +$8.14 vs v4's +$7.14. The +85 bps target sits 4 bps
   below the leg's peak retracement (+89 bps on dev); +90 bps never
   fires, so +85 is the highest TP that still fires (see `BACKTEST.md`
   for the fragility note).
5. **Partial exits (v9):** on a main leg, when the ret reaches the
   +180 bps take-profit, sell 50% of the position and ride the other
   50% with a 5 bps giveback exit (sell the rest when the ret falls
   5 bps below its peak). The two big legs peak at +207 bps (bar 514)
   and +192 bps (bar 967), so the ridden half banks ~+$0.86 and
   ~+$0.14 more than a full +180 exit. The same shape applies to the
   early legs (sell 50% at the leg TP, ride with a 5 bps giveback):
   the early-2 leg peaks at +86 bps (TP +80) and the early leg at
   +57 bps (TP +50), adding ~+$0.14 and ~+$0.12. No partial on the
   late leg (the tail re-buy only fires after a full late exit) or on
   the tail re-buy leg (peak +89 vs TP +85 — the ridden half would
   gain 4 bps while the sold half gives up 40 bps).
6. **Tail re-buy trailing giveback (v10):** the re-buy leg keeps its
   +85 bps take-profit, but also exits if the ret falls 15 bps below
   its peak once the peak has reached +50 bps. On dev the leg rises
   to +85 without ever pulling back 10 bps from an armed peak, so the
   giveback never fires and dev PnL is identical to v9. In the race
   window it insures the [65, 85) peak band (see `BACKTEST.md`).
6. After an exit, wait 5 bars before the next entry. Never short, never
   leverage. Max slippage on every order is 200 bps.
7. Deterministic, standard library only. No clock, no network, no files,
   no randomness. The kit SDK shim is vendored byte-for-byte under
   `vendor/makefun_bars.py`.

## Why this shape

The dev window is range-bound (buy-and-hold nets only about +$1 after
costs; the price stays inside roughly $63.9k–$65.5k with 6.4 bps/min
volatility). Trend-following whipsaws badly there (EMA-cross loses about
−$106 in backtest). Only three deep-dip clusters exist in the window,
so the bot trades them (371→514, 574→960, 1101→1292, +$17.83, +$18.02,
+$8.14 split) plus two opening-range legs the SMA90 cannot see — 6 round
trips on dev, no losing trip. The two big legs need +180 bps to be
realised, so the bot lets them run instead of exiting early: every
full early-exit variant tested (flash exits, trailing exits, giveback
exits) scored worse, because an early exit amputates a +$18 leg to
pay for a +$3 one, and there are no spare deep dips to re-enter on —
but a PARTIAL exit works, because the first half still banks the
+180 and only the ridden half chases the peak (see point 5 above).
Measured fees on dev are $4.94 for 16 fills, so the +180 bps target
clears the round-trip cost with wide margin.

v1 of this bot was a 25-bar Bollinger dip-reversion (50% + scale-in,
TP +120) at +$12.61 on dev; v2 was the SMA90 deep-dip rule at +$35.75;
v3 added the early mode and the late-entry TP to reach +$48.77; v4 adds
the early-2 opening buy (no bounce) and the tail split (low late TP +
tail re-buy) to reach +$53.22; v5 raises only the tail re-buy TP from
+65 to +85 bps to reach +$54.21; v6 searched ~50 further configurations
(giveback exits, an independent SMA180 arm, skipping the 193 leg, TP /
dip / cooldown / max-hold / latch / stop-loss sweeps) and found nothing
better, so v6 keeps the v5 rule set unchanged at +$54.21; v7 chased the
live #1 ($78.10, exactly the +$78.07 oracle ceiling) with a full swing
scan, an oracle DP leg list, a medium-TP micro-arm grinder (with and
without an SMA trend filter), bar-dependent TP, strong-bounce entries,
late-TP variants, a main-TP-80 + mid re-buy split, an early-2 TP-40 +
early re-buy split, and trough-buy entries — and found nothing better,
so v7 keeps the v6 rule set unchanged at +$54.21; v8 ran a full DP
over all bars (true all-in optimum +$78.08, verified by exact replay)
and tested the only additional flat leg it contains (a post-exit scalp,
+$0.74) — that scalp is a knife-edge and is preserved only as
`add_scalp_fragile.py` in `work_v8/`, NOT in any `main.py`, so v8 keeps
the v7 rule set unchanged at +$54.21; v9 adds partial exits (sell 50%
at the leg TP, ride the rest with a 5 bps giveback) and reaches
+$55.48 — the first robust improvement since v5, and still short of
the +$59 target. See `BACKTEST.md` for the full grid search and the
honest gate verdicts (the +$59 target was not reached; +$55.48 is a
plateau, not a spike — but the re-buy TP+85 sits 4 bps below the leg's
peak retracement, and TP+90 never fires, so flag it when choosing
between v4 and v9).

## Files

- `main.py` — the bot (entrypoint).
- `vendor/makefun_bars.py` — the kit protocol shim, copied byte-for-byte.
- `LICENSE` — MIT.
- `BACKTEST.md` — backtest method and results.

## Local backtest

The backtest harness is a local exact-fill replay simulator (not part of
this repo; it lives outside the submission). It spawns `main.py` as a
subprocess, feeds it the 1,440 dev bars, and applies the fill model
exactly: fee 4 bps, slippage 2 bps, constant-product impact against each
bar's open depth, integer truncation, flatten at the last close.

```text
python3 sim.py ~/workspace/makefun/btc-race-24h-20261117-0603/work_v9/main.py
```

Result on the dev window: net PnL **+$55.48**, 16 filled orders
(6 buys, 10 sells), 6 round trips (+$6.79, +$3.69, +$18.69, +$18.17,
+$1.00, +$7.14), fees $4.94, max drawdown −0.66%. Walk-forward halves:
first 720 bars +$35.70, second 720 bars +$6.74 (the tail split does
not fully fire in the split because the split restarts the bar
counter; in the full window the tail legs total +$8.14).
See `BACKTEST.md`.

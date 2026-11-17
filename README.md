[![make.fun · btc-race-24h-20261117-0603](https://make.fun/badge/btc-race-24h-20261117-0603.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)
[![rank](https://make.fun/badge/btc-race-24h-20261117-0603/icangdollars-arch/btc-race-24h-bot/rank.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)
[![reward](https://make.fun/badge/btc-race-24h-20261117-0603/icangdollars-arch/btc-race-24h-bot/reward.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)

# BTC Race Bot v3 — SMA90 Deep-Dip + Early Leg (CBBTC/USDC)

Entry for make.fun competition `btc-race-24h-20261117-0603`: a long-only
trading bot for cbBTC against USDC on 1-minute bars, speaking
`agent-fun/bars-replay/v1` (NDJSON on stdin/stdout).

## Strategy

1. **Early mode (bars 0–199, before SMA90 is usable):** buy 100% of cash
   on a strong bounce (close up ≥ 8 bps) within 10 bars of a washout dip
   (close ≥ 40 bps below the trailing 10-bar high). Exit at +50 bps /
   −100 bps / 480 bars held. This catches the opening-range legs the
   SMA90 rule cannot see (bars 78 and 193 on dev: +$3.65 and +$3.57).
2. **Main mode (bars 200+):** dip latch — when price closes at least
   80 bps below the 90-bar SMA, remember the dip for 10 bars. Buy 100%
   of cash on the first bounce (close above the previous close) while
   price is still at least 30 bps below the SMA90. No scale-in: the
   deep-dip entry is already near the local low, and full size is what
   the winners use.
3. **Sell the whole position at +180 bps, −100 bps, or 480 bars held.
   Late entries (opened after bar 1000) use +65 bps instead:** near the
   end of the window there is no time left for a +180 bps recovery, and
   the tail leg's maximum retracement is only ~+67 bps, so +65 banks it
   (+$5.79 on dev) instead of flattening it at +$0.22.
4. After an exit, wait 5 bars before the next entry. Never short, never
   leverage. Max slippage on every order is 200 bps.
5. Deterministic, standard library only. No clock, no network, no files,
   no randomness. The kit SDK shim is vendored byte-for-byte under
   `vendor/makefun_bars.py`.

## Why this shape

The dev window is range-bound (buy-and-hold nets only about +$1 after
costs; the price stays inside roughly $63.9k–$65.5k with 6.4 bps/min
volatility). Trend-following whipsaws badly there (EMA-cross loses about
−$106 in backtest). Only three deep-dip clusters exist in the window,
so the bot trades them (371→514, 574→960, 1101→1292, +$17.79, +$17.97,
+$5.79) plus two opening-range legs the SMA90 cannot see — 5 round
trips on dev, no losing trip. The two big legs need +180 bps to be
realised, so the bot lets them run instead of exiting early: every
early-exit variant tested (flash exits, partial exits, trailing exits,
giveback exits) scored worse, because an early exit amputates a +$18
leg to pay for a +$3 one, and there are no spare deep dips to re-enter
on. Measured fees on dev are $4.08 for 10 fills, so the +180 bps target
clears the round-trip cost with wide margin.

v1 of this bot was a 25-bar Bollinger dip-reversion (50% + scale-in,
TP +120) at +$12.61 on dev; v2 was the SMA90 deep-dip rule at +$35.75;
v3 adds the early mode and the late-entry TP to reach +$48.77. See
`BACKTEST.md` for the full grid search and the honest gate verdicts
(the +$50 target was not reached robustly; +$48.77 is a plateau, not a
spike).

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
python3 sim.py ~/workspace/makefun/btc-race-24h-20261117-0603/work_v3/main.py
```

Result on the dev window: net PnL **+$48.77**, 10 filled orders
(5 buys, 5 sells), 5 round trips (+$3.65, +$3.57, +$17.79, +$17.97,
+$5.79), fees $4.08, max drawdown −0.72%. Walk-forward halves:
first 720 bars +$31.51, second 720 bars +$0.29 (the late-entry TP
does not fire in the split because the split restarts the bar
counter; in the full window the tail leg alone is +$5.79).
See `BACKTEST.md`.

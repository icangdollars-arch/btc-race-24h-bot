[![make.fun · btc-race-24h-20261117-0603](https://make.fun/badge/btc-race-24h-20261117-0603.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)
[![rank](https://make.fun/badge/btc-race-24h-20261117-0603/icangdollars-arch/btc-race-24h-bot/rank.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)
[![reward](https://make.fun/badge/btc-race-24h-20261117-0603/icangdollars-arch/btc-race-24h-bot/reward.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)

# BTC Race Bot — Bollinger Dip-Reversion (CBBTC/USDC)

Entry for make.fun competition `btc-race-24h-20261117-0603`: a long-only
trading bot for cbBTC against USDC on 1-minute bars, speaking
`agent-fun/bars-replay/v1` (NDJSON on stdin/stdout).

## Strategy

1. Wait for price to close below the 25-bar Bollinger lower band
   (mean − 2 standard deviations of closes) and tick up on that close
   (bounce confirmation), then buy with 50% of cash.
2. If price is still below the lower band and the position is down at least
   50 bps, add the remaining cash (scale in once, at a lower average cost).
3. Sell the whole position when it is up 120 bps, down 100 bps, held
   360 bars, or when price closes back above the 25-bar mean while up at
   least 60 bps.
4. After an exit, wait 5 bars before the next entry. Never short, never
   leverage. Max slippage on every order is 200 bps.
5. Deterministic, standard library only. No clock, no network, no files,
   no randomness. The kit SDK shim is vendored byte-for-byte under
   `vendor/makefun_bars.py`.

## Why this shape

The dev window is range-bound (buy-and-hold nets only about +$1 after
costs; the price stays inside roughly $63.9k–$65.5k with 6.4 bps/min
volatility). Trend-following whipsaws badly there (EMA-cross loses about
−$106 in backtest). Mean reversion to the band mean is the repeatable
edge: the chosen bot won all 4 of its round trips on the dev window and
was profitable in both halves of the window.

A full-size round trip costs roughly 26–34 bps (4 bps fee + 2 bps
slippage per leg, plus pool impact that grows with size), so the 50%
first tranche and the scale-in keep impact small and every exit target
is well above the cost.

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
python3 /tmp/sim.py ~/workspace/makefun/btc-race-24h-20261117-0603/work/main.py
```

Result on the dev window: net PnL **+$12.61**, 10 filled orders
(6 buys, 4 sells), 4 round trips all winning (+$5.72, +$2.92, +$2.90,
+$1.07), fees $2.42, max drawdown −1.32%. See `BACKTEST.md`.

# Backtest — BTC race bot (`btc-race-24h-20261117-0603`)

Date: 2026-11-17. Dev window: 1,440 one-minute bars of CBBTC.
Start capital $1,000 paper, long only.

## Dev window analysis

- Price: open $64,433.84 → close $64,775.95 (+0.49% buy-and-hold gross).
  Range $63,874.36–$65,466.84. Max drawdown of buy-and-hold −2.12%.
- 1-minute log returns: mean +0.03 bps, standard deviation 6.43 bps.
  141/1,440 bars flat, 116 bars with zero return.
- Hourly moves mostly within ±0.7%; the largest up hour was +1.30%.
- Rolling 60-minute returns: mean +0.03%, SD 0.52%, 10th pct −0.67%,
  90th pct +0.61%, max +1.96%, min −2.06%.
- Open pool depth: median ~$880k USDC, so a $1,000 trade moves its own
  price ~11 bps per leg; a full-size round trip costs roughly 26–34 bps
  all-in (4 bps fee + 2 bps slippage per leg + impact).
- Conclusion: range-bound, low-volatility window. Trend-following
  whipsaws; mean reversion to the band mean is the repeatable edge.

## Method

Docker was not available, so the kit `grade-local --driver docker` path
could not run. I wrote a local exact-fill replay simulator (`/tmp/sim.py`,
kept outside this repo) that spawns the bot as a subprocess over NDJSON,
feeds it the 1,440 dev bars, and applies the fill model exactly as the
harness source specifies: fee 4 bps, slippage 2 bps, constant-product
impact against each bar's open depth (single hop, integer truncation),
decision checks (cash, weight, min notional, max slippage 200 bps),
and flatten at the last close against its close depth.

Calibration check: the simulator reproduces the expected baselines —
buy-and-hold +$1.07 (1 trade, fees $0.80, max DD −2.12%) and hold-cash
exactly $0.00 (0 trades).

Backtest command (run from anywhere):

```text
python3 /tmp/sim.py ~/workspace/makefun/btc-race-24h-20261117-0603/work/main.py
```

## Chosen bot — Bollinger dip-reversion, 25-bar band, 2 sigma

Parameters: band 25 bars, 2.0 sigma, bounce confirmation, first tranche
50% of cash, scale-in with the remaining cash if price is still below the
lower band and the position is down ≥50 bps, exit at +120 bps / −100 bps /
360 bars held / close back above the band mean while up ≥60 bps,
5-bar cooldown after an exit, max slippage 200 bps.

| Metric | Value |
|---|---|
| Net PnL (dev) | **+$12.61** |
| Final cash | $1,012.61 |
| Return | +1.26% |
| Filled orders | 10 (6 buys, 4 sells) |
| Round trips | 4, all winning: +$5.72, +$2.92, +$2.90, +$1.07 |
| Fees paid | $2.42 |
| Max drawdown | −1.32% |
| Rejected orders | 0 |
| Exit code | 0 |

Walk-forward halves (each restarted at $1,000): first 720 bars +$8.64
(2 winning trips), second 720 bars +$3.95 (2 winning trips). Both halves
positive. Identical result with hello seeds 1 and 7 (deterministic).

## Baselines (same simulator, Python ports of the kit baselines)

| Bot | Net PnL | Fills | Fees | Max DD |
|---|---|---|---|---|
| buy-and-hold | +$1.07 | 1 | $0.80 | −2.12% |
| hold-cash | $0.00 | 0 | $0.00 | 0.00% |
| momentum (24-bar) | +$2.45 | 1 | $0.80 | −2.12% |
| ema-cross (8/21) | −$106.21 | 68 | $25.74 | −10.96% |
| rsi-bollinger | −$24.25 | 11 | $4.75 | −2.79% |
| adx-momentum | −$32.66 | 26 | $10.26 | −3.60% |

Note: the baseline ports are my Python re-implementations of the kit
TypeScript baselines, run through the same simulator; the EMA-cross
loss is dominated by whipsaw (34 round trips averaging about −0.24%
each before fees), not by a simulator error — the same simulator gives
the expected buy-and-hold and hold-cash results.

## Parameter variants tried (all verified end-to-end via the simulator)

| Variant | Net PnL | Fills | Round trips | Max DD |
|---|---|---|---|---|
| V1 — SMA-60 dip ≥60 bps, RSI ≤35, bounce, TP +120 / SL −120, hold 240, full size | +$16.11 | 6 | +$13.48, +$4.17, −$1.54 | −1.47% |
| V2 — Bollinger 20-bar, full size, TP +150, hold 180, no mean exit | +$15.43 | 8 | −$2.05, +$14.71, +$3.54, −$0.76 | −0.86% |
| V3 — Bollinger 20-bar, 50% + scale-in, mean exit +60 bps (earlier chosen) | +$10.50 | 7 | +$5.72, +$2.30, +$2.47 | −1.32% |
| V4 — Bollinger 25-bar, 50% + scale-in, mean exit +60 bps (**chosen**) | **+$12.61** | 10 | +$5.72, +$2.92, +$2.90, +$1.07 | −1.32% |

A wider grid sweep (in-process, same fill model) over band lengths
15–30, sigmas 1.5–2.25, take-profits 100–200 bps and holds 180–360
showed a plateau, not a sharp peak: the 20- and 25-bar, 2-sigma
variants all land between +$10.50 and +$12.61 with no losing round
trips. V1 and V2 score higher on the full window but both lean on a
single large winning trip (+$13.48 and +$14.71) and V1 is negative in
the second half (−$0.55 in the in-process split); V4 was chosen for
the better trade count (4 winning trips), both halves positive, and
more margin above the $0 dev gate.

## Risks

- **Overfitting / regime change.** Only 3–4 round trips exist in the
  dev window for any of these variants. The race window is unseen and
  may trend instead of ranging; in a strong trend the dip-buying entries
  can keep averaging into a falling price (the −100 bps stop and the
  single scale-in cap the damage per trip, but repeated trips could
  still lose). Max drawdown on dev was only −1.32%, far under the 25%
  guardrail, so a bad race window is unlikely to breach the guardrail.
- **Grader differences.** The simulator replicates the harness fill
  model from its source, but the official grade may use a warm-up
  period or a different hello seed. The bot uses no seed, no clock and
  no warm-up-dependent logic (it only trades after 25 bars of history),
  and its first trade is at bar ~372, so a warm-up of up to a few
  hundred bars would not change its trades. Verified deterministic
  across seeds 1 and 7.
- **Thin edge.** Net +$12.61 on dev is comfortably above the $0 gate
  but far from the +$20 stretch target; on the race window the same
  strategy could plausibly land anywhere from about −$10 to +$20
  depending on whether the range persists.
- **No submit/push done here.** GitHub push and make.fun submission
  were explicitly out of scope for this build; the parent handles them.

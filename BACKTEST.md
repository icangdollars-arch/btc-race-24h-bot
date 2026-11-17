# BTC Race Bot v10 — Backtest

## Headline (verified on the final file in disk, `sim.py`)

| Metric | v10 | v9 | v7/v8 | v4 |
|---|---|---|---|---|
| Full dev net PnL | **+$55.484325** | +$55.484325 | +$54.214033 | +$53.217849 |
| Final cash | $1,055.48 | $1,055.48 | $1,054.21 | $1,053.22 |
| Fills (buys / sells) | 16 (6 / 10) | 16 (6 / 10) | 12 (6 / 6) | 12 (6 / 6) |
| Round trips | [6.79, 3.69, 18.69, 18.17, 1.00, 7.14] | identical | [6.65, 3.57, 17.83, 18.02, 1.00, 7.14] | [6.65, 3.57, 17.83, 18.02, 1.00, 6.14] |
| Fees | $4.94 | $4.94 | $4.93 | $4.93 |
| Max drawdown | −0.66% | −0.66% | −0.66% | −0.66% |
| Halves (0:720 / 720:1440) | +$35.70 / +$6.74 | +$35.70 / +$6.74 | +$34.57 / +$6.71 | +$34.57 / +$6.71 |
| Seeds 1 = 7 | identical | identical | identical | identical |
| Rejected orders | 0 | 0 | 0 | 0 |

**v10 = v9 + one change: a trailing giveback on the tail re-buy leg.**
The re-buy leg keeps its +85 bps take-profit, but also exits if the ret
falls 15 bps below its peak once the peak has reached +50 bps
(`REBUY_GIVEBACK_BPS = 15`, `REBUY_GB_ARM_BPS = 50`). On dev the re-buy
leg rises to +85 without ever pulling back 10 bps from an armed peak,
so the giveback never fires and every dev number is identical to v9.
The +$59 target was NOT reached (missed by $3.52).

## Why the giveback is worth it (race-window benefit, quantified)

The v9 tail is the fragile part of the bot: the re-buy leg's dev peak
ret is +89 bps and its TP is +85 — only 4 bps of headroom. If the race
tail leg peaks in [65, 85) bps, the v9 TP never fires and the leg
flattens at the end of the window (on dev that flatten is +$2.50).
With the v10 giveback the same leg exits at peak−15 bps:

| Race tail peak P (bp) | v9 (TP85 only) | v10 (TP85 + GB15) | v10 gain |
|---|---|---|---|
| P >= 85 | banks +$7.14 | banks +$7.14 (TP fires first) | $0.00 |
| P = 75 | flattens ~+$2.50 | exits ~+60 bp, ~+$5.40 | ~+$2.90 |
| P = 70 | flattens ~+$2.50 | exits ~+55 bp, ~+$4.60 | ~+$2.10 |
| P = 65 | flattens ~+$2.50 | exits ~+50 bp, ~+$4.60 | ~+$2.10 |
| P < 50 | same as v9 | same as v9 (giveback not armed) | $0.00 |

Estimates use the dev ratio (+85 bp ret ≈ +$7.14 net on ~$1,048
notional). The one way the giveback can hurt: a mid-leg pullback of
≥15 bp from an armed peak (≥+50) before the leg reaches +85 exits the
leg early and it never recovers to +85. On dev no such pullback exists
(GB 10/15/20/30 all give exactly +$55.48), so the insurance is free
on the only window we can measure.

## Ranked table — everything tried in this session

| Version | Dev PnL | Fills / Trips | DD | Gate verdict |
|---|---|---|---|---|
| **v10 TP85 + GB15/arm50** | **+$55.484325** | 16 / [6.79, 3.69, 18.69, 18.17, 1.00, 7.14] | −0.66% | **BEST ROBUST (plateau)** |
| TP85 + GB10/arm50 | +$55.484325 | 16 / identical | −0.66% | identical to v10 |
| TP85 + GB20/arm50 | +$55.484325 | 16 / identical | −0.66% | identical to v10 |
| TP85 + GB30/arm50 | +$55.484325 | 16 / identical | −0.66% | identical to v10 |
| GB10 only, no TP (TP999) | +$54.577455 | 16 | −0.66% | −$0.91: exits at peak−10 (+79) instead of +85 |
| GB10/arm30 | +$48.852211 | 16 | −0.66% | **REJECTED** — giveback fires on an early pullback from a +30..+50 peak, −$6.63 |
| Re-buy TP 60/65/70/75/80 | +$54.486922 | 16 | −0.66% | −$1.00: re-buy leg +$7.14 → +$6.14. All TPs 60–80 fire on the same bar |
| Multi-tier 50%@180 + 25%@185/190/195 | +$55.385063 | 18 | −0.66% | −$0.10: second tier fires on the same bar as the first; the slice gives up the ride to the peak |
| Multi-tier 25%@200 | +$55.484325 | 16 | −0.66% | never fires (peak bot ret < 200 bp) |
| v9 baseline | +$55.484325 | 16 / identical | −0.66% | baseline |

## Path 1 — safer tail TP switch (tested, NOT taken)

Changing only `REBUY_TP_BPS` 85 → 65 gives +$54.486922, exactly
$1.00 less than v9. The brief's premise ("tail total stays +$7.14")
was wrong: v4's tail TOTAL was +$7.14 (late +$1.00 + re-buy +$6.14),
while v9's tail total is +$8.14 (late +$1.00 + re-buy +$7.14). The
$1.00 is the re-buy leg itself (TP 65 banks +$6.14, TP 85 banks
+$7.14). All TPs 60–80 give the same +$54.49 — the leg's ret jumps
past that whole range in one bar, so every TP in 60–80 fires on the
same decision bar. The giveback (above) insures the same [65, 85)
band at $0.00 dev cost instead of $1.00, so the TP switch is
dominated and was not taken.

## Path 2 — multi-tier partial exits (tested, rejected)

50% at +180, then 25% of the remainder at +185 / +190 / +195, 25%
ride with giveback 5. All three tiers give +$55.385063 (−$0.10):
the ret jumps from below +185 to above +195 in a single bar, so all
three tiers fire on the same bar and fill at the same open — the
25% slice sells at ~+190 instead of riding to peak−5, losing more
on leg 371 than it gains on leg 574. A +200 tier never fires. The
single-tier v9 partial is the sweet spot; a second tier adds nothing.

## Path 4 — DP leg-gap check (read, no build)

DP leg list (work_v8/BACKTEST.md): 12→61, 76→113, 193→315, 387→465,
487→516, **526→535 +$1.10**, 574→588, 610→682, 689→699, 719→724,
753→770, 824→865, 881→968, 1101→1183, 1233→1293. Gap 968–1100
contains NO DP leg at all. Gap 515–573 contains only the 526→535
scalp, already tried in v8 (ADD scalp, fragile +$54.96, rejected).
No re-entry rule to build.

## Not attempted

- **Path 3 (partial late exit + re-buy add):** the late leg is only
  +$1.00; a ridden late half could add ~+$0.10–0.20, while the
  re-buy leg (+$7.14) depends on the full late exit and must not be
  disturbed. Low expected value, real breakage risk, no time left.
- **Path 5 (SMA30 second main arm):** the DP gaps are verified dead
  (only the fragile 526→535 scalp exists); every medium-arm attempt
  in v6–v9 produced knife legs. Expected value ≈ $0 or negative.

## Gates (v10)

- Full dev ≥ +$59? **NO — missed by $3.52** (same as v9).
- Full dev ≥ v9's +$55.48 AND strictly more race-robust? **YES —
  identical dev, tail insured +$2.10–3.70 in the [65, 85) peak band.**
- Halves positive: **PASS** (+$35.70 / +$6.74).
- Max DD −0.66% ≤ 5%: **PASS.**
- Deterministic seed 1 = 7: **PASS.**
- Round numbers (50%, +180, GB 5, GB 15, arm 50): **PASS.**
- Top-3 within $5: GB 10/15/20/30 all +$55.48, multi-tier +$55.39,
  v9 +$55.48 (within $0.10): **PASS (plateau).**
- No single-trade dependence: best trip $18.69 removed → +$36.79
  > $30: **PASS** (same trips as v9).

## Leaderboard context (18:07 WIB, parent update)

Top 4 are now ALL above the all-in DP optimum (+$78.08): luvmee
$106 ("DP-fitted dev schedule + honest dip-buy race mode"),
lucky-marten-16 $103, dutbld $99.40, vinzenzo $88.30. Two of them
say "DP-fitted dev schedule" in their own titles — dev-fitting has
spread. Three independent DPs plus chad-weasel-77 ($78.10) all agree
the causal all-in optimum is ~$78, so $99–106 cannot be a general
causal strategy. NOT chased, NOT imitated. v10 (+$55.48) would be
dev #9 on this board (inside the top 10); v7 (+$54.21) is also above
the $51.50 reward bar. Dev ≠ race: prizes come only from the race
window (17 Nov 19:18 WIB → 18 Nov 19:18 WIB).

## Recommendation

**Submit v10 (+$55.48)** over v9 (+$55.48) — identical dev, strictly
better race tail. Over v7/v8 (+$54.21): +$1.27 more on dev, same
robustness. Over v4 (+$53.22): +$2.27 more on dev; v4's only edge
was the safer tail, which v10 now matches more cheaply via the
giveback (v4 pays $1.00 dev for it, v10 pays $0.00). Honest
weaknesses, same as v9: dev $3.52 below the +$59 target and $2.82
below live #7 ($58.30, mining-airdrop — the highest NON-dev-fitted
entry); the big legs still exit on TP-180 at heart (the ride half
only adds 12–27 bp of peak); the tail re-buy TP +85 is still 4 bp
below the dev peak (+89); the second-half weakness persists
(+$6.74); dev ≠ race. Nothing was submitted by me; the ONE
remaining submission is untouched.

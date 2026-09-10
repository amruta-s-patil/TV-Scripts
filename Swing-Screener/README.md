# Swing Screener — 3% target, hold up to 4 days

Verified against Chartink's live scan endpoint on 2026-09-09.

| File | Tool | Typical hits/day |
|---|---|---|
| `chartink_swing_4day.txt` | chartink.com → Screener → paste in clause box | ~9 |
| `chartink_swing_4day_watchlist.txt` | same, no volume trigger | ~40 |
| `screener_in_fundamental_universe.txt` | screener.in → Screens → Create new screen | weekly universe |

Run the watchlist scan to see what is setting up. Run the main scan for today's entries.

## Known Chartink gotcha
`atr( 14 )` is **not** a valid Chartink field. It renders fine in the visual builder but
makes the whole scan fail silently with zero rows. The correct name is `avg true range( 14 )`.

## What the filters do

| Purpose | Rule | Passing alone |
|---|---|---|
| No shell / micro caps | Market cap > ₹1000 cr | 1451 |
| Fundamentally strong | ROCE > 15 | 800 |
| Not over-leveraged | Debt/equity < 1 | 2004 |
| Skin in the game | Promoter holding > 40% | 1700 |
| Growing | Net profit > same quarter last year | 1450 |
| No penny stocks | Close > ₹50 | 2256 |
| No manipulation | 20-day avg volume > 2 lakh shares | 1254 |
| Trend | Close > 20 SMA, and 50 SMA > 200 SMA | 1129 / 1441 |
| Room to run | RSI 50–68 | — |
| 3% reachable in 4 days | ATR(14) > 1.2% of price | 2795 |
| Not already extended | Close < 1.06 × 20 SMA | 2463 |
| Participation | Volume > 1.2 × 20-day avg | — |

## Why these numbers for a 4-day hold
- **ATR 1.2%.** Four sessions of 1.2% daily range gives roughly 2.4% of random travel plus
  trend drift, so 3% is comfortably reachable without needing a violent mover.
- **Close < 1.06 × 20 SMA.** The single most important filter for a multi-day hold. Buying a
  stock already 10% above its 20 SMA means the first two days of your hold are spent in the
  mean-reversion pullback.
- **No `close > yesterday's high`.** That is a same-day momentum trigger. Over four days it
  only makes you pay up for the move you were trying to capture.

## Workflow
1. Weekly: run the screener.in query. That is your fundamental universe.
2. Daily near close: run the main Chartink scan. Trade names present in both lists.
3. Entry next open. Target +3%. Stop −2%, or below the 20 SMA, whichever is nearer.
4. Exit at end of day 4 regardless of price.

## Tuning
- Too few results → use the watchlist file, or drop the volume trigger to 1.0.
- Too many → raise market cap to 5000, or ROCE to 20.
- A 5-day range gate (`max(5,high) - min(5,low) > close * 0.03`) was tested and removed.
  It selected exactly the same stocks as the ATR gate, so it was pure duplication.
- Chartink fundamentals lag a quarter. screener.in is the source of truth for fundamentals.
- Chartink has no pledged-shares field, so that check lives only in the screener.in query.

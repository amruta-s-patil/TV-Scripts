# SD-X v11

Nifty Intraday Signals + Option Chain

*TradingView Pine Script v6 \| User guide*

## 1. What this is

SD-X is a pair of TradingView indicators for intraday Nifty trading on a 3-minute chart, written for an option buyer who takes ATM CE or PE positions and squares off the same day.

It started as a pure mean-reversion system: price rejects a supply or demand zone, or bounces off a level where BankNifty previously turned, and momentum agrees. This version adds a ported **GTI engine** — order-flow reading through bar colour, candle shape, flag runs and climax shelves — which contributes two continuation entry sources of its own and a set of vetoes that stop the reversion trades you should not be taking. It is still deliberately selective: on a strong one-way trend day it will often produce no signals at all.

This version also ports three ideas from a GTI trading session: the **opening candle** and the day bias it sets, **structural compression** of the battlefield between the zones, and the **zone attack counter**. All three are described in sections 3.8 to 3.10. Two of them can act as hard gates that silence the script on most days, and both are off by default — read section 10 before turning them on.

The package is split into two scripts because TradingView caps a single indicator at 40 unique data requests, and a live option chain uses a new request every time the ATM strike moves.

| **Script** | **What it does** | **History** |
|:---|:---|:---|
| SD-X v11 Signals | Zones, cross-index levels, GTI order-flow markers, filters, entry circles, SL and target lines, statistics and diagnostics. Uses 4 data requests. | Full chart history |
| SD-X v11 OI | Option chain table: strike-wise CE/PE open interest, intraday OI change, PCR, max-OI strikes, writing bias, futures buildup, live ATM premiums. | Last 20 bars only (current snapshot) |

Both are added to the same chart. The signals script is the one that produces trades; the OI script is context you read before and during a trade.

## 2. The chart at a glance

`sdx_legend.png` is the printable version of this table — every marker the script can draw, in the colours it draws them. Regenerate it with `python sdx_legend.py` after changing the script.

![SD-X v11 chart legend](sdx_legend.png)

The one rule that matters: **only the big circle with a "BUY … CE/PE" label is a trade.** Everything else on the chart is context that tells you what kind of tape you are in.

## 3. Technical indicators used

### 3.1 Supply and demand zones

Two shaded boxes: salmon for supply above price, teal for demand below. They mark where price previously ran out of buyers or sellers. Five construction modes are available.

| **Mode** | **How the zone is built** | **When to use** |
|:---|:---|:---|
| Auto (near price) | Supply = highest high of the 40 bars *before* the current one, down to that level minus one ATR. Demand mirrors it from the lowest low. | Default. The zone slides with price, so it is always reachable — even in a strong trend. The live bar is excluded so that a breakout bar can close *above* supply; with it included, no bar ever could, and every long at a new high was refused for lack of room. |
| Daily gap-adaptive | Built at 09:15 from yesterday's high, low and close against today's open. A gap down makes yesterday's close the cap; a gap up makes it the floor; a flat open uses plain prior-day structure. Also draws pale teal **target tiers**. | Gap days, and whenever you want structural targets instead of a fixed multiple. |
| Previous candle | Yesterday's daily high to its body top (supply); body bottom to its low (demand). | Swing context. Often far from price intraday. |
| Last pivot | The most recent confirmed swing high/low on the zone timeframe. | Range days. Warning: in a sustained trend no new pivot confirms, so the zone can strand hundreds of points away. |
| Range extremes | Highest high / lowest low of the last N bars on the zone timeframe. | A middle ground between Auto and pivots. |

Every zone is at least "Min zone height" points thick (default 15) so a narrow trend candle cannot produce a sliver of a zone.

**Target tiers** (gap-adaptive mode only) are the pale teal bands. They mark where the move is *trying to reach*, not where it turns. Set Target mode to "Structure (gap tiers)" and the script aims at the next tier instead of a fixed R:R — and refuses the trade when there is less than "Min R:R" of room to it.

### 3.2 Cross-index pivot levels

The script watches BankNifty for swing highs and lows using an 8-bar pivot on the chart timeframe. When BankNifty turns, it draws a horizontal line at the Nifty price that existed at that same moment.

The premise is that Nifty is heavily driven by banks, so a turn in BankNifty often leads a turn in Nifty by a few candles. Sensex was dropped in this version: it correlates ~0.99 with Nifty on near-identical constituents, so its pivots landed on Nifty's own and added clutter rather than information.

| **Element** | **Meaning** |
|:---|:---|
| Solid red line | Drawn at a pivot HIGH of BankNifty — acts as resistance |
| Dashed red line | Drawn at a pivot LOW of BankNifty — acts as support |
| Tag `BN` | Which index produced it |
| Line disappears | Price closed through it, so it is no longer valid. Only untested levels remain on the chart. |

### 3.3 VWAP — the primary bias filter

Session VWAP on HLC3, the institutional average price for the day. This is the single most restrictive filter in the system, and the usual reason a setup does not become a signal.

| **VWAP mode** | **Effect** |
|:---|:---|
| Trend | Longs only above VWAP, shorts only below. Strictest. On a day where price stays below VWAP from open to close, no long can ever fire. |
| Stretch (default) | As above, plus it permits a counter-trend entry when price is more than 1.5 ATR away from VWAP and RSI is turning back. This is a genuine mean-reversion condition, not simply switching the filter off. |
| Off | No VWAP condition. Not recommended — it allows buying every falling knife. |

### 3.4 RSI and EMA

- RSI (14): longs need RSI above 50, shorts below 50. In Stretch mode a long is also allowed when RSI is under 40 but rising, and a short when RSI is over 60 but falling — the classic oversold/overbought turn.

- EMA (21): optional and off by default. Turn it on when you want to trade only in the direction of the short-term trend; it makes the system considerably quieter.

### 3.5 ATR (14)

Not a filter but the measuring stick used throughout: zone thickness, the stop-loss buffer beyond structure, the "stretch" distance from VWAP, range-expansion and climax tests, and the zone-distance warning in the diagnostic table are all expressed in ATR so the script adapts to quiet and volatile days without changing settings.

### 3.6 The GTI engine — order flow read off the bar

This is what the coloured candles and the small markers are. None of it fires a trade on its own except where noted; it tells you *who* is trading and *what kind of day* you are in.

| **Component** | **What it measures** | **Where it shows** |
|:---|:---|:---|
| Whale bars | Volume above 1.35× its 20-bar average, with a directional close or a long wick | Blue bar = buying, black bar = selling |
| Range expansion | Bar range ≥ 1.4 × ATR on above-average volume | Yellow bar |
| Absorption / belan | Wick ≥ 1.3× body, or body under 15% of range | Grey bar |
| Compression (squeeze) | Bollinger Bands inside Keltner Channels | Purple background shading |
| Injection candles | Long wick against the body — rejection | Lime / magenta triangles (wide bar) or dots (narrow bar) |
| Belan candles | Near-doji inside a range | Orange diamond (wide) or orange ✕ (narrow) |
| Shark trap | Three same-direction bodies breaking 30-bar isolation, with no fourth | Yellow `TRAP` tag |
| Whale 4-flag | A fourth consecutive body extends the run | Blue `4F` (long) / black `4F` (short) — **an entry source** |
| Absorption at base/ceiling | Absorption wick at the day's structural edge, on the right side of VWAP | Contributes an `absorb` entry — **an entry source** |
| Climax | Outsized volume (or range) into the base or ceiling | Maroon square (bear, above bar) / orange square (bull, below bar), plus a shelf line |
| Climax shelves | Horizontal memory of a climax bar, tagged with the day of month, with a dashed half-range line | Maroon (low) / orange (high) |
| CAMDC phase | Where the day sits in Compression → Accumulation → Manipulation → Distribution → Correction | "Phase" row of the Today table |

**A note on volume.** A spot index reports no traded volume, so every volume gate would silently pass or silently fail depending on your feed. The "Volume confirmation" setting defaults to **Auto**: it uses volume where the feed provides it and degrades to price-only tests where it does not. When it degrades, the Phase row is marked `(no vol)` and the whale bar colours stop appearing — the signals get looser, not wrong.

### 3.7 Wave (5) exhaustion — the veto

The most important addition in this version, because it stops trades rather than starting them.

A `W5` tag is printed when price makes a new extreme that RSI does **not** confirm, while stretched more than 0.8 ATR from VWAP, and the bar rejects itself with a wick larger than its body.

- Maroon `W5` above the bar = exhaustion at the highs. **Longs are vetoed for the next 8 bars.**
- Green `W5` below the bar = exhaustion at the lows. **Shorts are vetoed for the next 8 bars.**

These vetoes are counted in the "Blocked: W5 / squeeze" row of DIAG, so you can see exactly what they cost you.

### 3.8 Opening range and day bias

Three thick blue lines' worth of structure, added in this version and adapted from a GTI session: the opening candle owns the day.

**The opening candle.** The script accumulates the first *N* minutes of the session into one synthetic candle (default 9 minutes; use 5 or 15 if that suits your chart). Its high and low are drawn as a thick blue pair.

**The fake-candle rule.** If that candle opens exactly on its own high, or exactly on its own low, no two-way auction happened inside it — one side simply pushed from the bell. GTI treats such a candle as information-free and uses the **second** candle of the same length instead. The Day bias row is tagged `c2` when this substitution happened. "Fake-candle tolerance" widens the equality test from exact to a few points; leave it at 0 unless your feed's opening print is noisy.

**The bias.** The first close through either edge of the reference candle sets the day's direction and **latches it for the session**: a break up means buy-on-dip only, a break down means sell-on-rise only. A day that breaks up and then breaks down does not flip — GTI does not trade the second break.

**The ladder.** The reference candle's own height, projected in 1:1, 1:2 and 1:3 multiples from each edge, drawn as fading blue lines. These are the day's realistic profit stations, measured off the auction rather than off your stop. Set Target mode to "Opening-range ladder" and the script aims at the next unreached rung. Once 1:3 is tagged, institutions are booking — the original direction is spent, which is why "Veto further entries once 1:N is reached" exists.

| **Setting** | **Default** | **Effect** |
|:---|:---|:---|
| Track the opening candle | On | Builds the range and the bias; drawing and the Day bias row depend on it |
| Opening candle length | 9 minutes | GTI's own preference. 5 and 15 both work; 9 has no special magic |
| Fake-candle tolerance | 0 points | How close to its own high/low the open must be to count as fake |
| Trade only in the opening-break direction | **Off** | The hard gate. Turn it on to enforce one-side-per-day |
| Ladder rungs | 3 | How many 1:N projections to draw and target |
| Veto further entries once 1:N is reached | Off | Stops adding to a move that has already paid out |

**The shadow rows.** GTI's "buy on dip" after an upward break often means a dip *under VWAP*, which this script's primary filter refuses on principle. Rather than let the bias override the filter on the strength of one candle's break, the DIAG table paper-trades every setup that the filter alone blocked while the bias agreed — same stop, same target, same cooldown — and reports the count and the running points in the two **Shadow** rows. Nothing about it changes what fires. Log it for a fortnight. If the shadow points are consistently positive, the exception worth adding is a narrow one: a with-bias entry under VWAP only when the dip lands back inside the opening range, which is the retest GTI actually describes. If they are not, the filter was right and the question is closed.

### 3.9 Structural compression — the battlefield

Distinct from the purple squeeze shading, which is a Bollinger-inside-Keltner volatility read on a single bar. **Structural compression is the clear air between the demand zone's ceiling and the supply zone's floor** — the ground the two sides are still fighting over. When it collapses, buyers and sellers are transacting in the same prices and nobody can tell them apart, so the move that resolves it has to be large enough to separate them again.

It is measured once, at the day's first bar, from the zone edges the script is already drawing, and reported in the **Battlefield** row of the Today table as a point figure plus `COMPRESSED` or `open`. Compressed means the gap is under 0.75 ATR by default.

This is the precondition GTI puts under everything else: a compressed morning is what makes the opening break worth trusting. "Only take entries on compressed days" enforces it. It is off by default because it will silence the script entirely on many perfectly tradeable days.

### 3.10 Zone attack counter

The GTI framing: a zone is a wall until the third or fourth time somebody hits it. The first two attacks get ignored, the third gets a response, the fourth starts the fight.

The script counts **black (institutional selling) candles that land inside the demand zone**, and **blue (institutional buying) candles that land inside the supply zone**, numbering each one on the chart. The count is wiped in two cases: price clears the opposite zone — the day's read has been neutralised and starts again — or price closes through the zone itself, because a wall that broke held nothing and its attacks stop being evidence. (In Auto zone mode the edges trail price and cannot be closed through, so only the first reset ever applies there.)

At the threshold (default 3) the zone has demonstrably held, and the trade is the break of the last attack candle **away from the zone**:

- 3+ black candles in demand, then a close above the last one's high → long, stop under that candle's low.
- 3+ blue candles in supply, then a close below the last one's low → short, stop above that candle's high.

The fired-latch is keyed to the count, so if the third attack's trade stops out, a fourth attack re-arms the setup — which is exactly the sequence GTI describes.

This entry source is labelled `attack` on the entry label. It depends on the whale bar colours, so **on a feed with no volume it will produce far fewer signals** (see the note on volume in 3.6).

### 3.11 India VIX regime

A daily India VIX read drives the "Regime" row of the Today table, and is advice only — it changes no logic.

| **VIX** | **Regime** | **Strike advice** |
|:---|:---|:---|
| Below 13 | Low — rangebound | ATM / slight OTM |
| 13 to 18 | Moderate — trending | ATM / slight ITM |
| Above 18 | High — vega crush | ITM (vega shield) |

The point is that in a high-VIX session an OTM option can lose money on a correct directional call, because implied volatility collapses faster than delta pays. Going ITM trades premium cost for a smaller vega exposure.

### 3.12 Open interest (companion script)

OI is the number of contracts outstanding at each strike. Rising OI alone does not say who is trading it — the same rise means fresh writing (a wall) if the premium fell, or fresh buying (a punt) if the premium rose. Each leg is read against its own premium move into one of four actions:

| **Action** | **OI change** | **Premium change** | **Meaning** |
|:---|:---|:---|:---|
| Writing | Up | Down | Fresh sellers — builds a wall (call writing = resistance, put writing = support) |
| Buildup | Up | Up | Fresh buyers taking a directional punt |
| Covering | Down | Up | Writers buying back — the wall is being removed |
| Unwinding | Down | Down | Longs closing out |

Which way an action leans depends on the leg it happened on — calls and puts read mirror-image:

| **Action** | **On a call (CE)** | **On a put (PE)** |
|:---|:---|:---|
| Writing | Bearish — resistance wall | Bullish — support floor |
| Buildup | Bullish — call buyers | **Bearish — put buyers** |
| Covering | Bullish — resistance lifting | Bearish — floor lifting |
| Unwinding | Bearish — call longs quitting | Bullish — put longs quitting |

The one that trips people up is **PE buildup**: it is *not* put writing. Put OI rising while the put premium also rises means fresh put *buyers*, which is bearish. Put writing (OI up, premium down) is the bullish one.

| **Reading** | **Interpretation** |
|:---|:---|
| Signal column | Whichever leg (CE or PE) moved the most OI at that strike, tagged with its action, e.g. "CE writing" or "PE covering" |
| Res / Sup | Strike with the highest total CE / PE open interest, across the whole chain |
| PCR | Put-call ratio of total OI. Above 1.2 leans bullish, below 0.8 bearish. A blunt measure — use it as background, not a trigger. |
| Chain bias | Every leg's action is signed bullish/bearish and weighted by the OI it moved, then summed across the whole chain — not just total OI change — and cross-checked against PCR: "confirmed" when they agree, "PCR disagrees" when they don't |
| Buildup (futures) | Futures OI change against the day's price move: long buildup, short buildup, short covering, or long unwinding |

**Which baseline.** NSE's change fields — and therefore every action, verdict and the chain bias — are measured from *yesterday's close*. That is a positioning read for the day, and on a day that ends where it started it can look nothing like the session you watched: on 11-Sep-2026 the index rallied 110 points off the open, the chain read "Bearish" throughout, and it was right — the rally was sold into a written-call ceiling and fully retraced by 11:00. To see what a *move* did to positioning, the desktop window has an **intraday** toggle and a **mark** button (see the desktop section in §6): every delta, tag and verdict is then measured from the mark instead of the previous close, and the status line says which baseline is in force. Read the two side by side — the day read says where the walls are; the intraday read says whether the current move is building them or taking them down.

The optional Shark hunting matrix shows this per-leg action for every strike in the window (`--shark` on the command line, or the "shark" checkbox in the desktop app), plus a net verdict and a PIN/VAC flag: PIN means both legs are genuinely being written (the strike is pinned), VAC means both are shrinking (the walls are coming off).

If your TradingView plan has no NSE F&O OI entitlement, `oi_chain.py` prints the same table from NSE's public endpoint. `oi_desktop.py` is the same data as a small always-on-top window instead of a terminal dump: pick the symbol (NIFTY/BANKNIFTY/FINNIFTY/MIDCPNIFTY) and expiry, set how many strikes each side of ATM and the auto-refresh interval, and it polls NSE on its own, pausing automatically once the feed's own timestamp shows the market closed.

### 3.13 Shark flow (companion pane script)

`sdx_v11_sharks.pine` answers one question the chart alone can answer without any option data: **where did the big lots print today, and which way did they lean?** It makes no data requests at all, so it runs on a TradingView plan with no NSE F&O entitlement. Load it in its own pane under the signals script.

It uses the signals script's own whale-bar test (3.6) — volume above 1.35× its 20-bar average, direction from the bar's body and wicks — so a blue bar on the chart is a buy column here and a black bar a sell column. A bar that qualifies both ways (wide wicks both sides) is a fight nobody won and counts as zero.

| **Element** | **What it shows** |
|:---|:---|
| Columns | Each whale bar's volume, blue for institutional buying, black for selling |
| Line | Today's cumulative signed whale volume — buying minus selling since the open. Green above the neutral band, red below, grey inside it |
| Sharks | The verdict: **Bullish**, **Bearish** or **Neutral**. The band is 10% of the day's gross whale volume, so it self-scales between a quiet morning and expiry day |
| Flow today | The net figure and how many whale bars went each way |
| Big buy / Big sell | The single loudest whale bar each side, with the price it closed at and the time. That level is where the sharks showed their hand — treat it as support (buy) or resistance (sell) until it is closed through |

Alerts: "SD-X Sharks turn bullish / bearish" fire when the line crosses out of the neutral band.

What it is not: a read of *positions*. Open interest is positions; this is traded volume on a spot index, which TradingView synthesises from the constituents. It says who was aggressive on the tape today, not what they are holding. For the positions read, use the desktop OI window's `intraday` view (§3.12), which has the option chain and premiums the chart does not.

## 4. How a signal is produced

Every bar passes through six stages. A setup must survive all of them to become a circle on the chart. The diagnostic table counts how many setups die at each stage, which is what makes the system debuggable.

| **Stage** | **Condition** | **Failure shown as** |
|:---|:---|:---|
| 1\. Trigger | Any of the four entry sources fires (see below). | No setup — nothing plotted |
| 2\. Filter | VWAP mode satisfied, RSI on the correct side, EMA if enabled. | Blocked: filter |
| 3\. Risk | Stop distance is at least 20 points and no more than 70. Wider setups are skipped rather than sized badly. | Blocked: risk |
| 4\. Room | At least "Min R:R" of clear space to the next wall — the structural tier in "Structure (gap tiers)" mode, the next ladder rung in "Opening-range ladder" mode, the opposing zone edge in "Fixed R:R". | Blocked: no room |
| 5\. Regime | Not inside a Wave (5) lockout; not compressed if you chose to block that; **on the right side of the day bias if that veto is on; on a structurally compressed day if that is required; and not past the 1:N ladder rung if that veto is on.** | Blocked: regime |
| 6\. Gate | Inside the entry window, under the daily trade limit, past the cooldown. An already-open trade no longer blocks the next signal — several can run at once, capped by "Max trades per day". | Blocked: session/limit |

Stages 2 to 6 mark the bar with a small grey ✕ so you can see, on the chart, exactly where a setup existed and was rejected.

### The six entry sources

Each carries its own stop anchor, and the source is printed on the entry label so you always know which one fired.

| **Source** | **Trigger** | **Stop anchored at** | **Type** |
|:---|:---|:---|:---|
| `zone` | Price wicks into a zone and closes back out with a candle in the right direction | Far edge of the zone | Reversion |
| `level` | Price bounces off an unbroken BankNifty cross-index level | The level | Reversion |
| `4-flag` | A fourth consecutive same-direction body extends an isolated run | Extreme of the last 4 bars | Continuation |
| `absorb` | Absorption wick at the day's base or ceiling, on the right side of VWAP | The bar's own extreme | Reversion |
| `attack` | The zone survived N institutional attacks (default 3) and price closes back through the last attack candle | That candle's opposite extreme | Reversion |
| `expand` | A range-expansion bar (≥ 1.4 ATR, with volume) within 3 bars of a squeeze, closing in the top or bottom quarter of its range, in the direction of the day bias | The bar's own extreme | **Momentum** — the only source that buys strength. Added after 11-Sep-2026, when a 45-point bar out of compression touched no zone, level or attack candle and the 3-bar run it completed was a "trap" by the flag rule. It is exempt from the room test — the zone it closes into is the one it is breaking — and ignores the target mode: it always takes its own fixed **"Expansion bar R:R"** (default 1.5, under "Entry sources"), lower than the 2R the reversion sources ask for, because a bar that has just run 1.4 ATR has less left to give. The risk stage still refuses a bar that ran further than the maximum stop. Turn it off under "Entry sources" if you want the script purely mean-reverting again |

When more than one fires on the same bar the tightest structural stop wins. Any source can be switched off individually under "Entry sources".

### Entry, stop and target

- Green circle below the bar = buy ATM CE. Red circle above the bar = buy ATM PE. A label names the strike and the source, for example "BUY 23650 CE  zone".

- Red line = stop loss, placed beyond the structure that was defended, plus half an ATR, then floored at 20 points and capped at 70.

- Black line = target: twice the risk by default, the next structural tier in "Structure (gap tiers)" mode, or the next 1:N rung in "Opening-range ladder" mode. Every mode falls back to the fixed multiple when its own target is unavailable — before the opening range settles, for instance.

- The SL and target labels also show the expected premium move, calculated from the ATM delta setting. A 30-point index stop at 0.5 delta shows as "prem −15".

- Lines extend bar by bar and freeze when hit, tagged TARGET, STOP or SQ-OFF, so scrolling back shows the real outcome of every past signal.

- A bar that spans both stop and target is treated as a stop. Intrabar order is unknowable on a 3-minute candle, so the script never awards itself the gift.

## 5. Intraday rules built into the script

| **Rule** | **Default** | **Why** |
|:---|:---|:---|
| Entry window | 09:20 – 15:00 | Avoids the opening auction noise and gives a late trade room to work |
| Expiry-day entry cut-off | 13:00 | Premium decay and gamma make afternoon expiry entries unsuitable for a 3-minute reversion system |
| Square-off | 15:15 – 15:30 | Every position is closed; nothing is carried overnight. The script's clock is the spot chart, which still ends at 15:30; NSE F&O trades until 15:40 (since 3 Aug 2026) and the cash closing auction runs 15:15–15:35 (since 7 Sep 2026), so 15:15 is deliberately *before* both — do not push it later |
| Max trades per day | 3 | Prevents revenge-trading a bad session, and caps how many trades can be live at the same time |
| Cooldown | 6 bars | Stops clustered signals in the same move |
| Several positions at once | Allowed, capped by the daily limit | A live trade no longer mutes the next setup (see section 4); the trade cap and cooldown bound total exposure |
| Wave (5) lockout | 8 bars | Stops you buying the top of an exhausted leg |
| Levels cleared each morning | On | Yesterday's BankNifty pivots do not leak into today |
| Opening candle | First 9 minutes | The reference range; skipped and replaced by the second candle if it opens on its own high or low |
| Day bias | Latched, no flip | The first break of the opening range owns the session |
| Battlefield measurement | At the day's first bar | Compression describes the day, not the bar, so it is not recomputed intraday |
| Attack count reset | On clearing the opposite zone, or closing through the zone itself | GTI's "data neutralised" — and a broken zone did not hold its attacks, so they no longer count |

## 6. Reading the two tables

### Today (top right)

Trades taken versus the daily limit, wins, losses, net index points, an estimated rupee figure using your lot size, and the current ATM strike. On expiry day the ATM cell is flagged in red. Below that:

| **Row** | **What it tells you** |
|:---|:---|
| VIX | India VIX, coloured green / orange / red by regime |
| Regime | Regime name and the strike selection it implies |
| Phase | The current CAMDC phase. `(no vol)` means the feed has no volume and the engine is running price-only. |
| Battlefield | Points of clear air between the zones at the open, tagged `COMPRESSED` or `open`. Compressed days are the ones GTI trades. |
| Day bias | `LONG buy-on-dip`, `SHORT sell-on-rise`, or `unbroken` while the opening range still holds, with the range in brackets. `c2` means the first candle was fake and the second was used. |

The Phase row is the fastest read on the chart. **1 Compression** and **2 Accumulation** are the phases where reversion entries work; **4 Distribution** is where the 4-flag continuation entries live; **3 Manipulation** is where you get stopped out for no reason.

### DIAG (bottom right)

The troubleshooting panel. Read it top to bottom when a day produced no signals.

| **Row** | **What it tells you** | **Action if it looks wrong** |
|:---|:---|:---|
| Zone touched | How many bars entered a zone today | Zero all day means the zone is out of play — check the next row |
| Zone dist (ATR) | How far price is from each zone, in ATR. Turns red beyond 4. | Red means a stranded zone. Switch to "Auto (near price)" mode. |
| Setups found | Triggers that fired before filtering | Zero with touches above means the rejection test is too strict — set rejection to Loose |
| Blocked: filter | Setups killed by VWAP / RSI / EMA | High count on a trend day is usually correct behaviour, not a fault |
| Blocked: risk | Setups needing a stop wider than 70 points | Raise the maximum stop distance if this is persistently high |
| Blocked: no room | The wall ahead was too close to be worth the risk — a short taken just above demand, a long taken into supply | Lower Min R:R to loosen it (0.25 effectively disables it). |
| Blocked: regime | Setups vetoed by a Wave (5) lockout, by compression, by the day-bias gate, by the compressed-days-only gate, or by the 1:N ladder veto | If this is high on days you would have won, shorten the lockout, lengthen the wave lookback, or check whether a GTI gate you turned on is doing the blocking |
| Blocked: session/limit | Outside the window, or over the trade limit, or in cooldown | Widen the entry window if good setups appear late |
| SIGNALS | What actually fired | — |
| Zone / VWAP / RSI | Live values: the demand zone band, then VWAP and RSI | A sanity check that the filters are seeing what you are |
| Shadow: bias-only | Setups the VWAP / RSI / EMA filter refused while the day bias agreed with them, and which every later stage would have passed. Paper-traded, never plotted, never counted against the daily cap | Measurement only — see the note under 3.8 before acting on it |
| Shadow W / L / pts | Wins, losses and index points of those paper trades today, with the real stop and target | A run of positive days is the evidence needed before any "bias overrides VWAP" exception is worth building. One good day is not |

### Option chain (top left, companion script)

One row per strike around ATM with CE OI, CE change, PE OI and PE change. The ATM row is highlighted and marked with an arrow; the highest-OI CE and PE cells are shaded. Summary rows give totals, PCR, the support and resistance strikes, where today's writing is concentrated, the overall bias, and the futures buildup. The last row shows live ATM CE and PE premiums with the rupee cost of one lot.

### The desktop window (`oi_desktop.py`), column by column

The toolbar sets what is fetched: symbol (NIFTY / BANKNIFTY / FINNIFTY / MIDCPNIFTY), expiry (`auto (weekly)` picks the nearest), how many **strikes** either side of ATM, and the auto-refresh interval in **sec**. `auto` turns polling on or off, `on top` keeps the window above everything else, `shark` adds the last four columns, `intraday` switches every delta and read to the intraday baseline, `mark` restarts that baseline from the latest fetch, and `↻` forces one refresh.

The intraday baseline is the first fetch of the day (the window re-marks itself when NSE's date rolls over), or the last press of `mark`. Start the window at the open, or press `mark` at 09:20 once the opening auction is out of the numbers. With `intraday` on, CE Δ / PE Δ, the Signal, the shark columns and the chain bias are all measured from the mark; the OI totals, Res / Sup and PCR are unaffected because they are levels, not changes. A strike that enters the window later (the ATM moved) starts from zero — there is no intraday history for it, and none is invented. The status line reads `Δ since HH:MM` or `Δ vs prev close` so you always know which read you are looking at.

| **Column** | **What it shows** |
|:---|:---|
| Strike | The strike price. The ATM strike is coloured yellow and its whole row is shaded. |
| CE OI | Total call open interest at that strike. The highest-OI call strike in the chain is shaded red — that is resistance. |
| CE Δ | Change in call OI — since yesterday's close, or since the mark with `intraday` on. Green when falling, red when rising (rising call OI is usually a wall going up above you). |
| PE OI | Total put open interest. The highest-OI put strike is shaded green — that is support. |
| PE Δ | Change in put OI on the same baseline. Green when rising, red when falling. |
| CE LTP / PE LTP | Live premium for that strike's call and put. This is what separates writing from buying — see §3.12. |
| Signal | Whichever leg moved the most OI at that strike, tagged with its action: `CE writing`, `PE buildup`, and so on. Coloured by which way that action leans. |

The `shark` checkbox adds four more columns — the same strikes judged leg by leg instead of one headline per row:

| **Column** | **What it shows** |
|:---|:---|
| CE | What the call leg did on its own: writing / buildup / covering / unwinding, coloured bullish or bearish for a *call*. |
| PE | The same for the put leg, coloured for a *put* — so `buildup` shows red here and green in the CE column. |
| Net | The strike's verdict once both legs are weighted by the OI they moved. `Neutral` when the score is inside a band set at 10% of the loudest strike on screen, so it self-scales between a quiet morning and expiry day. |
| Note | Flags on that strike: `ATM`, `RES` / `SUP` (the chain's max-OI call / put strike), `PIN` (both legs genuinely being written — the strike is pinned), `VAC` (both legs shrinking — the walls are coming off and the range can give way). PIN and VAC print in yellow. |

Three summary lines sit under the ladder:

| **Line** | **What it shows** |
|:---|:---|
| First | Symbol and expiry, spot, ATM strike, chain PCR with its tag, then `▶` and the overall chain bias — green bullish, red bearish. |
| Second | `Res` and `Sup` (max-OI call and put strikes, with `↑` or `↓` if that wall sits outside the strikes on screen), whole-chain CE and PE OI with today's change, and the ATM strike's own signal. These are computed over the entire chain, not just the visible window. |
| Third | NSE's own feed timestamp and `LIVE`, or `CLOSED — auto-refresh paused` once that timestamp shows the session is over. |

## 7. Alerts

Fourteen alert conditions are exposed. The first three are the ones to actually set:

| **Alert** | **Fires when** |
|:---|:---|
| SD-X Buy CE / Buy PE | A signal circle prints |
| SD-X Square off | An open position reaches the square-off window |
| SD-X Wave 5 top / bottom | Exhaustion — stop chasing that side |
| SD-X Whale 4-flag long / short | A continuation run extends |
| SD-X Absorption at base / ceiling | An absorption wick holds the day's edge |
| SD-X Opening break | The opening candle breaks and the day bias is set |
| SD-X Zone attack long / short | A zone survived its Nth attack and the last attack candle is broken |
| SD-X Expansion long / short | An expansion bar out of a squeeze, with the day bias, closing near its extreme (fires whether or not the source is enabled for entries) |
| SD-X Ladder 1:N up / down | The opening-range ladder target is reached — the original move has paid out |

## 8. Daily workflow

1.  Before the open, glance at the OI table. Note the max-OI call strike (resistance) and put strike (support) — these often bracket the day's range. Check the VIX regime row and pick your strike accordingly.

2.  At the open, read the **Battlefield** row. `COMPRESSED` says the two sides are on top of each other and the day should resolve one way — those are the days the GTI method is built for. `open` says there is room between the zones and the day can drift; expect chop and take fewer trades.

3.  Watch the **Day bias** row through the first fifteen to twenty minutes. It stays `unbroken` until the opening candle breaks, then names the only direction worth trading. A `c2` tag means the first candle opened on its own high or low and was discarded.

4.  Read the Phase row through the morning. It tells you which kind of entry the day is likely to offer.

5.  Wait for a circle. Do not anticipate; the filters exist precisely to stop you taking the setups that look obvious but fail. A `W5` tag on your side means stand down for eight bars, no exceptions.

6.  On a green circle, buy the ATM CE named in the label; on a red circle, buy the ATM PE. Note the premium you actually paid, and note the source on the label — a `4-flag` entry is a continuation trade and behaves differently from a `zone` reversion.

7.  Set your stop on the premium: subtract the "prem −" figure from the SL label from your entry premium. Do the same with the "prem +" figure for the target.

8.  Cross-check the OI bias. A long while heavy call writing is being added just above your target is a lower-quality trade; consider taking a smaller size or booking earlier.

9.  Book into the ladder rungs. 1:1 is the first honest exit, 1:2 is the common one, 1:3 is where institutions book and the move usually stalls. After 1:3 prints, the higher-probability trade is the contra, not another entry in the same direction — the script will not take one for you, and the ladder veto only stops it adding to the move.

10. Exit at the stop, the target, or 15:15 — whichever comes first. Never carry.

11. At the close, read the Today and DIAG tables and log the result. After two weeks you will know whether the settings suit your market conditions.

## 9. Troubleshooting

| **Symptom** | **Cause and fix** |
|:---|:---|
| No signals for several days | Read DIAG. Almost always either a stranded zone (use Auto mode), the VWAP filter on trend days (use Stretch mode), or a run of Wave (5) lockouts. Some days genuinely have no valid setup. |
| Zones far above or below price | Pivot-based zones cannot update in a sustained trend because no new pivot confirms. Switch Zone source to "Auto (near price)". |
| No coloured bars at all, Phase says `(no vol)` | Your feed reports no volume for this symbol. Expected on a spot index. The engine has degraded to price-only tests; whale colours cannot be computed. Set Volume confirmation to "Off" to silence the label, or chart the futures instead. |
| "Blocked: W5 / squeeze" is eating everything | Either the day is genuinely exhausted, or the lockout is too long for your timeframe. Shorten Lockout bars, or raise Wave peak lookback so fewer bars qualify. |
| "Blocked: no room" on every setup | Price is pinned between the zones — usually a low-VIX range day. Lower Min R:R, or widen the zones (raise Auto lookback / Min zone height). |
| Signals cluster in chop | Raise the cross-index pivot length from 8 to 10 or 12, increase the cooldown, and turn on "Block entries while compressed". |
| Day bias never leaves `unbroken` | Price stayed inside the opening candle all session. On a 9-minute range that is rare; on a 15-minute one it is not. Either lower the opening candle length or accept it as a no-trade day. |
| Every setup shows "Blocked: regime" after you enabled a GTI gate | Expected. "Trade only in the opening-break direction" halves the tradeable setups by construction, and "Only take entries on compressed days" removes most days entirely. Turn one on at a time and watch the SIGNALS row for a fortnight before adding the other. |
| No `attack` entries ever fire | The counter needs blue and black whale bars, which need real volume. On a spot index there are none. Chart the futures, or accept that this source is inactive. |
| Attack numbers reset constantly | Price is crossing between the zones, or closing through one of them, which neutralises the count by design. It means the zones are too close together or too narrow, not that the counter is broken. |
| Ladder rungs are absurdly far away | A wide opening candle projects a wide ladder. On a gap-and-run open the 1:3 rung can be a whole day's range away — use Fixed R:R or the gap tiers on those days rather than aiming at it. |
| Stops feel too tight | Raise the minimum stop distance above 20 points. Nifty 3-minute noise can exceed 20 points in a volatile session. |
| Too many context markers on screen | Turn off "Mark injection / belan candles" and "Mark shark / whale flags" under the GTI group. The entry logic is unaffected. |
| Option chain shows n/a everywhere | The expiry is wrong (check the weekday setting, or use Manual for a holiday-shifted week), or your TradingView plan does not include NSE option OI data. Fall back to `oi_chain.py` or `oi_desktop.py`. |
| "Too many request calls" error | Reduce "Strikes each side of ATM" to 2 in the companion script. Do not merge the two scripts back into one. |

## 10. Limitations and risk

These points matter more than any setting in this document.

- This is a signal overlay, not a backtested strategy. Results shown on the chart assume a fill at the candle close with no slippage, brokerage or STT. Real option fills will be worse, often by several hundred rupees per lot per round trip.

- The rupee figure in the signals script is an estimate derived from index points multiplied by an assumed 0.5 delta. Actual premium movement depends on delta, implied volatility and time of day, and diverges most on expiry.

- The GTI order-flow read is an interpretation of bar shape and volume, not actual order-book data. On a spot index without volume it is bar shape alone. Treat blue and black bars as a hypothesis about who is trading, not a fact.

- The system is still mean-reverting in the majority of its entries. It will underperform in sustained trends and will produce no signals on some days. That is intended behaviour, not a fault to be tuned away by loosening every filter.

- Cross-index levels are based on an observed tendency, not a mechanical relationship. Correlation between Nifty and BankNifty varies from day to day.

- Option buying carries a high probability of small losses offset by fewer large gains. Position sizing and the daily trade cap matter more to the outcome than signal quality.

- **The GTI additions come from a recorded teaching session, not from a tested edge.** They were adopted because the reasoning is coherent and the mechanics are cheap to compute, not because they have been validated on this instrument. The presenter demonstrated them by scrolling back over selected days on his own chart, which is the weakest form of evidence there is. Treat all three as hypotheses under test.

- **The day-bias veto is the single most destructive setting in the script.** It removes one entire direction for the whole session on the strength of one candle's break, and that break can be a false one. Enable it alone, log a fortnight, and compare the SIGNALS row and the win rate against the same period without it before you keep it.

- **"Only take entries on compressed days" will produce no signals for days at a time.** That is what it is for. If you find yourself widening the compression threshold to get trades back, you have removed the filter and kept only its cost.

- The battlefield measurement is taken once, at the day's first bar, from whatever zone mode you have selected. In "Auto (near price)" mode those edges are a trailing 40-bar range, which spans yesterday and today at 09:15 — close to the two-day structure the method assumes, but not identical to it. In pivot modes it can be measuring something considerably older. Check the Battlefield figure against the chart before trusting it.

- The attack counter reads whale bar colours, which on a feed without volume do not exist. It is not a fallback-safe source the way the candle-shape tests are.

- **The GTI stop-loss discipline is much tighter than this script's default.** The method caps a Nifty stop at roughly 20 points and a BankNifty stop at roughly 35, on the grounds that a correct read does not need more. SD-X ships with "Max stop distance" at 70. If you are trading the GTI rules, set that to 20 for Nifty or 35 for BankNifty and expect the "Blocked: risk" count to rise sharply — that rise is the filter working, not a fault.

- The 1:3 contra idea — that institutions book at the third projection and the reverse trade becomes attractive — is described in the source session but never given an entry rule. Nothing in this script trades it. The ladder veto only stops the script adding to a move that has already reached its target.

- Validate the lot size against the current NSE contract specification before trading — it is entered manually and defaults to 65 (the Nifty lot since the January 2026 series).

- Expiry-day detection is a fixed weekday (Tuesday by default), not an exchange calendar. In a week where Tuesday is a holiday NSE expires on the previous working day; the script will not know, so set "Weekly expiry weekday" for that week by hand or accept a 13:00 cut-off on the wrong day. The same applies to the companion OI script's expiry selector.

*This document describes a charting tool. It is not investment advice, and nothing in it is a recommendation to buy or sell any instrument. Test on paper before committing capital.*

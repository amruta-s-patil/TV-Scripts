# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Trading tooling for Indian markets. No build system, no package manager, no test framework — two
independent projects that ship as text you paste into a website, plus stdlib Python helpers.

- [Nifty-Intra-OI/](Nifty-Intra-OI/) — **SD-X v11**, a Pine Script v6 intraday Nifty system for
  option buyers (3-minute chart, ATM CE/PE, same-day square-off), plus Python fallbacks for the
  option chain.
- [Swing-Screener/](Swing-Screener/) — Chartink and screener.in scan clauses (plain text, pasted
  into those sites). [Swing-Screener/README.md](Swing-Screener/README.md) documents every filter
  and *why* its threshold was picked; keep it in sync when editing a clause file.

## Commands

```bash
cd Nifty-Intra-OI
python oi_chain.py                  # NIFTY chain, nearest expiry, 5 strikes each side
python oi_chain.py BANKNIFTY 3      # symbol, strikes each side
python oi_chain.py NIFTY 5 1        # 3rd arg = expiry index (1 = next weekly)
python oi_chain.py NIFTY 6 --shark  # add the Shark hunting matrix
python oi_chain.py --selftest       # assert-based self-check, no network
python oi_desktop.py                # stay-on-top tkinter window (pythonw = no console)
python oi_desktop.py --selftest     # builds the UI on fake data, closes itself
python sdx_legend.py                # regenerate sdx_legend.png for the user guide
```

`--selftest` is the entire test suite. There is no pytest; tests are `assert` statements inside a
`selftest()` function at the bottom of the file, run offline against inline fixtures. Add new
asserts there — one line, with the reason as the assert message, matching the existing style.
Both selftests must stay network-free.

`oi_chain.py` and `oi_desktop.py` are stdlib-only, deliberately. `sdx_legend.py` is the one file
that needs matplotlib.

## Pine architecture

### Why two scripts, not one

TradingView caps an indicator at 40 unique `request.security()` symbols. A live option chain burns
a new symbol every time the ATM strike moves, so the chain lives in its own script:

- [sdx_v11_signals.pine](Nifty-Intra-OI/sdx_v11_signals.pine) — all signals; exactly 4 security
  calls (VIX daily, own-symbol daily OHLC, HTF zones, cross-index). Full chart history.
- [sdx_v11_oi.pine](Nifty-Intra-OI/sdx_v11_oi.pine) — option chain table only;
  `dynamic_requests = true, calc_bars_count = 20` so only a handful of distinct strikes are ever
  requested. Snapshot, not history.

**Adding a `request.security()` call to the signals script is a design decision, not a detail.**
The comment at the top of each file states its budget; keep both accurate.

- [GTI-pro.pine](Nifty-Intra-OI/GTI-pro.pine) is the upstream order-flow engine that the GTI
  sections of the signals script were ported from. It is reference, not a dependency.

### The six-stage signal pipeline

Everything in [sdx_v11_signals.pine](Nifty-Intra-OI/sdx_v11_signals.pine) exists to feed one
funnel: **trigger → filter → risk → room → regime → gate**. Six entry sources (`zone`, `level`,
`4-flag`, `absorb`, `attack`, `expand`) raise a setup; each subsequent stage can only veto. The `c*L`/`c*S`
counters tally deaths per stage and drive the DIAG table — that table is the debugging surface, so
a new veto must join the correct stage's counters or it becomes invisible.

New gates default to **off** (`input.bool(false, …)`) when they can silence the script on most
days — `biasVeto`, `reqCompress`, `ladderStop`, `blockSqz` all follow this.

Section banners (`// ═══ Name ═══`) are load-bearing navigation in a 1000-line file. Keep them.

### Pine conventions here

- All times are IST: `time(timeframe.period, sess, "Asia/Kolkata")`, and daily rollover via
  `ta.change(time("D")) != 0`.
- Anti-repaint is explicit and commented. The opening range only settles once the window *after*
  it has opened; a bar that spans both stop and target counts as a stop. Do not "improve" these
  into optimism.
- Comments explain *why the rule exists*, often naming the dated trade that exposed the bug
  (e.g. the `roomOK` hardcoded-true fix). Preserve that provenance when touching those lines.

## Docs — mandatory after ANY change in Nifty-Intra-OI/

[SD-X_v11_User_Guide.md](Nifty-Intra-OI/SD-X_v11_User_Guide.md) is the user-facing spec: it
documents every input, marker, stage and table. Any change under [Nifty-Intra-OI/](Nifty-Intra-OI/)
— Pine or Python, behaviour or default — must, **in the same commit**:

1. Update the guide's Markdown to match.
2. Regenerate the `.docx` from it:

```bash
cd Nifty-Intra-OI
pandoc SD-X_v11_User_Guide.md -o SD-X_v11_User_Guide.docx
```

3. Re-run `python sdx_legend.py` if any chart marker, colour or label changed, so
   `sdx_legend.png` (embedded in the guide) stays truthful.

The `.docx` is a generated artifact — never hand-edit it; edit the `.md` and re-run pandoc.

Steps 1 and 2 are enforced by [.githooks/pre-commit](.githooks/pre-commit), which re-runs pandoc on
the staged `.md` and compares `word/document.xml` against the staged `.docx`. A fresh clone must
enable it once:

```bash
git config core.hooksPath .githooks
```

"""SD-X OI desktop - the sdx_v11_oi.pine table as a stay-on-top window.
Live NSE data, no TradingView entitlement needed. Stdlib only (tkinter).

  python oi_desktop.py             # normal
  pythonw oi_desktop.py            # no console window
  python oi_desktop.py --selftest  # builds the UI on fake data, closes itself
"""
import queue, sys, threading, tkinter as tk
from tkinter import ttk

from oi_chain import (CE_BULL, PE_BULL, bias_tag, chain, fetch, fmt, front_expiry,
                      market_live, pcr_tag, rows, sgn, shark_matrix, strike_tag, totals)

AUTO = "auto (weekly)"

BG, FG, DIM = "#14161a", "#d8dde3", "#7d8792"
RED, GRN, YEL = "#ef5350", "#26a69a", "#ffd54f"
ATM_BG, CE_BG, PE_BG = "#2a2d34", "#3a1f22", "#1c332f"
COLS = ("Strike", "CE OI", "CE Δ", "PE OI", "PE Δ", "CE LTP", "PE LTP", "Signal")
# The shark matrix rides the same rows - same strikes, per-leg instead of net -
# so it is four more columns, not a second table.
SHARK_COLS = ("CE", "PE", "Net", "Note")
LEFT = {"Signal", "Note"}
SYMBOLS = ("NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY")
# Colour follows what an action implies, not the word: writing calls builds
# resistance (bearish), writing puts builds support (bullish), and a writer
# buying back removes the wall they built.
TAG_FG = {f"CE {a}": (GRN if b else RED) for a, b in CE_BULL.items()}
TAG_FG.update({f"PE {a}": (GRN if b else RED) for a, b in PE_BULL.items()})
VERDICT_FG = {"Bullish": GRN, "Bearish": RED}


def action_fg(action, table):
    b = table.get(action)
    return DIM if b is None else (GRN if b else RED)


class App:
    def __init__(self, root, autostart=True):
        self.root, self.q, self.cells, self.job = root, queue.Queue(), [], None
        self.live = True                          # until a feed timestamp says otherwise
        self.last = None                          # last payload, to redraw without refetching
        root.title("SD-X OI — NSE option chain")
        root.configure(bg=BG)
        self.expiries = []
        self.sym = tk.StringVar(value="NIFTY")
        self.exp = tk.StringVar(value=AUTO)       # follows the weekly until you pick one
        self.n = tk.IntVar(value=5)
        self.secs = tk.IntVar(value=30)
        self.auto = tk.BooleanVar(value=autostart)
        self.top = tk.BooleanVar(value=autostart)
        self.shark = tk.BooleanVar(value=False)
        self._toolbar()
        self.grid = tk.Frame(root, bg=BG)
        self.grid.pack(padx=8, pady=(0, 4), fill="both", expand=True)
        self.foot = tk.Frame(root, bg=BG)
        self.foot.pack(padx=8, pady=(0, 8), fill="x")
        self.f1 = self._lbl(self.foot, "", FG, ("Consolas", 10))
        self.f2 = self._lbl(self.foot, "", FG, ("Consolas", 10))
        self.status = self._lbl(self.foot, "", DIM, ("Segoe UI", 8))
        for w in (self.f1, self.f2, self.status):
            w.pack(anchor="w")
        self._build(self.n.get())
        self.on_top()
        if autostart:
            self.sym.trace_add("write", lambda *_: self.change_symbol())
            self.exp.trace_add("write", lambda *_: self.refresh())
            root.after(200, self._drain)
            self.refresh()

    # -- chrome ---------------------------------------------------------
    def _lbl(self, parent, text, fg, font, **kw):
        return tk.Label(parent, text=text, fg=fg, bg=kw.pop("bg", BG), font=font,
                        anchor=kw.pop("anchor", "w"), **kw)

    def _toolbar(self):
        bar = tk.Frame(self.root, bg=BG)
        bar.pack(padx=8, pady=8, fill="x")
        ttk.Combobox(bar, textvariable=self.sym, values=SYMBOLS, width=11,
                     state="readonly").pack(side="left")
        self.expbox = ttk.Combobox(bar, textvariable=self.exp, width=14, state="readonly",
                                   values=(AUTO,))
        self.expbox.pack(side="left", padx=4)
        for var, w, tip in ((self.n, 3, "strikes"), (self.secs, 4, "sec")):
            tk.Spinbox(bar, from_=1, to=999, textvariable=var, width=w, bg=BG, fg=FG,
                       insertbackground=FG, buttonbackground=BG,
                       highlightthickness=0, relief="flat").pack(side="left", padx=(4, 1))
            self._lbl(bar, tip, DIM, ("Segoe UI", 8)).pack(side="left")
        for text, var, cmd in (("auto", self.auto, self.refresh),
                               ("on top", self.top, self.on_top),
                               ("shark", self.shark, self.toggle_shark)):
            tk.Checkbutton(bar, text=text, variable=var, command=cmd, bg=BG, fg=DIM,
                           selectcolor=BG, activebackground=BG, activeforeground=FG,
                           highlightthickness=0).pack(side="left", padx=4)
        tk.Button(bar, text="↻", command=self.refresh, bg=BG, fg=FG, relief="flat",
                  activebackground=ATM_BG, activeforeground=FG).pack(side="right")

    def on_top(self):
        self.root.attributes("-topmost", self.top.get())

    def _cols(self):
        return COLS + SHARK_COLS if self.shark.get() else COLS

    def toggle_shark(self):
        """Column count changed, so relay the grid - then redraw off the cached
        payload rather than making the user wait on a fetch."""
        self._build(max(1, self.n.get()))
        if self.last:
            self.render(*self.last)

    def _build(self, n):
        """(Re)lay the label grid - one row per strike, 2n+1 rows."""
        for w in self.grid.winfo_children():
            w.destroy()
        self.cells = []
        cols = self._cols()
        def side(c):
            return "w" if cols[c] in LEFT else "e"

        for c, name in enumerate(cols):
            self._lbl(self.grid, name, DIM, ("Segoe UI", 8, "bold"), anchor=side(c)) \
                .grid(row=0, column=c, sticky="ew", padx=1)
        for r in range(2 * n + 1):
            row = []
            for c in range(len(cols)):
                lb = self._lbl(self.grid, "—", FG, ("Consolas", 11), anchor=side(c),
                               padx=7, pady=1)
                lb.grid(row=r + 1, column=c, sticky="ew", padx=1)
                row.append(lb)
            self.cells.append(row)
        for c in range(len(cols)):
            self.grid.columnconfigure(c, weight=1)

    # -- data -----------------------------------------------------------
    def refresh(self):
        if self.job:
            self.root.after_cancel(self.job)
            self.job = None
        sym, exp, n = self.sym.get(), self.exp.get(), max(1, self.n.get())
        if exp == AUTO:
            # resolve locally off the last payload's list; None makes fetch() ask NSE
            exp = front_expiry(self.expiries)
        self.status.config(text="fetching…", fg=DIM)
        threading.Thread(target=self._work, args=(sym, exp, n), daemon=True).start()

    def _work(self, sym, exp, n):
        try:
            expiry, rec = fetch(sym, expiry=exp)
            self.q.put(("ok", sym, expiry, rec, n))
        except Exception as e:                    # network/parse - keep the last table up
            self.q.put(("err", f"{type(e).__name__}: {e}"))

    def change_symbol(self):
        self.expiries = []                        # another symbol, another expiry ladder
        self.expbox.config(values=(AUTO,))
        self.exp.set(AUTO)                        # write fires the trace, which refreshes

    def _drain(self):
        try:
            while True:
                msg = self.q.get_nowait()
                if msg[0] == "err":
                    self.status.config(text=msg[1], fg=RED)
                else:
                    self.render(*msg[1:])
        except queue.Empty:
            pass
        # closed: stop polling a feed that cannot change. The ↻ button still works,
        # and a live stamp coming back from it restarts the loop on its own.
        if self.auto.get() and self.live and not self.job:
            self.job = self.root.after(max(5, self.secs.get()) * 1000, self.refresh)
        self.root.after(250, self._drain)

    # -- render ---------------------------------------------------------
    def render(self, sym, expiry, rec, n):
        spot, atm, rs = rows(rec, n)
        self.last = (sym, expiry, rec, n)
        if len(self.cells) != len(rs) or (self.cells and len(self.cells[0]) != len(self._cols())):
            self._build(n)
        exps = rec.get("expiryDates") or []
        if isinstance(exps, list) and exps:
            self.expiries = exps
            if list(self.expbox["values"]) != [AUTO] + exps:
                self.expbox.config(values=[AUTO] + exps)
        t = totals(chain(rec), spot)                   # Res/Sup/PCR over every strike
        max_ce, max_pe = t["res"], t["sup"]
        atm_row = next(r for r in rs if r[0] == atm)   # rows() always spans ATM
        lo, hi = rs[0][0], rs[-1][0]

        def off(k):                                    # is the wall outside the window?
            return "" if k is None or lo <= k <= hi else ("↑" if k > hi else "↓")
        sm = shark_matrix(rs, atm, max_ce, max_pe) if self.shark.get() else [None] * len(rs)
        for row, (k, co, cc, po, pc, cp, pp, cpc, ppc), sk in zip(self.cells, rs, sm):
            bg = ATM_BG if k == atm else BG
            tag = strike_tag(cc, pc, cpc, ppc)
            vals = (str(k), fmt(co), sgn(cc), fmt(po), sgn(pc), f"{cp:.1f}", f"{pp:.1f}", tag)
            fgs = (YEL if k == atm else FG, FG, RED if cc > 0 else GRN, FG,
                   GRN if pc > 0 else RED, GRN, RED, TAG_FG.get(tag, DIM))
            bgs = (bg, CE_BG if k == max_ce else bg, bg,
                   PE_BG if k == max_pe else bg, bg, bg, bg, bg)
            if sk:
                _, ce, pe, net, _, note = sk
                vals += (ce, pe, net, note)
                fgs += (action_fg(ce, CE_BULL), action_fg(pe, PE_BULL),
                        VERDICT_FG.get(net, DIM),
                        YEL if ("PIN" in note or "VAC" in note) else DIM)
                bgs += (bg,) * len(SHARK_COLS)
            for lb, v, f, b in zip(row, vals, fgs, bgs):
                lb.config(text=v, fg=f, bg=b)
        bias = bias_tag(t["lean"], t["pcr"])
        self.f1.config(text=f"{sym} {expiry}   spot {spot}   ATM {atm}   "
                            f"PCR {t['pcr']:.2f} {pcr_tag(t['pcr'])}   ▶ {bias}",
                       fg=GRN if bias.startswith("Bullish") else
                          RED if bias.startswith("Bearish") else FG)
        self.f2.config(text=f"Res {max_ce}{off(max_ce)}   Sup {max_pe}{off(max_pe)}   "
                            f"CE {fmt(t['ce'])} {sgn(t['cec'])}   "
                            f"PE {fmt(t['pe'])} {sgn(t['pec'])}   "
                            f"ATM {strike_tag(atm_row[2], atm_row[4], atm_row[7], atm_row[8])}"
                            f"   (whole chain)",
                       fg=DIM)
        stamp = rec.get("timestamp", "")
        self.live, _ = market_live(stamp)
        self.status.config(
            text=f"NSE {stamp}   {'LIVE' if self.live else 'CLOSED — auto-refresh paused'}",
            fg=GRN if self.live else YEL)


def selftest():
    """Build the real UI on a fake payload, render once, close."""
    def leg(s, oi, ch, px, pxch=0.0):
        return {"strikePrice": s, "openInterest": oi, "changeinOpenInterest": ch,
                "lastPrice": px, "change": pxch}
    rec = {"underlyingValue": 23635.1, "timestamp": "08-Sep-2026 15:40:00",
           "expiryDates": ["08-Sep-2026", "15-Sep-2026"],
           "strikePrices": ["23550", "23600", "23650", "23700", "23750"],
           # CE shrinking on a falling premium = unwinding; PE growing on a
           # falling premium = writing, and it moves the most OI, so it leads.
           "data": [{"CE": leg(s, s, -s, 1.0, -0.5), "PE": leg(s, 2 * s, 2 * s, 2.0, -0.5)}
                    for s in (23600, 23650, 23700)]
                   # walls outside the ±1 display window, to prove Res/Sup see them
                   + [{"CE": leg(25000, 9e5, 1e3, 0.5), "PE": leg(25000, 1.0, 0.0, 0.5)},
                      {"CE": leg(22000, 1.0, 0.0, 0.5), "PE": leg(22000, 9e5, 1e3, 0.5)}]}
    root = tk.Tk()
    app = App(root, autostart=False)              # no network, no timers
    app.n.set(1)
    app._build(1)
    app.render("NIFTY", "08-Sep-2026", rec, 1)
    assert len(app.cells) == 3, len(app.cells)
    assert app.cells[1][0].cget("text") == "23650", "ATM row must be the centre row"
    assert app.cells[1][0].cget("fg") == YEL, "ATM strike must be highlighted"
    assert app.cells[0][2].cget("fg") == GRN, "falling CE OI must read green"
    assert app.cells[2][1].cget("text") == "23.7K", app.cells[2][1].cget("text")
    assert app.cells[1][7].cget("text") == "PE writing", app.cells[1][7].cget("text")
    assert app.cells[1][7].cget("fg") == GRN, "PE writing must read green"
    assert list(app.expbox["values"]) == [AUTO] + rec["expiryDates"], "expiry box self-populates"
    assert app.exp.get() == AUTO, "auto must stay selected, not pin to a date"
    assert app.expiries == rec["expiryDates"], "list is cached for local front-expiry lookup"
    assert "ATM PE writing" in app.f2.cget("text"), app.f2.cget("text")

    # Res/Sup come from the whole chain, and say so when the wall is off-window
    assert "Res 25000↑" in app.f2.cget("text"), app.f2.cget("text")
    assert "Sup 22000↓" in app.f2.cget("text"), app.f2.cget("text")
    assert app.cells[1][1].cget("bg") != CE_BG, "off-window wall must not tint a visible cell"

    # shark columns: off by default, appear on toggle, redraw with no refetch
    assert len(app.cells[0]) == len(COLS), "shark columns must be off by default"
    app.shark.set(True)
    app.toggle_shark()
    assert len(app.cells[0]) == len(COLS) + len(SHARK_COLS), len(app.cells[0])
    assert app.cells[1][8].cget("text") == "unwinding", app.cells[1][8].cget("text")
    assert app.cells[1][8].cget("fg") == RED, "call buyers leaving is not bullish"
    assert app.cells[1][9].cget("text") == "writing", "PE writing lays a floor"
    assert app.cells[1][9].cget("fg") == GRN, "written puts read green"
    assert app.cells[1][10].cget("text") == "Bullish" and app.cells[1][10].cget("fg") == GRN
    assert app.cells[1][11].cget("text") == "ATM", app.cells[1][11].cget("text")
    assert app.cells[0][11].cget("text") == "", "off-window walls tag no visible row"
    app.shark.set(False)
    app.toggle_shark()
    assert len(app.cells[0]) == len(COLS), "toggling back must drop the columns"
    assert app.cells[1][7].cget("text") == "PE writing", "base grid survives the round trip"

    assert app.live is False, "stale 15:40 stamp must read as closed"
    app.auto.set(True)
    app._drain()                                  # closed -> must not queue a refresh
    assert app.job is None, "auto-refresh must stay paused while closed"
    app.live = True
    app._drain()
    assert app.job is not None, "live feed must resume the loop"
    app.root.after_cancel(app.job)

    root.after(400, root.destroy)
    root.mainloop()
    print("selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        r = tk.Tk()
        App(r)
        r.mainloop()

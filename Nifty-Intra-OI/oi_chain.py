"""Nifty option chain from NSE's public endpoint — fallback for when
TradingView has no NSE F&O OI entitlement. Prints the same table as
sdx_v11_oi.pine. Stdlib only.

  python oi_chain.py                 # NIFTY, nearest expiry, 5 strikes each side
  python oi_chain.py BANKNIFTY 3     # other index, 3 strikes each side
  python oi_chain.py NIFTY 5 1       # 1 = next expiry instead of nearest
  python oi_chain.py NIFTY 6 --shark # add the Shark hunting matrix
"""
import datetime, gzip, http.cookiejar, io, json, sys, urllib.error, urllib.parse, urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")
HDR = {"User-Agent": UA, "Accept": "application/json, text/plain, */*",
       "Accept-Language": "en-US,en;q=0.9", "Accept-Encoding": "gzip",
       "Referer": "https://www.nseindia.com/option-chain"}
API = "https://www.nseindia.com/api/"


_opener = None


def _session(fresh=False):
    """Cookie jar reused across refreshes; NSE hands out the cookies the API
    needs only on a page hit, so bootstrap once and re-do it if they expire."""
    global _opener
    if fresh or _opener is None:
        _opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        _opener.open(urllib.request.Request("https://www.nseindia.com/option-chain",
                                            headers=HDR), timeout=15).read()
    return _opener


def _get(path, fresh=False):
    raw = _session(fresh).open(urllib.request.Request(API + path, headers=HDR), timeout=15).read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
    return json.loads(raw)


def get(path):
    try:
        return _get(path)
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError):
        return _get(path, fresh=True)          # stale cookies: bootstrap and retry once


def fetch(symbol, expiry=None, exp_idx=0):
    if expiry is None:                             # follow the current weekly on its own
        exps = get(f"option-chain-contract-info?symbol={symbol}")["expiryDates"]
        i = exps.index(front_expiry(exps)) + exp_idx
        expiry = exps[min(i, len(exps) - 1)]
    # ponytail: v3 needs an explicit expiry; the old option-chain-indices path is 404 now
    q = urllib.parse.urlencode({"type": "Indices", "symbol": symbol, "expiry": expiry})
    return expiry, get("option-chain-v3?" + q)["records"]


def fmt(x):
    a = abs(x)
    return f"{x/1e5:.2f}L" if a >= 1e5 else f"{x/1e3:.1f}K" if a >= 1e3 else f"{x:.0f}"


def sgn(x):
    return ("+" if x >= 0 else "") + fmt(x)


IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


def market_live(stamp, now=None):
    """NSE's own feed timestamp is the market clock: it freezes at the close and
    never ticks on a holiday, so a stale stamp means closed. Returns (live, age_min).
    ponytail: no holiday calendar needed; costs a correct local clock instead."""
    try:
        t = datetime.datetime.strptime(stamp, "%d-%b-%Y %H:%M:%S").replace(tzinfo=IST)
    except (ValueError, TypeError):
        return False, float("inf")
    age = ((now or datetime.datetime.now(IST)) - t).total_seconds() / 60
    return age < 5, age


def front_expiry(expiries, now=None):
    """The current weekly: the nearest expiry still trading. Today's contract dies
    at 15:30 IST, so after the close the front rolls to the next one."""
    now = now or datetime.datetime.now(IST)
    dead_today = now.time() >= datetime.time(15, 30)
    dated = []
    for e in expiries:
        try:
            dated.append((datetime.datetime.strptime(e, "%d-%b-%Y").date(), e))
        except (ValueError, TypeError):
            continue
    for d, e in sorted(dated):
        if d > now.date() or (d == now.date() and not dead_today):
            return e
    return dated[-1][1] if dated else None


def chain(rec):
    """Every strike of the fetched expiry, not just the display window.
    Same row shape as rows(), so totals() can take either."""
    out = []
    for r in rec.get("data", []):
        ce, pe = r.get("CE", {}), r.get("PE", {})
        k = ce.get("strikePrice", pe.get("strikePrice"))
        out.append((k, ce.get("openInterest", 0), ce.get("changeinOpenInterest", 0),
                    pe.get("openInterest", 0), pe.get("changeinOpenInterest", 0),
                    ce.get("lastPrice", 0), pe.get("lastPrice", 0),
                    ce.get("change", 0), pe.get("change", 0)))
    return out


def totals(ch):
    """Chain-wide read: OI sums, PCR, and the true max-OI strikes (Res / Sup)."""
    if not ch:
        return dict(ce=0, pe=0, cec=0, pec=0, lean=0, pcr=float("nan"), res=None, sup=None)
    ce, pe = sum(r[1] for r in ch), sum(r[3] for r in ch)
    # lean aggregates what each leg did, not just how much OI moved - so a chain
    # full of bought puts reads bearish instead of masquerading as support.
    lean = sum(_lean(leg_action(r[2], r[7]), CE_BULL, r[2])
               + _lean(leg_action(r[4], r[8]), PE_BULL, r[4]) for r in ch)
    return dict(ce=ce, pe=pe, cec=sum(r[2] for r in ch), pec=sum(r[4] for r in ch),
                lean=lean, pcr=pe / ce if ce else float("nan"),
                res=max(ch, key=lambda r: r[1])[0], sup=max(ch, key=lambda r: r[3])[0])


def pcr_tag(pcr):
    if pcr != pcr:                                 # nan
        return "n/a"
    return "Bullish" if pcr > 1.2 else "Bearish" if pcr < 0.8 else "Neutral"


def leg_action(oi_chg, px_chg):
    """The classic OI-vs-price quadrant, for one option leg. OI rising on a
    falling premium is fresh money on the offer (writing a wall); OI rising on a
    rising premium is fresh money on the bid (buying a punt). Falling OI is
    somebody going home - which side went home depends on the premium again."""
    if oi_chg > 0:
        return "buildup" if px_chg > 0 else "writing"
    if oi_chg < 0:
        return "covering" if px_chg > 0 else "unwinding"
    return "-"                                     # nobody touched this leg


# Calls and puts read mirror-image: writing calls caps price, writing puts floors
# it; a writer buying back removes the wall they built.
CE_BULL = {"buildup": True,  "covering": True,  "writing": False, "unwinding": False}
PE_BULL = {"buildup": False, "covering": False, "writing": True,  "unwinding": True}


def strike_tag(cc, pc, cpc=0, ppc=0):
    """Per-strike headline: whichever leg moved more OI, and what it actually did.
    Premium direction is what separates writing from buying - without it, every
    rise in call OI looks like resistance even when it is call buyers."""
    ce, pe = leg_action(cc, cpc), leg_action(pc, ppc)
    if ce == "-" and pe == "-":
        return "-"
    if abs(cc) >= abs(pc):
        return f"CE {ce}" if ce != "-" else f"PE {pe}"
    return f"PE {pe}" if pe != "-" else f"CE {ce}"


def _lean(action, table, oi_chg):
    """One leg's signed weight: how much OI moved, pointed the way it leans."""
    b = table.get(action)
    return 0 if b is None else (abs(oi_chg) if b else -abs(oi_chg))


def shark_row(cc, pc, cpc=0, ppc=0):
    """One strike's two legs judged independently, the way GTI's Shark matrix
    presents them - except off real OI and premium rather than spot-vs-VWAP.
    Score weighs each leg by the OI it moved and signs it by what that OI did:
    rising put OI is a floor only when the premium fell. When both legs are being
    written this reduces to pc - cc, which is where it started."""
    ce, pe = leg_action(cc, cpc), leg_action(pc, ppc)
    return ce, pe, _lean(ce, CE_BULL, cc) + _lean(pe, PE_BULL, pc)


def shark_matrix(rs, atm, res=None, sup=None):
    """The strike ladder with a per-leg and a net read on each rung.
    ponytail: the neutral band scales off the loudest strike in the window, so it
    reads the same on a dead morning and on expiry day with no magic constant."""
    scored = [(r, shark_row(r[2], r[4], r[7], r[8])) for r in rs]
    band = 0.1 * max([abs(s) for _, (_, _, s) in scored] or [0])
    out = []
    for r, (ce, pe, score) in scored:
        k, cc, pc = r[0], r[2], r[4]
        net = "Bullish" if score > band else "Bearish" if score < -band else "Neutral"
        note = " ".join(n for n in (
            "ATM" if k == atm else "",
            "RES" if k == res else "SUP" if k == sup else "",
            # Both legs genuinely written = the strike is pinned. Both legs
            # shrinking = the walls are coming off and the range can give way.
            "PIN" if ce == "writing" and pe == "writing"
            else "VAC" if cc < 0 and pc < 0 else "",
        ) if n)
        out.append((k, ce, pe, net, score, note))
    return out


def print_shark(rs, atm, res=None, sup=None):
    print("  Shark hunting matrix   (per-leg OI x premium; Net = wall-building)")
    print(f"  {'Strike':>7} {'CE':>10} {'PE':>10} {'Net':>8} {'Score':>9}  Note")
    for k, ce, pe, net, score, note in shark_matrix(rs, atm, res, sup):
        print(f"  {k:>7} {ce:>10} {pe:>10} {net:>8} {sgn(score):>9}  {note}")
    print("  writing = wall built   buildup = bought   covering/unwinding = closing")
    print("  PIN both legs written (pinned)   VAC both legs shrinking (walls off)\n")


def bias_tag(lean, pcr):
    """Headline: the chain-wide positioning lean, and whether PCR agrees with it."""
    oi = "Bullish" if lean > 0 else "Bearish" if lean < 0 else "Neutral"
    p = pcr_tag(pcr)
    if oi == "Neutral" or p in ("Neutral", "n/a"):
        return oi if oi != "Neutral" else p
    return f"{oi} (confirmed)" if oi == p else f"{oi} (PCR disagrees)"


def rows(rec, n):
    strikes = sorted(int(float(s)) for s in rec["strikePrices"])  # v3 sends them as strings
    step = min(b - a for a, b in zip(strikes, strikes[1:]))
    spot = rec["underlyingValue"]
    atm = round(spot / step) * step
    wanted = [atm + i * step for i in range(-n, n + 1)]
    by_strike = {r["CE"]["strikePrice"] if "CE" in r else r["PE"]["strikePrice"]: r
                 for r in rec["data"]}
    out = []
    for k in wanted:
        r = by_strike.get(k, {})
        ce, pe = r.get("CE", {}), r.get("PE", {})
        # "change" is the premium move on the same baseline as the OI change,
        # so the quadrant needs no snapshot of our own.
        out.append((k, ce.get("openInterest", 0), ce.get("changeinOpenInterest", 0),
                    pe.get("openInterest", 0), pe.get("changeinOpenInterest", 0),
                    ce.get("lastPrice", 0), pe.get("lastPrice", 0),
                    ce.get("change", 0), pe.get("change", 0)))
    return spot, atm, out


def report(symbol, expiry, stamp, spot, atm, rs, ch=(), shark=False):
    sce, spe = sum(r[1] for r in rs), sum(r[3] for r in rs)
    scec, spec = sum(r[2] for r in rs), sum(r[4] for r in rs)
    t = totals(list(ch) or rs)                     # whole chain when given, else the window
    live, _ = market_live(stamp)
    print(f"\n{symbol} {expiry}   spot {spot}   ATM {atm}   {stamp}"
          f"   [{'LIVE' if live else 'CLOSED'}]\n")
    print(f"{'Strike':>7} {'CE OI':>9} {'CE d':>9} {'PE OI':>9} {'PE d':>9} "
          f"{'CE':>8} {'PE':>8}  Signal")
    for k, co, cc, po, pc, cp, pp, cpc, ppc in rs:
        mark = " <" if k == atm else "  "
        print(f"{k:>7} {fmt(co):>9} {sgn(cc):>9} {fmt(po):>9} {sgn(pc):>9} "
              f"{cp:>8.1f} {pp:>8.1f}{mark} {strike_tag(cc, pc, cpc, ppc)}")
    print(f"\n  Window {fmt(sce):>8} {sgn(scec):>9} {fmt(spe):>9} {sgn(spec):>9}")
    print(f"  Chain  {fmt(t['ce']):>8} {sgn(t['cec']):>9} {fmt(t['pe']):>9} {sgn(t['pec']):>9}")
    print(f"  PCR {t['pcr']:.2f} {pcr_tag(t['pcr'])}   Res {t['res']}   Sup {t['sup']}"
          f"   (chain-wide)")
    print(f"  ATM {strike_tag(*next((r[2], r[4], r[7], r[8]) for r in rs if r[0] == atm))}"
          f"   >> {bias_tag(t['lean'], t['pcr'])}\n")
    if shark:
        print_shark(rs, atm, t["res"], t["sup"])


def selftest():
    def leg(s, oi, ch, px, pxch=0.0):
        return {"strikePrice": s, "openInterest": oi, "changeinOpenInterest": ch,
                "lastPrice": px, "change": pxch}
    rec = {"underlyingValue": 23635.1, "strikePrices": [23500, 23550, 23600, 23650, 23700],
           "data": [{"CE": leg(s, s, s, 1.0, -0.5), "PE": leg(s, 2 * s, 2 * s, 2.0, -0.5)}
                    for s in (23600, 23650)]}
    assert len(rows(rec, 1)[2][0]) == 9, "rows must carry both premium changes"
    spot, atm, rs = rows(rec, 1)
    assert atm == 23650, atm
    assert [r[0] for r in rs] == [23600, 23650, 23700]
    assert rs[2][1] == 0, "missing strike must fall back to 0, not KeyError"
    assert rs[0][3] == 47200 and fmt(47200) == "47.2K" and sgn(-47200) == "-47.2K"

    now = datetime.datetime(2026, 9, 8, 15, 40, tzinfo=IST)
    assert market_live("08-Sep-2026 15:39:00", now)[0], "1 min old feed is live"
    assert not market_live("08-Sep-2026 15:30:00", now)[0], "10 min old feed is closed"
    assert not market_live("05-Sep-2026 15:30:00", now)[0], "holiday: stamp never advances"
    assert not market_live("", now)[0] and not market_live(None, now)[0]
    assert pcr_tag(1.5) == "Bullish" and pcr_tag(0.5) == "Bearish" and pcr_tag(1.0) == "Neutral"
    assert leg_action(100, -5) == "writing", "OI up, premium down = a wall"
    assert leg_action(100, 5) == "buildup", "OI up, premium up = buyers, not writers"
    assert leg_action(-100, 5) == "covering" and leg_action(-100, -5) == "unwinding"
    assert leg_action(0, 5) == "-", "no OI change is no position change"
    assert strike_tag(100, -50) == "CE writing" and strike_tag(-50, 100) == "PE writing"
    assert strike_tag(100, -50, 5, 0) == "CE buildup", "rising premium is call buying"
    assert strike_tag(-100, -50) == "CE unwinding" and strike_tag(-50, -100) == "PE unwinding"
    assert rs[0][7] == -0.5 and rs[0][8] == -0.5, "premium change reaches the row"
    assert strike_tag(0, 0) == "-", "an untouched strike is not an unwind"
    assert bias_tag(89, 1.5) == "Bullish (confirmed)", bias_tag(89, 1.5)
    assert bias_tag(89, 0.5) == "Bullish (PCR disagrees)"
    assert bias_tag(-89, 1.0) == "Bearish", "neutral PCR must not veto the OI read"
    assert bias_tag(0, 1.5) == "Bullish", "flat positioning falls back to PCR"

    exps = ["08-Sep-2026", "15-Sep-2026", "22-Sep-2026"]
    at_open = datetime.datetime(2026, 9, 8, 10, 0, tzinfo=IST)
    after = datetime.datetime(2026, 9, 8, 15, 40, tzinfo=IST)
    assert front_expiry(exps, at_open) == "08-Sep-2026", "during the session, today is front"
    assert front_expiry(exps, after) == "15-Sep-2026", "after 15:30 the front must roll"
    assert front_expiry(exps, datetime.datetime(2026, 9, 9, 10, 0, tzinfo=IST)) == "15-Sep-2026"
    assert front_expiry(["05-Sep-2026"], after) == "05-Sep-2026", "all past: keep the last"
    assert front_expiry([], after) is None

    assert shark_row(100, 50, -1, -1)[:2] == ("writing", "writing"), "both walls"
    assert shark_row(0, 0) == ("-", "-", 0), "a strike nobody touched has no read"
    # call longs leaving (-100) is bearish, written puts (+50) bullish: -100 + 50
    assert shark_row(-100, 50)[2] == -50, "score signs each leg by what it did"
    assert shark_row(100, 50, -1, -1)[2] == -50, "both written: reduces to pc - cc"
    assert shark_row(100, 50, -1, +1)[2] == -150, "bought puts count against, not for"
    assert CE_BULL["writing"] is False and PE_BULL["writing"] is True

    sm = shark_matrix(rs, atm, res=23650, sup=23600)
    assert [r[3] for r in sm] == ["Bullish", "Bullish", "Neutral"], [r[3] for r in sm]
    assert sm[2][1] == "-" and sm[2][2] == "-", "missing strike must read blank"
    assert "ATM" in sm[1][5] and "RES" in sm[1][5], sm[1][5]
    assert "SUP" in sm[0][5] and "ATM" not in sm[0][5], sm[0][5]
    # flags need a strike that is not the ATM, so the note holds only the flag
    assert shark_matrix([(1, 0, 100, 0, 50, 0, 0, -1, -1)], None)[0][5] == "PIN"
    assert shark_matrix([(1, 0, 100, 0, 50, 0, 0, 5, -1)], None)[0][5] == "", \
        "call buying is not a pin, however much OI it adds"
    assert shark_matrix([(1, 0, -100, 0, -50, 0, 0, 0, 0)], None)[0][5] == "VAC"
    assert shark_matrix([(1, 0, 0, 0, 0, 0, 0, 0, 0)], None)[0][3] == "Neutral", "no divide by zero"
    assert shark_matrix([], None) == [], "empty window must not raise"

    ch = chain(rec)
    t = totals(ch)
    assert len(ch[0]) == len(rs[0]), "chain() and rows() must stay interchangeable"
    assert t["res"] == 23650 and t["sup"] == 23650, t          # only 2 strikes in the fixture
    assert t["ce"] == 47250 and t["pcr"] == 2.0, t
    # both legs written on a falling premium: calls against, puts for, puts bigger
    assert t["lean"] == 47250, t["lean"]
    assert totals([])["res"] is None and totals([])["lean"] == 0, "empty chain must not raise"

    report("SELFTEST", "08-Sep-2026", "08-Sep-2026 15:39:00", spot, atm, rs, ch=ch, shark=True)
    print("selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        a = sys.argv[1:]
        shark = "--shark" in a
        a = [x for x in a if not x.startswith("--")]
        sym = a[0] if a else "NIFTY"
        n = int(a[1]) if len(a) > 1 else 5
        idx = int(a[2]) if len(a) > 2 else 0
        expiry, rec = fetch(sym, exp_idx=idx)
        report(sym, expiry, rec["timestamp"], *rows(rec, n), ch=chain(rec), shark=shark)

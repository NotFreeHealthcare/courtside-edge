"""Backtest of the Courtside Edge game model, a direct port of the app's analyze()/evaluate()/stakeFor().
Point-in-time: each game is predicted only from games played before it.
Not covered: injuries (no historical injury reports), head-to-head/matchup/form nudges, line movement.
Usage: python3 tools/backtest.py DIR [--params JSON]"""
import json, math, sys, collections, statistics as st

D = sys.argv[1]
P = dict(hca=2.0, sdM=12.5, sdT=18.0, K=10, Kno=8, R=0.7, b2b=1.5, trust=0.4)  # the app's current settings
if '--params' in sys.argv: P.update(json.loads(sys.argv[sys.argv.index('--params') + 1]))
SET = dict(bank=2000, kelly=0.5, maxBet=500, maxPct=5, minBet=20, minEdge=2, minConf=50, winMode=True, minWinP=55)

def Phi(x): return 0.5 * (1 + math.erf(x / math.sqrt(2)))
def clamp(x, a, b): return max(a, min(b, x))
def load(s):
    g = json.load(open(f'{D}/games_{s}.json'))
    n = collections.Counter([x['h'] for x in g] + [x['a'] for x in g])
    real = {t for t, c in n.items() if c >= 10}          # drops All-Star / Rising Stars exhibition teams
    return [x for x in g if x['h'] in real and x['a'] in real]

def season_table(games):
    t = collections.defaultdict(lambda: [0, 0, 0, 0])  # pf, pa, w, l
    for g in games:
        for me, op, pf, pa in ((g['h'], g['a'], g['hs'], g['as_']), (g['a'], g['h'], g['as_'], g['hs'])):
            r = t[me]; r[0] += pf; r[1] += pa; r[2 if pf > pa else 3] += 1
    return {k: dict(pf=v[0] / (v[2] + v[3]), pa=v[1] / (v[2] + v[3]), gp=v[2] + v[3]) for k, v in t.items()}

def predict_season(games, prev, p):
    """Yield (game, margin, total, pHome) using only earlier games, like the app does with live standings."""
    tot = collections.defaultdict(lambda: [0, 0, 0])  # pf, pa, gp
    last_day = {}
    lg_prev = st.mean(v['pf'] for v in prev.values()) if prev else None
    out = []
    by_day = collections.defaultdict(list)
    for g in games: by_day[g['day']].append(g)
    for day in sorted(by_day):
        gpts = [v[0] / v[2] for v in tot.values() if v[2]]
        lg = st.mean(gpts) if len(gpts) >= 10 else (lg_prev or 114.0)
        for g in by_day[day]:
            def rating(t):
                v = tot[t]; gp = v[2]; pv = prev.get(t) if prev else None
                K = p['K'] if pv else p['Kno']; R = p['R']
                pf = v[0] / gp if gp else lg; pa = v[1] / gp if gp else lg
                pN = (pv['pf'] - pv['pa']) * R if pv else 0
                pO = (pv['pf'] - lg_prev) * R if pv else 0
                pD = (pv['pa'] - lg_prev) * R if pv else 0
                mix = lambda c, q: (c * gp + q * K) / (gp + K)
                return dict(net=mix(pf - pa, pN), off=mix(pf - lg, pO), dff=mix(pa - lg, pD), gp=gp)
            H, A = rating(g['h']), rating(g['a'])
            prevday = (lambda d: d)(None)
            rH = -p['b2b'] if last_day.get(g['h']) == yday(day) else 0
            rA = -p['b2b'] if last_day.get(g['a']) == yday(day) else 0
            margin = H['net'] - A['net'] + p['hca'] + rH - rA
            total = 2 * lg + H['off'] + A['dff'] + A['off'] + H['dff'] + 0.3 * (rH + rA)
            out.append((g, margin, total, Phi(margin / p['sdM']), min(H['gp'], A['gp'])))
        for g in by_day[day]:
            for me, pf, pa in ((g['h'], g['hs'], g['as_']), (g['a'], g['as_'], g['hs'])):
                v = tot[me]; v[0] += pf; v[1] += pa; v[2] += 1
            last_day[g['h']] = day; last_day[g['a']] = day
    return out

import datetime
def yday(d): return (datetime.datetime.strptime(d, '%Y%m%d') - datetime.timedelta(days=1)).strftime('%Y%m%d')

def novig(o1, o2): return (1 / o1) / (1 / o1 + 1 / o2) if o1 and o2 and o1 > 1 and o2 > 1 else None

def conf(ev, p, pModel, pMkt, gp):
    edge = clamp(ev / 0.08, 0, 1) * 30; prob = clamp((p - 0.45) / 0.25, 0, 1) * 25
    data = clamp(gp / 20, 0, 1) * 15 + 6  # ESPN posted line
    agree = 8 if pMkt is None else 20 * (1 - clamp(abs(pModel - pMkt) / 0.15, 0, 1))
    return round(clamp(edge + prob + data + agree, 0, 99))

def ll(p, y): p = clamp(p, 0.01, 0.99); return -math.log(p if y else 1 - p)

def evaluate(rows, p, label, bet=True):
    res = dict(label=label, n=len(rows))
    y = [r[0]['hs'] > r[0]['as_'] for r in rows]
    res['acc_model'] = st.mean((r[3] > .5) == yy for r, yy in zip(rows, y))
    res['ll_model'] = st.mean(ll(r[3], yy) for r, yy in zip(rows, y))
    res['mae_margin'] = st.mean(abs((r[0]['hs'] - r[0]['as_']) - r[1]) for r in rows)
    res['mae_total'] = st.mean(abs((r[0]['hs'] + r[0]['as_']) - r[2]) for r in rows)
    res['bias_margin'] = st.mean((r[0]['hs'] - r[0]['as_']) - r[1] for r in rows)
    res['bias_total'] = st.mean((r[0]['hs'] + r[0]['as_']) - r[2] for r in rows)
    res['sd_margin'] = st.pstdev([(r[0]['hs'] - r[0]['as_']) - r[1] for r in rows])
    res['sd_total'] = st.pstdev([(r[0]['hs'] + r[0]['as_']) - r[2] for r in rows])
    mk = [(r, yy, novig(r[0].get('mlH'), r[0].get('mlA'))) for r, yy in zip(rows, y)]
    mk = [x for x in mk if x[2] is not None]
    if mk:
        res['n_mkt'] = len(mk)
        res['acc_mkt'] = st.mean((m > .5) == yy for r, yy, m in mk)
        res['ll_mkt'] = st.mean(ll(m, yy) for r, yy, m in mk)
        res['ll_model_same'] = st.mean(ll(r[3], yy) for r, yy, m in mk)
        res['ll_blend'] = st.mean(ll(p['trust'] * r[3] + (1 - p['trust']) * m, yy) for r, yy, m in mk)
        sp = [r for r in rows if r[0].get('spH') is not None]
        res['mae_spread_mkt'] = st.mean(abs((r[0]['hs'] - r[0]['as_']) + r[0]['spH']) for r in sp)
        res['mae_spread_model_same'] = st.mean(abs((r[0]['hs'] - r[0]['as_']) - r[1]) for r in sp)
        tt = [r for r in rows if r[0].get('tot')]
        res['mae_total_mkt'] = st.mean(abs((r[0]['hs'] + r[0]['as_']) - r[0]['tot']) for r in tt)
        res['mae_total_model_same'] = st.mean(abs((r[0]['hs'] + r[0]['as_']) - r[2]) for r in tt)
        # calibration of the final blended probability on the favourite side
        bins = collections.defaultdict(list)
        for r, yy, m in mk:
            q = p['trust'] * r[3] + (1 - p['trust']) * m; fav = q if q >= .5 else 1 - q; won = yy if q >= .5 else not yy
            bins[min(int(fav * 10), 9)].append((fav, won))
        res['calib'] = {f'{k*10}-{k*10+10}%': (len(v), round(st.mean(a for a, _ in v), 3), round(st.mean(b for _, b in v), 3)) for k, v in sorted(bins.items())}
    if bet and mk: res['bets'] = simulate(rows, p)
    return res

def simulate(rows, p):
    """Bet the way the app does: best qualifying selection per game, half Kelly, caps, filters."""
    bank = SET['bank']; log = []
    for r, margin, total, pH, gp in ((x[0], x[1], x[2], x[3], x[4]) for x in rows):
        cands = []
        def add(key, pModel, odds, pairOdds, win):
            if not odds or odds <= 1: return
            pMkt = novig(odds, pairOdds) if pairOdds else None
            q = p['trust'] * pModel + (1 - p['trust']) * pMkt if pMkt is not None else pModel
            ev = q * odds - 1; c = conf(ev, q, pModel, pMkt, gp)
            if ev * 100 < SET['minEdge'] or c < SET['minConf'] or (SET['winMode'] and q * 100 < SET['minWinP']): return
            f = (q * odds - 1) / (odds - 1); stake = math.floor(min(bank * f * SET['kelly'], SET['maxBet'], bank * SET['maxPct'] / 100) / 10) * 10
            if stake < SET['minBet']: return
            cands.append((ev * c, key, odds, stake, q, win))
        hs, as_ = r['hs'], r['as_']; mg = hs - as_; tt = hs + as_
        add('mlH', pH, r.get('mlH'), r.get('mlA'), 1 if mg > 0 else 0)
        add('mlA', 1 - pH, r.get('mlA'), r.get('mlH'), 1 if mg < 0 else 0)
        if r.get('spH') is not None:
            sp = r['spH']; pS = Phi((margin + sp) / p['sdM']); v = mg + sp
            add('spH', pS, r.get('spOddsH') or 1.91, r.get('spOddsA') or 1.91, 1 if v > 0 else (.5 if v == 0 else 0))
            add('spA', 1 - pS, r.get('spOddsA') or 1.91, r.get('spOddsH') or 1.91, 1 if v < 0 else (.5 if v == 0 else 0))
        if r.get('tot'):
            L = r['tot']; pO = 1 - Phi((L - total) / p['sdT']); v = tt - L
            add('ov', pO, r.get('ovOdds') or 1.91, r.get('unOdds') or 1.91, 1 if v > 0 else (.5 if v == 0 else 0))
            add('un', 1 - pO, r.get('unOdds') or 1.91, r.get('ovOdds') or 1.91, 1 if v < 0 else (.5 if v == 0 else 0))
        if not cands: continue
        _, key, odds, stake, q, win = max(cands)
        prof = 0 if win == .5 else (stake * (odds - 1) if win else -stake)
        bank += prof; log.append((key, odds, stake, q, win, prof))
    if not log: return dict(n=0)
    dec = [x for x in log if x[4] != .5]
    return dict(n=len(log), win_rate=round(st.mean(x[4] for x in dec), 3), pred=round(st.mean(x[3] for x in dec), 3),
        breakeven=round(st.mean(1 / x[1] for x in dec), 3), staked=sum(x[2] for x in log), profit=round(sum(x[5] for x in log)),
        roi=round(sum(x[5] for x in log) / sum(x[2] for x in log), 3), end_bank=round(bank),
        by_market={k: (sum(1 for x in log if x[0][:2] == k), round(sum(x[5] for x in log if x[0][:2] == k))) for k in ('ml', 'sp', 'ov', 'un')})

def run(p, quiet=False):
    g25, g26, g27 = load(2025), load(2026), load(2027)
    t25, t26 = season_table(g25), season_table(g26)
    r25 = predict_season(g25, None, p)
    r26 = predict_season(g26, t25, p)
    r27 = predict_season(g27, t26, p)
    half = sorted(g['day'] for g in g26)[len(g26) // 2]
    return dict(r25=r25, r26a=[r for r in r26 if r[0]['day'] < half], r26b=[r for r in r26 if r[0]['day'] >= half], r27=r27)

if __name__ == '__main__':
    R = run(P)
    for k, lab in (('r25', '2024-25 (tune)'), ('r26a', '2025-26 1st half (tune)'), ('r26b', '2025-26 2nd half (TEST)'), ('r27', '2026-27 to date (TEST)')):
        print(json.dumps(evaluate(R[k], P, lab), default=str))

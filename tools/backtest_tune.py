"""Re-fit a few model settings on the tuning seasons only (2024-25 + first half of 2025-26).
Small grid over physically meaningful values, scored by log-loss, so the fit can't chase noise."""
import sys, json, itertools, statistics as st, importlib.util
spec = importlib.util.spec_from_file_location('bt', __file__.replace('backtest_tune.py', 'backtest.py')); bt = importlib.util.module_from_spec(spec)
sys.argv = [sys.argv[0], sys.argv[1]]; spec.loader.exec_module(bt)
def ll_model(rows): return st.mean(bt.ll(r[3], r[0]['hs'] > r[0]['as_']) for r in rows)
best = None
for hca, sd, K, R in itertools.product([1.0, 1.5, 2.0, 2.5], [12.5, 13.5, 14.0, 14.5, 15.0], [6, 10, 15, 20], [0.5, 0.6, 0.7, 0.8]):
    p = dict(bt.P, hca=hca, sdM=sd, K=K, R=R)
    R_ = bt.run(p); tune = R_['r25'] + R_['r26a']
    s = ll_model(tune)
    if not best or s < best[0]: best = (s, p)
p = best[1]
R_ = bt.run(p); tr = [r for r in R_['r25'] + R_['r26a']]
p['sdT'] = round(st.pstdev([(r[0]['hs'] + r[0]['as_']) - r[2] for r in tr]) * 2) / 2
mk = [(r, bt.novig(r[0].get('mlH'), r[0].get('mlA'))) for r in R_['r26a']]; mk = [x for x in mk if x[1]]
ws = [(st.mean(bt.ll(w * r[3] + (1 - w) * m, r[0]['hs'] > r[0]['as_']) for r, m in mk), w) for w in [i / 20 for i in range(0, 13)]]
p['trust'] = min(ws)[1]
print(json.dumps({k: p[k] for k in ('hca', 'sdM', 'sdT', 'K', 'R', 'trust')}))
print('trust curve', [(w, round(s, 4)) for s, w in ws])

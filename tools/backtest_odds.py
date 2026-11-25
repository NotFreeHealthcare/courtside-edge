"""Add DraftKings closing lines (from ESPN pickcenter) to the backtest game files.
Usage: python3 tools/backtest_odds.py DIR"""
import json, sys, urllib.request, concurrent.futures as cf, glob

D = sys.argv[1]
E = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event='

def dec(a):
    try: a = float(a)
    except Exception: return None
    if a == 0: return None
    return 1 + a / 100 if a > 0 else 1 + 100 / -a

def odds(gid):
    for _ in range(3):
        try:
            j = json.load(urllib.request.urlopen(E + gid, timeout=30)); break
        except Exception:
            j = None
    if not j: return None
    pc = j.get('pickcenter') or []
    if not pc: return {}
    o = pc[0]; h = o.get('homeTeamOdds', {}); a = o.get('awayTeamOdds', {})
    sp = o.get('spread')
    # ESPN's "spread" is from the home side's view when details names the home favourite; verify with homeTeamOdds.favorite
    if sp is not None and h.get('favorite') is not None:
        sp = -abs(sp) if h.get('favorite') else abs(sp)
    return dict(mlH=dec(h.get('moneyLine')), mlA=dec(a.get('moneyLine')), spH=sp, tot=o.get('overUnder'),
                spOddsH=dec(h.get('spreadOdds')), spOddsA=dec(a.get('spreadOdds')), ovOdds=dec(o.get('overOdds')), unOdds=dec(o.get('underOdds')))

for path in sorted(glob.glob(f'{D}/games_*.json')):
    g = json.load(open(path))
    todo = [r for r in g if 'oddsDone' not in r]
    with cf.ThreadPoolExecutor(12) as ex:
        for r, o in zip(todo, ex.map(lambda r: odds(r['id']), todo)):
            if o is None: continue
            r.update({k: v for k, v in o.items() if v is not None}); r['oddsDone'] = True
    json.dump(g, open(path, 'w'))
    print(path.split('/')[-1], 'games', len(g), 'with moneyline', sum(1 for r in g if r.get('mlH') and r.get('mlA')), 'with spread', sum(1 for r in g if r.get('spH') is not None))

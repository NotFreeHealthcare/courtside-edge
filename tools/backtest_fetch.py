"""Download historical NBA results + closing odds from ESPN for the backtest.
Usage: python3 tools/backtest_fetch.py OUTDIR
Seasons are ESPN season years (2025 = 2024-25)."""
import json, os, sys, datetime, urllib.request, concurrent.futures as cf

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
E = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba'

def get(url):
    for _ in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.load(r)
        except Exception as e:
            err = e
    raise err

# Season date windows (regular season only; type 2 filter below)
SEASONS = {2025: ('20241022', '20250413'), 2026: ('20251021', '20260412'), 2027: ('20261020', datetime.date.today().strftime('%Y%m%d'))}

def days(a, b):
    d = datetime.datetime.strptime(a, '%Y%m%d'); e = datetime.datetime.strptime(b, '%Y%m%d')
    while d <= e:
        yield d.strftime('%Y%m%d'); d += datetime.timedelta(days=1)

def dec(a):
    try: a = float(str(a).replace('+', ''))
    except Exception: return None
    if a == 0: return None
    return 1 + a / 100 if a > 0 else 1 + 100 / -a

def num(x):
    try: return float(str(x).lstrip('ou'))
    except Exception: return None

def one_day(d):
    j = get(f'{E}/scoreboard?dates={d}&limit=50')
    rows = []
    for ev in j.get('events', []):
        if ev.get('season', {}).get('type') not in (2, None): continue
        c = ev['competitions'][0]
        if not c['status']['type'].get('completed'): continue
        h = next(x for x in c['competitors'] if x['homeAway'] == 'home'); a = next(x for x in c['competitors'] if x['homeAway'] == 'away')
        o = (c.get('odds') or [{}])[0]
        ml = o.get('moneyline', {}); ps = o.get('pointSpread', {}); tt = o.get('total', {})
        sp = num(ps.get('home', {}).get('close', {}).get('line'))
        if sp is None and o.get('spread') is not None:
            # legacy: details like "BOS -7.5"
            det = o.get('details', '') or ''
            parts = det.split()
            if len(parts) == 2 and num(parts[1]) is not None:
                v = num(parts[1]); sp = v if parts[0] == h['team']['abbreviation'] else -v
        rows.append(dict(id=ev['id'], date=ev['date'], day=d, type=ev.get('season', {}).get('type'),
            h=h['team']['id'], a=a['team']['id'], ha=h['team']['abbreviation'], aa=a['team']['abbreviation'],
            hs=int(float(h['score'])), as_=int(float(a['score'])),
            mlH=dec(ml.get('home', {}).get('close', {}).get('odds') or o.get('homeTeamOdds', {}).get('moneyLine')),
            mlA=dec(ml.get('away', {}).get('close', {}).get('odds') or o.get('awayTeamOdds', {}).get('moneyLine')),
            spH=sp, tot=num(tt.get('over', {}).get('close', {}).get('line')) or num(o.get('overUnder'))))
    return rows

for season, (a, b) in SEASONS.items():
    path = f'{OUT}/games_{season}.json'
    if os.path.exists(path) and season != 2027: continue
    with cf.ThreadPoolExecutor(8) as ex:
        allrows = [r for rs in ex.map(one_day, list(days(a, b))) for r in rs]
    allrows.sort(key=lambda r: r['date'])
    json.dump(allrows, open(path, 'w'))
    n = len(allrows); odds = sum(1 for r in allrows if r['mlH'] and r['mlA']); sp = sum(1 for r in allrows if r['spH'] is not None)
    print(season, 'games', n, 'with moneyline', odds, 'with spread', sp)

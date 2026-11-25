import sys, json
snap_path, page = sys.argv[1], sys.argv[2]
snap = json.load(open(snap_path))
games = [u for u in snap['data'] if '/scoreboard?' in u]
if len(snap['data']) < 20 or not games:
    sys.exit('Snapshot looks empty, keeping the previous data.')
raw = json.dumps(snap, separators=(',', ':')).replace('</', '<\\/')
s = open(page).read()
s = '\n'.join(l for l in s.split('\n') if 'window.__CE_SNAP=' not in l)
anchor = "<script>\n(() => {"
assert anchor in s
s = s.replace(anchor, "<script>window.__CE_SNAP=" + raw + ";</script>\n" + anchor, 1)
open(page, 'w').write(s)
print('embedded', len(snap['data']), 'responses')

# How real gearboxes space their gears: every stock gearbox in the game and the installed car packs.
# Read-only. Position x = 0 at first gear, 1 at top. y = 1 at first gear, 0 at top, in log(ratio):
# even (geometric) spacing is y = 1 - x. Fits y = (1 - x)^p: p above 1 means bigger steps low down.
import glob, json, math, os, sqlite3, statistics as st, sys
game = sys.argv[1]
p = game + "/GameFiles/Anthem_1.0.0.64_x64__8wekyb3d8bbwe/Mount/mediaoverride/Stripped/gamedbRC.slt"
db = sqlite3.connect("file:" + p + "?mode=ro&immutable=1", uri=True)
cols = ["NumGears"] + [f"GearRatio{i}" for i in range(1, 9)]
rows = db.execute(f"SELECT {','.join(cols)} FROM List_UpgradeDrivetrainTransmission WHERE IsStock=1").fetchall()
base = len(rows)
for f in glob.glob(os.path.join(game, "mods", "*", "database.json")):
    found = []
    def walk(o):
        if isinstance(o, dict):
            if "NumGears" in o and "GearRatio1" in o and o.get("IsStock") == 1: found.append(o)
            for v in o.values(): walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(json.load(open(f, encoding="utf8")))
    rows += [tuple(r.get(c) for c in cols) for r in found]
print(f"{base} base game + {len(rows) - base} from car packs = {len(rows)} stock gearboxes")

def fit(y_by_x):
    # least squares on p over a grid
    best, err = 1.0, 1e9
    for k in range(50, 300):
        q = k / 100
        e = sum((y - (1 - x) ** q) ** 2 for x, y in y_by_x)
        if e < err: best, err = q, e
    return best

by = {}
for r in rows:
    if not all(isinstance(v, (int, float)) for v in r[:2]): continue
    n = int(r[0]) - 1
    gears = r[1:n + 1]
    if n < 3 or any(not isinstance(g, (int, float)) or g <= 0 for g in gears): continue
    if any(gears[i] <= gears[i + 1] for i in range(n - 1)): continue
    by.setdefault(n, []).append(gears)

print("\nforward gears | cars | span (first/top) | median step between each pair of gears | fitted p")
allp = []
for n in sorted(by):
    g = by[n]
    spans = [x[0] / x[-1] for x in g]
    steps = [st.median(x[i] / x[i + 1] for x in g) for i in range(n - 1)]
    ps = []
    for x in g:
        lo = math.log(x[0] / x[-1])
        ps.append(fit([(i / (n - 1), math.log(x[i] / x[-1]) / lo) for i in range(n)]))
    allp += ps
    print(f"{n:13} | {len(g):4} | {st.median(spans):5.2f} ({min(spans):.2f}-{max(spans):.2f}) | " + " ".join(f"{s:.2f}" for s in steps) + f" | {st.median(ps):.2f}")
print(f"\nall {len(allp)}: median p {st.median(allp):.2f}, quartiles {st.quantiles(allp, n=4)[0]:.2f} to {st.quantiles(allp, n=4)[2]:.2f}")

# How far off is each spacing, on the real gearboxes? (mean absolute error in gear ratio, %)
for label, q in (("even (what the mod does now)", 1.0), ("fitted", st.median(allp))):
    errs = []
    for n, g in by.items():
        for x in g:
            lo = math.log(x[0] / x[-1])
            for i in range(1, n - 1):
                model = x[-1] * math.exp(lo * (1 - i / (n - 1)) ** q)
                errs.append(abs(model - x[i]) / x[i])
    print(f"{label:30} p={q:.2f}: gears between first and top are off by {100 * st.mean(errs):.1f}% on average")

# And the car under test, at every gear count, both ways
first, top = 3.65, 0.76
q = st.median(allp)
print(f"\nThe SRT4 (first {first}, top {top}):")
for n in (3, 5, 6, 8):
    e = [round(first * (top / first) ** (i / (n - 1)), 2) for i in range(n)]
    pr = [round(top * math.exp(math.log(first / top) * (1 - i / (n - 1)) ** q), 2) for i in range(n)]
    print(f"  {n} even:        {e}\n  {n} progressive: {pr}")
print("  its real 5-speed:", [r for r in rows if r[1] == 3.65][:1] or "from its pack")

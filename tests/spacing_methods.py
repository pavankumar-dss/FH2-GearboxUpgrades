# Which way of spacing new gears best matches real gearboxes? A fair test on the 478 stock gearboxes of
# the game and the ZS car packs: take a real N-speed, remove one of its middle gears, and let each method
# rebuild the N-speed from what's left. Error = how far its gears land from the real ones.
#
#   global:  one curve for every car: log(ratio) from first to top falls off as (1 - x)^1.38 (what the mod does now)
#   jante:   Jante's corrected geometric series: each step is m times the one above it. m is this car's own,
#            from its own steps (fallback 1.1, the textbook value); first and top fixed.
#   shape:   the car's own curve: its gears' log(ratio) against position from first to top, followed
#            smoothly (monotone cubic) at the new positions. With the same count it's the car's gearbox exactly.
import glob, json, math, os, sqlite3, statistics as st, sys

game = sys.argv[1]
p = game + "/GameFiles/Anthem_1.0.0.64_x64__8wekyb3d8bbwe/Mount/mediaoverride/Stripped/gamedbRC.slt"
db = sqlite3.connect("file:" + p + "?mode=ro&immutable=1", uri=True)
cols = ["NumGears"] + [f"GearRatio{i}" for i in range(1, 9)]
rows = db.execute(f"SELECT {','.join(cols)} FROM List_UpgradeDrivetrainTransmission WHERE IsStock=1").fetchall()
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
boxes = []
for r in rows:
    if not isinstance(r[0], (int, float)): continue
    n = int(r[0]) - 1
    g = r[1:n + 1]
    if n >= 3 and all(isinstance(x, (int, float)) and x > 0 for x in g) and all(g[i] > g[i + 1] for i in range(n - 1)):
        boxes.append(list(g))


def global_curve(first, top, n, p=1.38):
    return [top * (first / top) ** ((1 - i / (n - 1)) ** p) for i in range(n)]


def own_m(gears):
    """m from the car's own steps: log(step) is linear in its place from the top, slope log(m)."""
    steps = [gears[i] / gears[i + 1] for i in range(len(gears) - 1)][::-1]  # from the top down
    if len(steps) < 2: return 1.1
    xs = list(range(len(steps))); ys = [math.log(s) for s in steps]
    mx, my = st.mean(xs), st.mean(ys)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    return min(max(math.exp(slope), 0.9), 1.4)


def jante(first, top, n, m):
    # steps from the top: K, K m, K m^2 ... ; their product is first/top: K^(n-1) m^((n-1)(n-2)/2)
    k = math.exp((math.log(first / top) - math.log(m) * (n - 1) * (n - 2) / 2) / (n - 1))
    out = [top]
    for j in range(n - 1):
        out.append(out[-1] * k * m ** j)
    return out[::-1]


def pchip(xs, ys, x):
    """Monotone cubic (Fritsch-Carlson) through (xs, ys), at x."""
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0: m[i] = 0.0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    for i in range(n - 1):
        if xs[i] <= x <= xs[i + 1]:
            t = (x - xs[i]) / h[i]
            h00, h10, h01, h11 = 2*t**3 - 3*t**2 + 1, t**3 - 2*t**2 + t, -2*t**3 + 3*t**2, t**3 - t**2
            return h00 * ys[i] + h10 * h[i] * m[i] + h01 * ys[i + 1] + h11 * h[i] * m[i + 1]
    return ys[-1] if x > xs[-1] else ys[0]


def shape(gears, n):
    k = len(gears)
    xs = [i / (k - 1) for i in range(k)]
    ys = [math.log(g) for g in gears]
    return [math.exp(pchip(xs, ys, i / (n - 1))) for i in range(n)]


methods = {
    "global (now)": lambda g, n: global_curve(g[0], g[-1], n),
    "Jante, m = 1.1": lambda g, n: jante(g[0], g[-1], n, 1.1),
    "Jante, own m": lambda g, n: jante(g[0], g[-1], n, own_m(g)),
    "own shape": lambda g, n: shape(g, n),
}
errs = {k: [] for k in methods}
worst = {k: [] for k in methods}
for real in boxes:
    n = len(real)
    if n < 5: continue
    for drop in range(1, n - 1):
        left = real[:drop] + real[drop + 1:]
        for name, f in methods.items():
            guess = f(left, n)
            e = [abs(guess[i] - real[i]) / real[i] for i in range(1, n - 1)]
            errs[name] += e
            worst[name].append(max(e))
print(f"{len(boxes)} gearboxes; rebuilding each N-speed (N >= 5) after removing one middle gear, every way")
print(f"{'method':18} {'mean error':>10} {'median':>8} {'90th pct':>9} {'worst gear per test, median':>28}")
for name in methods:
    e = sorted(errs[name]); w = sorted(worst[name])
    print(f"{name:18} {100*st.mean(e):9.1f}% {100*st.median(e):7.1f}% {100*e[int(.9*len(e))]:8.1f}% {100*st.median(w):27.1f}%")
ms = [own_m(g) for g in boxes]
print(f"\nown m across the gearboxes: median {st.median(ms):.3f}, quartiles {st.quantiles(ms, n=4)[0]:.3f} to {st.quantiles(ms, n=4)[2]:.3f} (the textbook value is 1.1)")

srt4 = [3.65, 2.05, 1.37, 0.97, 0.76]
print(f"\nThe SRT4's real 5-speed {srt4}, own m {own_m(srt4):.3f}:")
for n in (3, 4, 6, 7, 8):
    print(f"  {n}-speed:")
    for name, f in methods.items():
        print(f"    {name:16} " + " ".join(f"{x:.2f}" for x in f(srt4, n)))

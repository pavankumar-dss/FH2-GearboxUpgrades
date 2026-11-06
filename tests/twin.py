"""The spacing formula, exactly as src/gearbox_upgrades.c does it, for the tests and the in-game kit."""
import math

SPACING = 1.38
QUIRKS = 0.5


def pchip(xs, ys, x):
    n = len(xs)
    if n < 2:
        return ys[0] if n else 0.0
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0.0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    for i in range(n - 1):
        if xs[i] <= x <= xs[i + 1]:
            t = (x - xs[i]) / h[i]
            return ((2 * t**3 - 3 * t**2 + 1) * ys[i] + (t**3 - 2 * t**2 + t) * h[i] * m[i] + (-2 * t**3 + 3 * t**2) * ys[i + 1]
                    + (t**3 - t**2) * h[i] * m[i + 1])
    return ys[-1] if x > xs[-1] else ys[0]


def spaced(stock, gears):
    """The forward ratios of a `gears`-speed made from a stock gearbox (its forward ratios, first first)."""
    first, top = stock[0], stock[-1]
    if gears == 1:
        return [math.sqrt(first * top)]
    k = len(stock)
    span = math.log(first / top)
    xs = [i / (k - 1) for i in range(k)]
    quirk = [math.log(stock[i] / top) / span - (1 - xs[i]) ** SPACING for i in range(k)]
    out = []
    for g in range(1, gears + 1):
        if g == 1:
            out.append(first)
        elif g == gears:
            out.append(top)
        else:
            x = (g - 1) / (gears - 1)
            out.append(top * math.exp(span * ((1 - x) ** SPACING + QUIRKS * pchip(xs, quirk, x))))
    return out

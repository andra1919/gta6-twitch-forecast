import json, math, sys, itertools
from datetime import timedelta
sys.path.insert(0, sys.argv[1])
import main as M

case0 = json.load(open(sys.argv[2]))
comps = case0["comparables"]
Z = [-1.645, -0.674, 0, 0.674, 1.645]


def pinball(y, qs):
    s = 0
    for tau, q in zip(M.LEVELS, qs):
        d = math.log(max(y, 1)) - math.log(q)
        s += 2 * max(tau * d, (tau - 1) * d)
    return s


def targets(min_h1=20000, rolling_only=False):
    out = []
    for c in comps:
        u = (c.get("unlock") or "").lower()
        if "target-history" in u:
            continue
        ds = M.parse_ts(c["day_start"])
        m = M.hourly_map(c["hourly"])
        v1 = m.get(ds)
        if not v1 or v1 < min_h1:
            continue
        if rolling_only and M.comparable_weight(c, M.PARAMS) <= 1.0 + 1e-9 * 0 and "midnight local" not in u:
            continue
        hist = [{"from": r["from"], "viewers": r["viewers"]} for r in c["hourly"] if M.parse_ts(r["from"]) < ds]
        ans = {h: m.get(ds + timedelta(hours=h - 1)) for h in range(2, 25)}
        case = {"day_start": c["day_start"], "known": [{"hour": 1, "viewers": v1}],
                "history_hourly": hist, "comparables": comps}
        out.append((c["name"], case, v1, ans, "midnight local" in u))
    return out


def score(p, T, base=False):
    tot = n = 0
    per = {}
    for name, case, v1, ans, _ in T:
        if base:
            rows = {h: [v1 * math.exp(z * 0.15 * math.sqrt(h - 1)) for z in Z] for h in range(2, 25)}
        else:
            f = M.forecast_case(case, p, exclude_name=name)
            rows = {r["hour"]: r["q"] for r in f["hours"]}
        s = k = 0
        for h, y in ans.items():
            if y is None:
                continue
            s += pinball(y, rows[h]); k += 5
        per[name] = s / k
        tot += s; n += k
    return tot / n, per


if __name__ == "__main__":
    T = targets()
    TR = [t for t in T if t[4]]
    print("targets", len(T), "rolling", len(TR))
    for lab, TT in (("all", T), ("rolling", TR)):
        print(lab, "baseline %.4f" % score(None, TT, True)[0], "model %.4f" % score(M.PARAMS, TT)[0])
    if len(sys.argv) > 3:
        best = None
        grid = dict(w_rolling=[1, 3, 6], feat_bw=[0.3, 0.6, 1.5, 100], sd0=[0.05, 0.12, 0.2], sd_slope=[0.0, 0.04, 0.08], w_simul=[0.1, 0.4, 1])
        keys = list(grid)
        for vals in itertools.product(*grid.values()):
            p = dict(M.PARAMS); p.update(zip(keys, vals))
            a = score(p, T)[0]; r = score(p, TR)[0]
            obj = 0.5 * a + 0.5 * r
            if best is None or obj < best[0]:
                best = (obj, a, r, dict(zip(keys, vals)))
        print("best", best)

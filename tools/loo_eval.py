"""Leave-one-out check of main.py on the comparables' own release days.

Each past launch whose hour 1 has at least 20k viewers becomes a pseudo-case: its hour 1 is the print,
the hours before it are the history, and the other launches are the comparables. Scored with the bounty's
log-scale pinball loss, against the house persistence baseline on the same pseudo-cases.

Usage: python3 tools/loo_eval.py <case.in> [key=value ...]   (key=value overrides a SETTINGS entry)
"""
import json
import math
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import main  # noqa: E402


def pinball(y, row):
    y = max(y, 1.0)
    total = 0.0
    for tau, q in zip(main.QUANTILE_LEVELS, row):
        d = math.log(y) - math.log(q)
        total += 2.0 * max(tau * d, (tau - 1.0) * d)
    return total


def pseudo_cases(case):
    for launch in case["comparables"]:
        if "target-history" in (launch.get("unlock") or "").lower():
            continue
        start = main.to_utc(launch["day_start"])
        series = main.series_by_hour(launch["hourly"])
        first = series.get(start)
        if not first or first < 20000:
            continue
        truth = {h: series[start + timedelta(hours=h - 1)] for h in main.HOURS
                 if start + timedelta(hours=h - 1) in series}
        hist = [r for r in launch["hourly"] if main.to_utc(r["from"]) <= start]
        yield launch["name"], {
            "day_start": launch["day_start"],
            "known": [{"hour": 1, "viewers": first}],
            "history_hourly": hist,
            "comparables": case["comparables"],
        }, truth


def score(case, cfg):
    model = base = n = 0.0
    for name, pc, truth in pseudo_cases(case):
        fc = {r["hour"]: r["q"] for r in main.forecast(pc, cfg, skip=name)["hours"]}
        bl = {r["hour"]: r["q"] for r in main.baseline(pc)["hours"]}
        for h, y in truth.items():
            model += pinball(y, fc[h])
            base += pinball(y, bl[h])
            n += 5
    return model / n, base / n


if __name__ == "__main__":
    case = json.loads(Path(sys.argv[1]).read_text())
    cfg = dict(main.SETTINGS)
    for kv in sys.argv[2:]:
        k, v = kv.split("=")
        cfg[k] = float(v)
    m, b = score(case, cfg)
    print(f"model {m:.4f}  baseline {b:.4f}")

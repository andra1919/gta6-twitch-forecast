"""Forecast Grand Theft Auto VI's launch-day Twitch viewers, hours 2 to 24.

Entry for make.fun's bounty gta6-twitch-ccu-forecast-01. Python 3.13, standard library only, deterministic.

Method (analogue forecasting):
  Every case carries the release-day hourly curves of past big launches (`comparables`). For each usable
  launch c we take its shape after hour 1 on the log scale, s_c(h) = ln V_c(h) - ln V_c(1).
  Each launch is weighted by
    * how it unlocked (rolling midnight-local console launches look most like GTA VI; a single global
      unlock or an early-access-contaminated day looks less like it), and
    * how close its run-up into hour 1 is to the case's own (hour 1 against the few hours before it),
      through a Gaussian kernel.
  Hour h's forecast is a weighted mixture of normal kernels in log space, one per launch, centred on
  s_c(h) with a width that grows with h. The five quantiles are found by bisection on the mixture CDF
  and multiplied by the case's hour-1 print.

Usage: python3 main.py   (reads every *.in from $MAKEFUN_INPUT_DIR or /input, writes <id>.out to
$MAKEFUN_OUTPUT_DIR or /output).
"""

import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

QUANTILE_LEVELS = (0.05, 0.25, 0.5, 0.75, 0.95)
HOURS = range(2, 25)

# Model settings, chosen with tools/loo_eval.py (leave-one-out over the comparables' own release days).
SETTINGS = {
    "min_first_hour": 5000.0,   # launches with a smaller hour 1 are too noisy to learn a shape from
    "min_hours": 18,            # a launch needs at least this many of hours 2..24 present
    "rolling_boost": 1.0,       # multiplier for rolling midnight-local unlocks
    "global_unlock": 0.1,       # multiplier for a single simultaneous global unlock
    "early_access": 0.8,        # multiplier for early-access-contaminated launches
    "weak_tier": 0.3,           # multiplier for launches the case marks as weak analogues
    "runup_bandwidth": 0.4,     # kernel width on the run-up feature, log units
    # Leave-one-out on 2026-11-17: mean log pinball 0.268 vs 0.321 for the house baseline.
    "width_base": 0.12,         # kernel width at hour 2, log units
    "width_growth": 0.04,       # extra kernel width per sqrt(hours after hour 1)
}

Z_BASELINE = (-1.645, -0.674, 0.0, 0.674, 1.645)


def to_utc(stamp):
    """Parse an ISO 8601 timestamp (with Z or an offset) into an aware UTC datetime."""
    return datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(timezone.utc)


def series_by_hour(rows):
    """{hour start: viewers} from rows of {from, viewers}; rows without a count are skipped."""
    out = {}
    for row in rows or []:
        value = row.get("viewers")
        if value is None or row.get("from") is None:
            continue
        out[to_utc(row["from"])] = float(value)
    return out


def runup(series, start, first_hour):
    """ln(hour 1 / mean of the three hours before the day starts); None when they are missing."""
    before = []
    for k in (1, 2, 3):
        v = series.get(start - timedelta(hours=k))
        if v is not None and v > 0:
            before.append(v)
    if not before or first_hour <= 0:
        return None
    return math.log(first_hour / (sum(before) / len(before)))


def unlock_weight(launch, cfg):
    """Prior weight of a past launch from the words its record uses about its unlock and tier."""
    words = " ".join([launch.get("unlock") or "", launch.get("name") or ""]).lower()
    weight = 1.0
    if "tier: early-access" in words:
        weight *= cfg["early_access"]
    elif "tier: weak" in words:
        weight *= cfg["weak_tier"]
    is_global = any(p in words for p in ("simultaneous", "single global", "single time"))
    if is_global and "rolling" not in words:
        weight *= cfg["global_unlock"]
    elif "rolling" in words or "midnight local" in words:
        weight *= cfg["rolling_boost"]
    return weight


def launch_shapes(comparables, cfg, skip=None):
    """Usable past launches: their prior weight, run-up feature and log shape after hour 1."""
    shapes = []
    for launch in comparables or []:
        name = launch.get("name")
        if skip is not None and name == skip:
            continue
        if "tier: target-history" in (launch.get("unlock") or "").lower():
            continue  # the target's own pre-release category: not a launch day
        try:
            start = to_utc(launch["day_start"])
        except (KeyError, ValueError, AttributeError):
            continue
        series = series_by_hour(launch.get("hourly"))
        first = series.get(start)
        if first is None or first < cfg["min_first_hour"]:
            continue
        shape = {}
        for h in HOURS:
            v = series.get(start + timedelta(hours=h - 1))
            if v is not None and v > 0:
                shape[h] = math.log(v / first)
        if len(shape) < cfg["min_hours"]:
            continue
        shapes.append({
            "name": name,
            "prior": unlock_weight(launch, cfg),
            "runup": runup(series, start, first),
            "shape": shape,
        })
    return shapes


def normal_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def mixture_quantile(parts, level):
    """Quantile of sum_i w_i N(mu_i, sd_i) at `level`, by 80 bisection steps (deterministic)."""
    total = sum(w for w, _, _ in parts)
    low = min(mu - 8.0 * sd for _, mu, sd in parts)
    high = max(mu + 8.0 * sd for _, mu, sd in parts)
    for _ in range(80):
        mid = 0.5 * (low + high)
        mass = sum(w * normal_cdf((mid - mu) / sd) for w, mu, sd in parts) / total
        if mass < level:
            low = mid
        else:
            high = mid
    return 0.5 * (low + high)


def first_hour_print(case):
    for row in case.get("known") or []:
        if row.get("hour") == 1 and row.get("viewers") is not None:
            return max(float(row["viewers"]), 1.0)
    return 1.0


def monotone_row(first, logs):
    """Turn log offsets into a valid quantile row: positive, capped, non-decreasing, 2 decimals."""
    row, floor = [], 0.0
    for x in logs:
        v = min(max(first * math.exp(x), 0.01), 1e9)
        v = round(max(v, floor), 2)
        row.append(v)
        floor = v
    return row


def forecast(case, cfg=SETTINGS, skip=None):
    """The forecast object {"hours": [...]} for one case."""
    first = first_hour_print(case)
    start = to_utc(case["day_start"])
    own = series_by_hour(case.get("history_hourly"))
    own.setdefault(start, first)
    own_runup = runup(own, start, first)

    shapes = launch_shapes(case.get("comparables"), cfg, skip)
    weights = []
    for s in shapes:
        w = s["prior"]
        if own_runup is not None and s["runup"] is not None:
            gap = (own_runup - s["runup"]) / cfg["runup_bandwidth"]
            w *= math.exp(-0.5 * gap * gap)
        weights.append(w)
    if shapes and sum(weights) < 1e-12:
        weights = [s["prior"] for s in shapes]  # run-up matched nothing: fall back to the priors

    hours = []
    for h in HOURS:
        width = cfg["width_base"] + cfg["width_growth"] * math.sqrt(h - 1)
        parts = [(w, s["shape"][h], width) for s, w in zip(shapes, weights) if w > 0 and h in s["shape"]]
        if not parts:
            parts = [(1.0, 0.0, 0.15 * math.sqrt(h - 1))]
        logs = [mixture_quantile(parts, level) for level in QUANTILE_LEVELS]
        hours.append({"hour": h, "q": monotone_row(first, logs)})
    return {"hours": hours}


def baseline(case):
    """The house persistence forecast, used only if the model itself fails on a case."""
    first = first_hour_print(case)
    return {"hours": [{"hour": h, "q": [round(first * math.exp(z * 0.15 * math.sqrt(h - 1)), 2)
                                         for z in Z_BASELINE]} for h in HOURS]}


def main():
    in_dir = Path(os.environ.get("MAKEFUN_INPUT_DIR") or "/input")
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output")
    out_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted(in_dir.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        try:
            result = forecast(case)
        except Exception as err:  # a crash would make the case invalid; persistence is better
            print(f"{path.stem}: model failed ({err!r}), writing baseline", file=sys.stderr)
            result = baseline(case)
        (out_dir / f"{path.stem}.out").write_text(json.dumps(result, separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    main()

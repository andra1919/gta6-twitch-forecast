# gta6-twitch-forecast

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/andra1919/gta6-twitch-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/andra1919/gta6-twitch-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

Forecasts how many people watch Grand Theft Auto VI on Twitch in each hour (2 to 24) of its release day,
2026-11-19 UTC, as five quantiles per hour, from the first hour's count. Plain Python 3.13, standard library
only, deterministic, well under a second per case.

How it works: every past big launch in the case's `comparables` gives its release-day curve on the log scale
relative to its own hour 1. Launches are weighted by how they unlocked (rolling midnight-local console launches,
like GTA VI's, count most; single global unlocks and early-access days less) and by how closely their run-up
into hour 1 matches the case's. Each hour's forecast is a weighted mixture of log-normal kernels, one per launch,
read off at 5/25/50/75/95% and scaled by the hour-1 print.

Leave-one-out on the comparables' own release days (`tools/loo_eval.py`): mean log pinball loss 0.268, against
0.321 for the house persistence baseline on the same pseudo-cases.

## Run it

```sh
MAKEFUN_INPUT_DIR=./input MAKEFUN_OUTPUT_DIR=./out python3 main.py
```

---

<sub>Entered on [make.fun](https://make.fun/?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01) · AI agents build software for cash rewards</sub>

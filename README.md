# gta6-twitch-forecast

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/andra1919/gta6-twitch-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/andra1919/gta6-twitch-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

Forecasts Grand Theft Auto VI's launch-day Twitch viewers (the "Grand Theft Auto VI" category, hours 2 to 24 of
2026-11-19 UTC) as five quantiles per hour, from the first hour's count. It is an analogue model in plain Python
(standard library only, deterministic): each past big launch in the case's `comparables` contributes its release-day
curve relative to its own hour 1, weighted by its tier, its unlock style (rolling midnight-local vs simultaneous) and
how closely its run-up into hour 1 matches the case's. The quantiles are read off a weighted mixture of log-normal
components and scaled by the hour-1 print.

Leave-one-out over the comparables' own release days (27 launches with an hour 1 of 20k+ viewers), the mean log-scale
pinball loss is 0.274, against 0.321 for the house persistence baseline. `tools/eval_loo.py` reproduces it.

## Run it

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

---

<sub>Entered on [make.fun](https://make.fun/?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01) · AI agents build software for cash rewards</sub>

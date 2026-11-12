# roblox-up-and-coming-forecast-01 — Vel entry
# Empirical rank-transition model: builds P(next_pos | cur_pos) from the chart history
# (recency-decayed), computes each game's expected next position, then per place spreads
# mass over the games closest to that place. Offline, stdlib only, Python 3.
import json, os, math
from collections import defaultdict

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
DECAY = 0.95   # recency weight per older read
SHARP = 0.5    # exp distance falloff
NCAND = 15     # games named per place
SHARE = 0.95   # named mass per place (rest spread by grader)
CAP = 25       # games considered
STAY_BOOST = 2.0  # extra diagonal weight: hourly window reads reward stay
VERSION = "v1.3"

def chart(line):
    return [g["universe_id"] for g in sorted(line["up_and_coming"], key=lambda g: g["rank"])]

def build(train):
    trans = defaultdict(lambda: defaultdict(float))
    n = len(train)
    for i in range(n - 1):
        w = DECAY ** (n - 2 - i)
        c1, c2 = chart(train[i]), chart(train[i + 1])
        pos2 = {u: k + 1 for k, u in enumerate(c2)}
        for k, u in enumerate(c1[:20]):
            trans[k + 1][pos2.get(u, 0)] += w
            trans[k + 1][k + 1] += w * STAY_BOOST
    P = {p: {q: v / sum(row.values()) for q, v in row.items()} for p, row in trans.items()}
    last = train[-1]
    cl = chart(last)
    pos = {u: k + 1 for k, u in enumerate(cl)}
    exp = {}
    for u in cl[:CAP]:
        p = pos.get(u, 0)
        row = P.get(p) or {p: 1.0}
        exp[u] = sum(q * pr for q, pr in row.items() if q > 0) or p
    games = cl[:CAP]
    probabilities = []
    for k in range(1, 11):
        cands = sorted(games, key=lambda u: abs(exp[u] - k))[:NCAND]
        ws = [(u, math.exp(-SHARP * abs(exp[u] - k))) for u in cands]
        tot = sum(w for _, w in ws) or 1.0
        for u, w in ws:
            probabilities.append({"universe_id": u, "place": k, "p": round(SHARE * w / tot, 6)})
    top10 = sorted(games, key=lambda u: exp[u])[:10]
    return probabilities, top10

def main():
    lines = [json.loads(l) for l in open(os.path.join(INPUT_DIR, "history.ndjson")) if l.strip()]
    task = json.load(open(os.path.join(INPUT_DIR, "task.json")))
    probabilities, top10 = build(lines)
    pool = [u for u in chart(lines[-1]) if u not in top10]
    while len(top10) < task["places"] and pool:
        top10.append(pool.pop(0))
    out = {"probabilities": probabilities, "top10": top10}
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, "forecast.json"), "w") as f:
        json.dump(out, f)

main()

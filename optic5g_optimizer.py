import pandas as pd
import numpy as np
from pulp import LpProblem, LpVariable, LpMinimize, lpSum, LpBinary

layout = pd.read_csv("data/hex_layout_baseline.csv")
towers = pd.read_csv("data/manila_towers_xy.csv")

# Greedy: filter nearest candidate sites to real towers
layout["nearest_dist"] = layout.apply(
    lambda r: np.min(np.sqrt((r.x - towers.x)**2 + (r.y - towers.y)**2)), axis=1
)
candidates = layout.nsmallest(20, "nearest_dist")

# ILP: select minimal subset covering all towers
prob = LpProblem("OPTIC5G_ILP", LpMinimize)
x_vars = [LpVariable(f"x{i}", cat=LpBinary) for i in range(len(candidates))]
coverage = np.zeros((len(towers), len(candidates)))

for t, tower in towers.iterrows():
    for i, cand in candidates.iterrows():
        if np.sqrt((tower.x - cand.x)**2 + (tower.y - cand.y)**2) <= 200:
            coverage[t, i] = 1

prob += lpSum(x_vars)  # objective: minimize active sites
for t in range(len(towers)):
    prob += lpSum(coverage[t, i] * x_vars[i] for i in range(len(candidates))) >= 1

prob.solve()

active = [int(v.value()) for v in x_vars]
candidates["active"] = active
candidates.to_csv("data/optic5g_activation.csv", index=False)
print("✅ Saved classical optimization result: optic5g_activation.csv")

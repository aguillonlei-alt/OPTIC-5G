import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from math import sqrt, exp
import random
import os

from qiskit_optimization import QuadraticProgram

# ==========================================
# CONFIGURATION
# ==========================================
MASK_FILENAME = "optimized_mask.txt"
FORCE_RERUN = True  # <--- I SET THIS TO TRUE SO IT RE-CALCULATES AUTOMATICALLY

print("\n=== OPTIC-5G: HYBRID OPTIMIZATION (TUNED FOR HIGHER SINR) ====")

# ==========================================
# PHASE 1: DATA LOADING & GREEDY SELECTION
# ==========================================
try:
    df = pd.read_csv("data/real_towers_ns3.csv")
    print(f"--> Loaded {len(df)} total towers.")
except FileNotFoundError:
    print("❌ Error: 'data/real_towers_ns3.csv' not found.")
    exit()

# Manual Blacklist
MANUAL_BLACKLIST = [2, 185] 

all_towers = df.to_dict('records')
valid_towers = []

for idx, t in enumerate(all_towers):
    t['original_index'] = int(idx)
    if 'txpower_dbm' not in t: t['txpower_dbm'] = 46.0
    if t['original_index'] in MANUAL_BLACKLIST: continue 
    valid_towers.append(t)

# Density Calculation
DENSITY_RADIUS = 1000.0
for t in valid_towers:
    neighbor_count = 0
    for other in valid_towers:
        if t == other: continue
        dist = sqrt((t['x_m'] - other['x_m'])**2 + (t['y_m'] - other['y_m'])**2)
        if dist < DENSITY_RADIUS:
            neighbor_count += 1
    t['density_score'] = neighbor_count

# Greedy Filtering
# INCREASED LIMIT slightly to give solver more options
CANDIDATE_LIMIT = 28  
MIN_SEPARATION = 300.0 

sorted_towers = sorted(valid_towers, key=lambda x: x['density_score'], reverse=True)
candidates = []
candidate_indices = []

print(f"--> Running Greedy Selection for {CANDIDATE_LIMIT} towers...")

for tower in sorted_towers:
    if len(candidates) >= CANDIDATE_LIMIT:
        break
    is_far_enough = True
    for selected in candidates:
        dist = sqrt((tower['x_m'] - selected['x_m'])**2 + (tower['y_m'] - selected['y_m'])**2)
        if dist < MIN_SEPARATION:
            is_far_enough = False
            break
    if is_far_enough:
        candidates.append(tower)
        candidate_indices.append(tower['original_index'])

print(f"--> Selection Complete: {len(candidates)} Candidates Chosen.")

# ==========================================
# PHASE 2: QUBO FORMULATION (TUNED)
# ==========================================
print("\n=== PHASE 2: QUBO FORMULATION ===")

qp = QuadraticProgram()
for i in range(len(candidates)):
    qp.binary_var(name=f"t_{i}")

linear_terms = {}
quadratic_terms = {}

# --- TUNING PARAMETERS (THE FIX) ---
# OLD: Reward=250, Penalty=200 --> Resulted in only 13 towers (Too sparse)
# NEW: Reward=1800, Penalty=600 --> Should target ~18-22 towers (Sweet Spot)
COVERAGE_REWARD = 1800.0 
INTERFERENCE_THRESHOLD = 1000.0 # Only penalize if VERY close
PENALTY_WEIGHT = 600.0

# Linear (Rewards)
for i in range(len(candidates)):
    # Reward is high, cost (TxPower) is low. Net positive to turn ON.
    cost = candidates[i]['txpower_dbm'] - COVERAGE_REWARD
    linear_terms[f"t_{i}"] = cost

# Quadratic (Penalties)
for i in range(len(candidates)):
    for j in range(i + 1, len(candidates)):
        t1 = candidates[i]
        t2 = candidates[j]
        dist = sqrt((t1['x_m'] - t2['x_m'])**2 + (t1['y_m'] - t2['y_m'])**2)
        
        if dist < INTERFERENCE_THRESHOLD:
            quadratic_terms[(f"t_{i}", f"t_{j}")] = PENALTY_WEIGHT

qp.minimize(linear=linear_terms, quadratic=quadratic_terms)

# ==========================================
# PHASE 3: SOLVER (Simulated Annealing)
# ==========================================
print("\n=== PHASE 3: SOLVER (Simulated Annealing) ===")

def get_qubo_energy(solution_vec):
    energy = 0
    for i in range(len(solution_vec)):
        if solution_vec[i] == 1:
            energy += linear_terms.get(f"t_{i}", 0)
    for (key, weight) in quadratic_terms.items():
        i, j = int(key[0].split('_')[1]), int(key[1].split('_')[1])
        if solution_vec[i] == 1 and solution_vec[j] == 1:
            energy += weight
    return energy

iterations = 8000 # Increased iterations for better convergence
temperature = 150.0
cooling_rate = 0.99

current_solution = [random.randint(0, 1) for _ in range(len(candidates))]
current_energy = get_qubo_energy(current_solution)
best_solution = list(current_solution)
best_energy = current_energy

for k in range(iterations):
    idx = random.randint(0, len(candidates)-1)
    new_solution = list(current_solution)
    new_solution[idx] = 1 - new_solution[idx] 
    
    new_energy = get_qubo_energy(new_solution)
    delta = new_energy - current_energy
    
    if delta < 0 or random.random() < exp(-delta / temperature):
        current_solution = new_solution
        current_energy = new_energy
        if current_energy < best_energy:
            best_energy = current_energy
            best_solution = list(current_solution)
    temperature *= cooling_rate

# ==========================================
# PHASE 4: OUTPUT
# ==========================================
final_mask_list = ['0'] * len(df)
candidate_real_ids = [c['original_index'] for c in candidates]

active_count = 0
for i, val in enumerate(best_solution):
    original_idx = candidate_real_ids[i]
    if val == 1:
        final_mask_list[original_idx] = '1'
        active_count += 1

final_mask_str = "".join(final_mask_list)

with open(MASK_FILENAME, "w") as f:
    f.write(final_mask_str)

print(f"\n✅ GENERATED NEW TUNED MASK ({active_count} Active):")
print(f"Goal: Should be roughly 18-24 towers for balanced SINR.")
print(f"Mask: {final_mask_str}")
print(f"\n🚀 TO RUN SIMULATION:")
print(f"./ns3 run 'scratch/manila_5g --mask={final_mask_str}'")

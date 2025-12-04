import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from math import sqrt
from sklearn.cluster import KMeans # <--- NEW: Machine Learning for Coverage

# Qiskit Imports
from qiskit.circuit.library import TwoLocal
from qiskit_algorithms import SamplingVQE
from qiskit_algorithms.optimizers import COBYLA
from qiskit.primitives import StatevectorSampler
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.algorithms import MinimumEigenOptimizer

# ==========================================
# PHASE 1: CLASSICAL OPTIMIZATION (K-MEANS CLUSTERING)
# ==========================================
print("\n=== PHASE 1: CLASSICAL PRE-PROCESSING (SPATIAL COVERAGE) ====")

# 1. Load Real Data
try:
    df = pd.read_csv("data/real_towers_ns3.csv")
    print(f"--> Loaded {len(df)} total towers from Manila dataset.")
except FileNotFoundError:
    print("Error: 'data/real_towers_ns3.csv' not found.")
    exit()

# 2. Coverage-Aware Selection (K-Means)
# Thesis Logic: "To ensure maximum coverage area with limited quantum resources (12 qubits),
# we employ K-Means Clustering to identify the 12 spatial centroids of the network."
CANDIDATE_LIMIT = 12

# Extract coordinates for clustering
coords = df[['x_m', 'y_m']].values

print(f"--> Running K-Means to find {CANDIDATE_LIMIT} optimal coverage zones...")
kmeans = KMeans(n_clusters=CANDIDATE_LIMIT, random_state=42, n_init=10)
kmeans.fit(coords)
centroids = kmeans.cluster_centers_

# Find the REAL tower closest to each Centroid
# (We can't move towers, so we pick the existing one closest to the ideal center)
candidates = []
candidate_indices = []

all_towers = df.to_dict('records')
for idx, t in enumerate(all_towers):
    t['original_index'] = idx
    if 'txpower_dbm' not in t: t['txpower_dbm'] = 46.0

for centroid in centroids:
    best_tower = None
    min_dist = float('inf')
    
    for tower in all_towers:
        # Calculate distance from tower to this cluster center
        dist = sqrt((tower['x_m'] - centroid[0])**2 + (tower['y_m'] - centroid[1])**2)
        
        # We pick the closest tower to the center
        if dist < min_dist:
            # Check if we already picked this tower (prevent duplicates)
            if tower['original_index'] not in candidate_indices:
                min_dist = dist
                best_tower = tower
    
    if best_tower:
        candidates.append(best_tower)
        candidate_indices.append(best_tower['original_index'])

# Identify rejected for plotting
rejected = [t for t in all_towers if t['original_index'] not in candidate_indices]

print(f"--> Spatial Optimization Results: {len(candidates)} Candidates Selected for Coverage.")

# --- VISUALIZATION 1: CLASSICAL FILTER MAP ---
print("--> Generating Classical Optimization Map...")
plt.figure(figsize=(10, 10))

# Plot Rejected (Gray)
rx = [r['x_m'] for r in rejected]
ry = [r['y_m'] for r in rejected]
plt.scatter(rx, ry, c='lightgray', label='Redundant Nodes', s=30, alpha=0.5)

# Plot Candidates (Blue)
cx = [c['x_m'] for c in candidates]
cy = [c['y_m'] for c in candidates]
plt.scatter(cx, cy, c='blue', label='Spatial Candidates (Top 12)', s=150, edgecolors='black', zorder=10)

# Plot Centroids (Red X) - To show the math
plt.scatter(centroids[:, 0], centroids[:, 1], c='red', marker='x', s=100, label='Ideal Centers (K-Means)')

plt.title(f"Spatial Coverage Optimization: 12 Candidates Covering {len(df)} Sites")
plt.xlabel("X Coordinates (m)")
plt.ylabel("Y Coordinates (m)")
plt.legend()
plt.grid(True, alpha=0.3)
plt.savefig("data/classical_filter_map.png")
print("Saved 'data/classical_filter_map.png'")


# ==========================================
# PHASE 2: QUBO FORMULATION
# ==========================================
print("\n=== PHASE 2: QUBO FORMULATION ===")

qp = QuadraticProgram()

# 1. Define Binary Variables
for i in range(len(candidates)):
    qp.binary_var(name=f"t_{i}")

# 2. Define Objective
linear_terms = {}
quadratic_terms = {}

# LINEAR (Energy - Reward)
# Thesis Goal: "Maintain Coverage".
# We give a HIGHER reward here because we pre-selected them for coverage.
# We want to keep as many ON as possible, unless they interfere violently.
COVERAGE_REWARD = 120.0 

for i in range(len(candidates)):
    cost = candidates[i]['txpower_dbm'] - COVERAGE_REWARD
    linear_terms[f"t_{i}"] = cost

# QUADRATIC (Interference Penalty)
# Thesis Goal: "High QoS" (Low Interference).
# We keep the penalty high. If two coverage nodes are close, one MUST go.
INTERFERENCE_THRESHOLD = 800.0 # Increased slightly to catch overlaps
PENALTY_WEIGHT = 600.0

for i in range(len(candidates)):
    for j in range(i + 1, len(candidates)):
        t1 = candidates[i]
        t2 = candidates[j]
        dist = sqrt((t1['x_m'] - t2['x_m'])**2 + (t1['y_m'] - t2['y_m'])**2)
        
        if dist < INTERFERENCE_THRESHOLD:
            quadratic_terms[(f"t_{i}", f"t_{j}")] = PENALTY_WEIGHT

qp.minimize(linear=linear_terms, quadratic=quadratic_terms)
print("--> Converted to QUBO format.")

# --- VISUALIZATION 2: QUBO HEATMAP ---
print("--> Generating QUBO Matrix Heatmap...")
matrix_size = len(candidates)
qubo_matrix = np.zeros((matrix_size, matrix_size))

for i in range(matrix_size):
    qubo_matrix[i, i] = linear_terms.get(f"t_{i}", 0)

for (key, weight) in quadratic_terms.items():
    i = int(key[0].split('_')[1])
    j = int(key[1].split('_')[1])
    qubo_matrix[i, j] = weight
    qubo_matrix[j, i] = weight 

plt.figure(figsize=(8, 6))
plt.imshow(qubo_matrix, cmap='coolwarm', interpolation='nearest')
plt.colorbar(label='Penalty Strength')
plt.title("QUBO Hamiltonian Matrix (Interference Visualization)")
plt.savefig("data/qubo_matrix_heatmap.png")
print("Saved 'data/qubo_matrix_heatmap.png'")


# ==========================================
# PHASE 3: QUANTUM CIRCUIT (ANSATZ)
# ==========================================
print("\n=== PHASE 3: QUANTUM CIRCUIT ===")
ansatz = TwoLocal(num_qubits=len(candidates), rotation_blocks='ry', entanglement_blocks='cz', entanglement='linear', reps=1)

print("--> Generating Circuit Diagram...")
ansatz.decompose().draw(output='mpl', filename="data/quantum_circuit_ansatz.png")
print("Saved 'data/quantum_circuit_ansatz.png'")


# ==========================================
# PHASE 4: EXECUTION (VQE)
# ==========================================
print("\n=== PHASE 4: RUNNING VQE OPTIMIZATION ===")
optimizer = COBYLA(maxiter=50)
sampler = StatevectorSampler()
vqe = SamplingVQE(sampler=sampler, ansatz=ansatz, optimizer=optimizer)
optimizer_vqe = MinimumEigenOptimizer(vqe)

result = optimizer_vqe.solve(qp)

print(f"\nOptimal State: {result.x}")
print(f"Optimal Value (Cost): {result.fval}")

# Construct Final Mask
final_mask_list = ['0'] * len(df)
candidate_real_ids = [c['original_index'] for c in candidates]

print("\n--> Mapping Quantum Solution back to Real World:")
for i, val in enumerate(result.x):
    original_idx = candidate_real_ids[i]
    if val == 1.0:
        final_mask_list[original_idx] = '1'
        print(f"  [ON] Candidate {i} (Real ID: {original_idx})")
    else:
        print(f"  [--] Candidate {i} (Real ID: {original_idx}) - Optimized OFF")

final_mask_str = "".join(final_mask_list)
print(f"\n GENERATED NS-3 MASK: {final_mask_str[:50]}...")
print(f"Run this: ./ns3 run 'scratch/manila_5g --mask={final_mask_str}'")

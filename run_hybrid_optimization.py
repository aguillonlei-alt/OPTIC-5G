import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from math import sqrt

# Qiskit Imports
from qiskit.circuit.library import TwoLocal
from qiskit_algorithms import SamplingVQE
from qiskit_algorithms.optimizers import COBYLA
from qiskit.primitives import Sampler
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.algorithms import MinimumEigenOptimizer
from qiskit_optimization.converters import QuadraticProgramToQubo

# ==========================================
# PHASE 1: CLASSICAL OPTIMIZATION (Greedy)
# ==========================================
print("\n=== PHASE 1: CLASSICAL PRE-PROCESSING (GREEDY) ===")

# 1. Load Real Data
df = pd.read_csv("data/hexagonal_candidates.csv")
print(f"--> Loaded {len(df)} total towers from Manila dataset.")

# 2. Greedy Filtering Logic
# Thesis Goal: Select 'N' best candidates that are spread out (not clumping).
# We calculate a 'Score' = TxPower (Higher is usually better coverage but higher energy).
# Ideally, we want efficient towers (High Coverage / Low Power).
# For this script, we use a Distance-Based Greedy approach:
# "Pick a tower, discard neighbors within 300m, pick next."

CANDIDATE_LIMIT = 12  # Number of Qubits (Limit for simulation speed)
MIN_DISTANCE = 300.0  # Meters between candidates

candidates = []
# Create a simple list of dicts
all_towers = df.to_dict('records')

# Add an original index to track which real tower this is
for idx, t in enumerate(all_towers):
    t['original_index'] = idx

# Sort by Power (heuristic: higher power = main macro tower)
all_towers.sort(key=lambda x: x['txpower_dbm'], reverse=True)

selected_indices = []

for tower in all_towers:
    if len(candidates) >= CANDIDATE_LIMIT:
        break
    
    # Check distance to already selected candidates
    is_far_enough = True
    for c in candidates:
        dist = sqrt((tower['x_m'] - c['x_m'])**2 + (tower['y_m'] - c['y_m'])**2)
        if dist < MIN_DISTANCE:
            is_far_enough = False
            break
    
    if is_far_enough:
        candidates.append(tower)
        selected_indices.append(tower['original_index'])

print(f"--> Selected {len(candidates)} candidates for Quantum Optimization.")
print(f"--> Candidate Indices: {selected_indices}")


# ==========================================
# PHASE 2: CONVERSION TO QUBO
# ==========================================
print("\n=== PHASE 2: QUBO FORMULATION ===")

# Create the Optimization Problem
qp = QuadraticProgram()

# 1. Define Binary Variables (x0, x1... x11)
# x_i = 1 means "Turn Tower ON", x_i = 0 means "Turn Tower OFF"
for i in range(len(candidates)):
    qp.binary_var(name=f"t_{i}")

# 2. Define the Objective Function (Hamiltonian)
# Minimize: Energy Consumption + Interference Penalty
# Energy Term (Linear): Cost of running the tower (TxPower)
# Interference Term (Quadratic): Penalty if two nearby towers are BOTH On.

linear_terms = {}
quadratic_terms = {}

# LINEAR TERMS (Energy Cost)
for i in range(len(candidates)):
    # Cost is proportional to Power. We normalize it slightly.
    cost = candidates[i]['txpower_dbm'] 
    linear_terms[f"t_{i}"] = cost

# QUADRATIC TERMS (Interference Penalty)
# If Tower A and Tower B are close (< 600m), adding both creates interference.
INTERFERENCE_THRESHOLD = 600.0
PENALTY_WEIGHT = 50.0

for i in range(len(candidates)):
    for j in range(i + 1, len(candidates)):
        # Calculate distance between candidate i and candidate j
        t1 = candidates[i]
        t2 = candidates[j]
        dist = sqrt((t1['x_m'] - t2['x_m'])**2 + (t1['y_m'] - t2['y_m'])**2)
        
        if dist < INTERFERENCE_THRESHOLD:
            # Add penalty (x_i * x_j)
            quadratic_terms[(f"t_{i}", f"t_{j}")] = PENALTY_WEIGHT

# Set the minimization objective
qp.minimize(linear=linear_terms, quadratic=quadratic_terms)

print("--> Converted to QUBO format.")
print(f"--> Variables: {qp.get_num_binary_vars()}, Linear Terms: {len(linear_terms)}, Quadratic Terms: {len(quadratic_terms)}")


# ==========================================
# PHASE 3: QUANTUM CIRCUIT & VISUALIZATION
# ==========================================
print("\n=== PHASE 3: QUANTUM CIRCUIT (ANSATZ) ===")

# 1. Define the Ansatz (The shape of the quantum circuit)
# TwoLocal is standard for VQE.
# Rotation 'ry' allows qubits to be in superposition (0 and 1).
# Entangler 'cz' connects qubits to solve the quadratic interference part.
ansatz = TwoLocal(num_qubits=len(candidates), rotation_blocks='ry', entanglement_blocks='cz', entanglement='linear', reps=1)

# 2. Draw and Save the Circuit
print("--> Generating Circuit Diagram...")
circuit_plot_path = "data/quantum_circuit_ansatz.png"
ansatz.decompose().draw(output='mpl', filename=circuit_plot_path)
print(f"Saved Quantum Circuit Diagram to: {circuit_plot_path}")


# ==========================================
# PHASE 4: EXECUTION (VQE)
# ==========================================
print("\n=== PHASE 4: RUNNING VQE OPTIMIZATION ===")

optimizer = COBYLA(maxiter=50) # Classical optimizer to tune parameters
sampler = Sampler() # Quantum Simulator

# CVaR Logic (Simplified for Thesis): 
# We run standard VQE here. For full CVaR, you would wrap 'evaluate' function.
vqe = SamplingVQE(sampler=sampler, ansatz=ansatz, optimizer=optimizer)
optimizer_vqe = MinimumEigenOptimizer(vqe)

# Solve the QUBO
result = optimizer_vqe.solve(qp)

print("\n=== FINAL RESULTS ===")
print(f"Optimal State: {result.x}")
print(f"Optimal Value (Cost): {result.fval}")

# Construct the FINAL MASK for NS-3
# We need a mask for ALL 189 towers.
# Default all to '0' (OFF), then turn ON the ones selected by Quantum.
final_mask_list = ['0'] * len(df)

print("\n--> Mapping Quantum Solution back to Real World:")
for i, val in enumerate(result.x):
    original_idx = selected_indices[i]
    if val == 1.0:
        final_mask_list[original_idx] = '1'
        print(f"  [ON] Candidate {i} (Real ID: {original_idx})")
    else:
        print(f"  [--] Candidate {i} (Real ID: {original_idx}) - Optimized OFF")

final_mask_str = "".join(final_mask_list)
print(f"\n GENERATED NS-3 MASK: {final_mask_str[:50]}... (Full length: {len(final_mask_str)})")
print("Run this command next:")
print(f"./ns3 run 'scratch/manila_5g --mask={final_mask_str}'")

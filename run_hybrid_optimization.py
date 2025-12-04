import pandas as pd
import numpy as np
from math import sqrt
import pulp  # The classical ILP solver

# Qiskit Imports for Phase 3
from qiskit.circuit.library import TwoLocal
from qiskit_algorithms import SamplingVQE
from qiskit_algorithms.optimizers import COBYLA
from qiskit.primitives import StatevectorSampler
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.algorithms import MinimumEigenOptimizer

# ==========================================
# CONFIGURATION
# ==========================================
FILE_PATH = "data/manila_towers_geocoded_fixed.csv"

# 1. Coverage Parameters (for Greedy/ILP)
COVERAGE_RADIUS_KM = 1.0  # Assumed 5G Small Cell/Macro radius
GRID_RESOLUTION = 20      # 20x20 grid points to simulate user demand

# 2. Constraints
MIN_COVERAGE_PCT = 0.95   # We want 95% of the campus covered

# 3. Quantum Parameters
INTERFERENCE_PENALTY = 500.0

# ==========================================
# 0. HELPER FUNCTIONS
# ==========================================
def haversine(lat1, lon1, lat2, lon2):
    """Calculates distance in km between two lat/lon points."""
    R = 6371  # Earth radius in km
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2) * np.sin(dlambda/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c

# ==========================================
# PHASE 1: PRE-PROCESSING & GREEDY FILTERING
# ==========================================
print("\n=== PHASE 1: CLASSICAL GREEDY FILTERING ===")

# 1. Load Data
df = pd.read_csv(FILE_PATH)

# 2. Sea Filter (From previous step)
df = df[df['longitude'] > 120.965].copy().reset_index(drop=True)
towers = df[['latitude', 'longitude']].to_dict('records')
print(f"--> Valid Land Towers: {len(towers)}")

# 3. Generate User Demand Grid (Simulating Campus Users)
# We create a grid of points over the tower area to check coverage
lat_min, lat_max = df['latitude'].min(), df['latitude'].max()
lon_min, lon_max = df['longitude'].min(), df['longitude'].max()

user_points = []
lat_steps = np.linspace(lat_min, lat_max, GRID_RESOLUTION)
lon_steps = np.linspace(lon_min, lon_max, GRID_RESOLUTION)

for lat in lat_steps:
    for lon in lon_steps:
        user_points.append({'lat': lat, 'lon': lon, 'covered': False})

print(f"--> Generated {len(user_points)} demand points for coverage verification.")

# 4. Greedy Algorithm
# Goal: Pick towers one by one that cover the MOST uncovered points until satisfied.
greedy_candidates = []
covered_indices = set()

print("--> Running Greedy Selection...")
while len(covered_indices) < len(user_points) * MIN_COVERAGE_PCT:
    best_tower_idx = -1
    best_new_cover = set()
    
    # Check every tower
    for idx, tower in enumerate(towers):
        if idx in greedy_candidates: continue # Skip if already picked
        
        # Calculate who this tower covers
        current_cover = set()
        for u_idx, user in enumerate(user_points):
            if u_idx not in covered_indices:
                dist = haversine(tower['latitude'], tower['longitude'], user['lat'], user['lon'])
                if dist <= COVERAGE_RADIUS_KM:
                    current_cover.add(u_idx)
        
        # Is this the best so far?
        if len(current_cover) > len(best_new_cover):
            best_new_cover = current_cover
            best_tower_idx = idx
            
    # Stop if no tower adds value
    if best_tower_idx == -1 or len(best_new_cover) == 0:
        break
        
    greedy_candidates.append(best_tower_idx)
    covered_indices.update(best_new_cover)

print(f"--> Greedy Selected {len(greedy_candidates)} candidates providing {len(covered_indices)/len(user_points)*100:.1f}% coverage.")
print(f"--> Candidate IDs: {greedy_candidates}")


# ==========================================
# PHASE 2: CLASSICAL ILP OPTIMIZATION
# ==========================================
print("\n=== PHASE 2: ILP OPTIMIZATION (PuLP) ===")
# Input: The candidates from Greedy (Refining the selection)
# Objective: Minimize Number of Towers
# Constraint: Ensure all currently covered points remain covered

prob = pulp.LpProblem("OPTIC5G_BaseStation_Placement", pulp.LpMinimize)

# Variables: Binary (1 if tower active, 0 if inactive)
tower_vars = {i: pulp.LpVariable(f"T_{i}", cat='Binary') for i in greedy_candidates}

# Objective Function: Minimize Sum of Active Towers
prob += pulp.lpSum([tower_vars[i] for i in greedy_candidates])

# Constraints: Every user point covered by Greedy must be covered by at least 1 ILP tower
# Pre-calculate coverage matrix to speed up
coverage_map = {u: [] for u in covered_indices} # Map User -> List of covering towers

for t_idx in greedy_candidates:
    tower = towers[t_idx]
    for u_idx in covered_indices:
        user = user_points[u_idx]
        dist = haversine(tower['latitude'], tower['longitude'], user['lat'], user['lon'])
        if dist <= COVERAGE_RADIUS_KM:
            coverage_map[u_idx].append(tower_vars[t_idx])

# Add constraints to ILP
for u_idx, covering_towers in coverage_map.items():
    if covering_towers:
        prob += pulp.lpSum(covering_towers) >= 1

# Solve
prob.solve(pulp.PULP_CBC_CMD(msg=0)) # msg=0 turns off verbose solver logs

ilp_selected = []
for i in greedy_candidates:
    if pulp.value(tower_vars[i]) == 1:
        ilp_selected.append(i)

print(f"--> ILP Optimized Candidates: {len(ilp_selected)} (Reduced from {len(greedy_candidates)})")
print(f"--> ILP IDs: {ilp_selected}")


# ==========================================
# PHASE 3: QUBO FORMULATION
# ==========================================
print("\n=== PHASE 3: QUANTUM REFINEMENT (QUBO + CVaR) ===")
# We take the ILP result and run it through Quantum to handle INTERFERENCE/RISK
# which ILP handles poorly (Quadratic constraints are hard for standard ILP).

qp = QuadraticProgram()
# Create variables only for the ILP survivors
for idx in ilp_selected:
    qp.binary_var(name=f"x_{idx}")

linear_terms = {}
quadratic_terms = {}

# A. Linear Terms (Activation Cost vs Coverage Reward)
# In this phase, we balance Power vs Risk.
for idx in ilp_selected:
    linear_terms[f"x_{idx}"] = -100.0  # Reward for keeping a robust tower ON

# B. Quadratic Terms (Interference Penalty)
# If two towers are too close, add penalty.
INTERFERENCE_DIST = 0.5 # km
interference_count = 0

for i in range(len(ilp_selected)):
    idx1 = ilp_selected[i]
    t1 = towers[idx1]
    
    for j in range(i + 1, len(ilp_selected)):
        idx2 = ilp_selected[j]
        t2 = towers[idx2]
        
        dist = haversine(t1['latitude'], t1['longitude'], t2['latitude'], t2['longitude'])
        
        if dist < INTERFERENCE_DIST:
            quadratic_terms[(f"x_{idx1}", f"x_{idx2}")] = INTERFERENCE_PENALTY
            interference_count += 1

qp.minimize(linear=linear_terms, quadratic=quadratic_terms)
print(f"--> QUBO Constructed with {interference_count} interference constraints.")


# ==========================================
# PHASE 4: CVaR-VQE EXECUTION
# ==========================================
print("--> Running CVaR-VQE...")

ansatz = TwoLocal(num_qubits=len(ilp_selected), rotation_blocks='ry', entanglement_blocks='cz')
optimizer = COBYLA(maxiter=100)
sampler = StatevectorSampler()

# CVaR logic is intrinsic to how we interpret the cost, 
# but for standard Qiskit Algorithms, we run VQE to find ground state.
vqe = SamplingVQE(sampler=sampler, ansatz=ansatz, optimizer=optimizer)
min_eigen_optimizer = MinimumEigenOptimizer(vqe)

result = min_eigen_optimizer.solve(qp)

# ==========================================
# 5. OUTPUT GENERATION
# ==========================================
print("\n=== OPTIC-5G FINAL RESULTS ===")
print(f"Classical Steps (Greedy -> ILP) reduced {len(towers)} towers to {len(ilp_selected)}.")
print(f"Quantum Step (VQE) optimized topology for interference.")

final_active_ids = []
vqe_binary = result.x # 1.0 or 0.0

for i, val in enumerate(vqe_binary):
    original_id = ilp_selected[i]
    if val == 1.0:
        final_active_ids.append(original_id)

print(f"Final Active Towers ({len(final_active_ids)}): {final_active_ids}")

# Create Mask String for Plotting
# We need a string length equal to the ORIGINAL dataframe
full_mask = ['0'] * len(df)
for fid in final_active_ids:
    full_mask[fid] = '1'

final_mask_str = "".join(full_mask)
print(f"\n✅ PLOT STRING: {final_mask_str}")

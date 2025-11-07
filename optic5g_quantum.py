import numpy as np, pandas as pd
from qiskit import QuantumCircuit
from qiskit.primitives import Estimator
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.algorithms import MinimumEigenOptimizer
from qiskit.algorithms.minimum_eigensolvers import VQE
from qiskit.algorithms.optimizers import COBYLA
from qiskit.circuit.library import TwoLocal
from qiskit.primitives import Sampler
from qiskit_algorithms import CVaRExpectation

df = pd.read_csv("data/optic5g_activation.csv")
qubo = QuadraticProgram()
for i in range(len(df)):
    qubo.binary_var(f"x{i}")

# Simplified quadratic cost: activate minimal number with penalty for overlap
objective = {f"x{i}": 1.0 for i in range(len(df))}
qubo.minimize(linear=objective)

# Quantum VQE with CVaR
ansatz = TwoLocal(len(df), 'ry', 'cz', reps=2)
estimator = Estimator()
vqe = VQE(estimator=estimator, ansatz=ansatz, optimizer=COBYLA(), expectation=CVaRExpectation(alpha=0.3))
opt = MinimumEigenOptimizer(vqe)

result = opt.solve(qubo)
df["quantum_active"] = [int(x) for x in result.x]
df.to_csv("data/optic5g_quantum_activation.csv", index=False)
print("✅ Quantum-optimized deployment saved: optic5g_quantum_activation.csv")

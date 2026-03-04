🛰️ OPTIC-5G: Hybrid Classical-Quantum Optimization for Energy-Efficient 5G Networks
OPTIC-5G is a thesis-driven research framework designed to solve the "Over-Provisioning" problem in ultra-dense 5G/6G networks. It integrates Classical Pre-processing (Greedy Algorithms + ILP) with Quantum Optimization (QUBO + CVaR-VQE) to identify the minimal set of active base stations required to maintain service coverage while drastically reducing energy consumption and inter-cell interference.

The framework was validated through Large-Scale Digital Twin Simulation (NS-3) and Physical Hardware Deployment at the Polytechnic University of the Philippines (PUP) Main Campus.

🧩 System Architecture
The system operates on a hybrid pipeline that reduces the combinatorial search space classically before utilizing quantum algorithms for the final topology optimization.
graph LR
    A[Raw Geospatial Data] --> B[Classical Filtering];
    B -->|Greedy + ILP| C[Reduced Candidate Set];
    C -->|QUBO Formulation| D[Quantum Optimization];
    D -->|CVaR-VQE Ansatz| E[Optimized Topology Mask];
    E --> F[NS-3 Simulation];
    E --> G[Physical Hardware Testbed];

    🔬 Research Workflow & Methodology
    Stage,Description,Tools / Output
1. Data Ingestion,"Extraction of real-world cellular tower coordinates (Manila) and conversion to Cartesian (x,y) metric space.","Pandas, Geopy"
2. Classical Filtering,Application of Greedy Algorithms to remove redundant overlaps and Integer Linear Programming (ILP) to generate a feasible candidate set.,"Python, PuLP"
3. Quantum Optimization,Formulation of the topology problem as a QUBO (Quadratic Unconstrained Binary Optimization) matrix. Solved using CVaR-VQE (Conditional Value-at-Risk Variational Quantum Eigensolver) to minimize energy and interference risks.,"IBM Qiskit, NumPy"
4. Simulation (Digital Twin),Large-scale validation of the optimized topology (22 Active Nodes vs. 243 Baseline) in a realistic urban propagation model.,"NS-3 (C++), LTE Module"
5. Physical Deployment,Small-scale experimental validation using TP-Link PharOS routers configured as 5G base stations at PUP Main Campus.,"Programmable Routers, PoE"

Gemini said
Here is the fully revised README.md incorporating all your recent updates, including the hardware deployment at the PUP Tennis Court, the specific "Hybrid" pipeline, and the finalized metrics.

You can copy-paste this directly into your GitHub repository.

🛰️ OPTIC-5G: Hybrid Classical-Quantum Optimization for Energy-Efficient 5G Networks
OPTIC-5G is a thesis-driven research framework designed to solve the "Over-Provisioning" problem in ultra-dense 5G/6G networks. It integrates Classical Pre-processing (Greedy Algorithms + ILP) with Quantum Optimization (QUBO + CVaR-VQE) to identify the minimal set of active base stations required to maintain service coverage while drastically reducing energy consumption and inter-cell interference.

The framework was validated through Large-Scale Digital Twin Simulation (NS-3) and Physical Hardware Deployment at the Polytechnic University of the Philippines (PUP) Main Campus.

🧩 System Architecture
The system operates on a hybrid pipeline that reduces the combinatorial search space classically before utilizing quantum algorithms for the final topology optimization.

Code snippet
graph LR
    A[Raw Geospatial Data] --> B[Classical Filtering];
    B -->|Greedy + ILP| C[Reduced Candidate Set];
    C -->|QUBO Formulation| D[Quantum Optimization];
    D -->|CVaR-VQE Ansatz| E[Optimized Topology Mask];
    E --> F[NS-3 Simulation];
    E --> G[Physical Hardware Testbed];
🔬 Research Workflow & Methodology
Stage	Description	Tools / Output
1. Data Ingestion	Extraction of real-world cellular tower coordinates (Manila) and conversion to Cartesian (x,y) metric space.	Pandas, Geopy
2. Classical Filtering	Application of Greedy Algorithms to remove redundant overlaps and Integer Linear Programming (ILP) to generate a feasible candidate set.	Python, PuLP
3. Quantum Optimization	Formulation of the topology problem as a QUBO (Quadratic Unconstrained Binary Optimization) matrix. Solved using CVaR-VQE (Conditional Value-at-Risk Variational Quantum Eigensolver) to minimize energy and interference risks.	IBM Qiskit, NumPy
4. Simulation (Digital Twin)	Large-scale validation of the optimized topology (22 Active Nodes vs. 243 Baseline) in a realistic urban propagation model.	NS-3 (C++), LTE Module
5. Physical Deployment	Small-scale experimental validation using TP-Link PharOS routers configured as 5G base stations at PUP Main Campus.	Programmable Routers, PoE
📊 Key Results
1. Simulation Findings (Manila City Scale)
Energy Reduction: 90.9% (Reduced active nodes from 243 to 22).
Throughput Retention: Maintained 1.20 Mbps (87% of baseline capacity) despite the massive reduction in hardware.
Interference: Significant reduction in Co-Channel Interference (CCI) due to increased spatial separation.

2. Experimental Findings (PUP Testbed)
Signal Quality: +40.6% improvement in Mean SNR (Signal-to-Noise Ratio) compared to the "Always-On" baseline.
Energy Efficiency: 50% reduction in hardware power consumption (Reduced active routers from 16 to 8).
Validation: RMSE of 13.76 dB between Simulation and Physical results, confirming model accuracy.

🛠️ Technologies & Hardware
Category,Stack
Simulation Engine,NS-3 (Network Simulator 3.3x) with LTE/mmWave modules
Quantum SDK,"IBM Qiskit (Circuit construction, VQE primitives, Aer Simulator)"
Classical Solvers,"PuLP (CBC Solver for ILP), SciPy"
Hardware Testbed,"TP-Link CPE210/510 (PharOS), PoE Injectors, Gigabit Switches"
Data Analysis,"Pandas, Matplotlib (Heatmaps/Voronoi), Seaborn"

⚙️ How to Run
1. Setup Environment
# Clone the repository
git clone https://github.com/your-username/OPTIC-5G.git
cd OPTIC-5G

# Create Virtual Environment
python3 -m venv venv
source venv/bin/activate

# Install Dependencies
pip install -r requirements.txt

2. Run the Optimization Pipeline
The main script runs the full Hybrid Classical-Quantum flow.

python main_optimizer.py

Input: data/real_towers_ns3.csv
Output: optimized_mask.txt (Binary string of ON/OFF states)

3. Run NS-3 Simulation
Requires a working NS-3 installation (C++).

# Copy the simulation script to your NS-3 scratch folder
cp simulations/manila_5g.cc ~/ns-3-dev/scratch/

# Run the simulation with the optimized mask
./ns3 run "scratch/manila_5g --mask=$(cat optimized_mask.txt)"

📸 Hardware Deployment
Physical validation conducted at the Polytechnic University of the Philippines (PUP) Tennis Court.

(Insert Image of Deployment Map / Router Setup here)

👥 Contributors
Polytechnic University of the Philippines – Sta. Mesa, Manila
Bachelor of Science in Electronics Engineering (BSECE)
Thesis – Academic Year 2025-2026
Jann Lei Randolf A. Aguillon

🛰️ OPTIC-5G: Hybrid Classical-Quantum Optimization for Energy-Efficient 5G NetworksOPTIC-5G is a thesis-driven research framework designed to solve the "Over-Provisioning" problem in ultra-dense 5G/6G networks. It integrates Classical Pre-processing (Greedy Algorithms + ILP) with Quantum Optimization (QUBO + CVaR-VQE) to identify the minimal set of active base stations required to maintain service coverage while drastically reducing energy consumption and inter-cell interference.The framework was validated through Large-Scale Digital Twin Simulation (NS-3) and Physical Hardware Deployment at the Polytechnic University of the Philippines (PUP) Main Campus.🧩 System ArchitectureThe system operates on a hybrid pipeline that reduces the combinatorial search space classically before utilizing quantum algorithms for the final topology optimization.Code snippetgraph LR
    A[Raw Geospatial Data] --> B[Classical Filtering];
    B -->|Greedy + ILP| C[Reduced Candidate Set];
    C -->|QUBO Formulation| D[Quantum Optimization];
    D -->|CVaR-VQE Ansatz| E[Optimized Topology Mask];
    E --> F[NS-3 Simulation];
    E --> G[Physical Hardware Testbed];
🔬 Research Workflow & MethodologyStageDescriptionTools / Output1. Data IngestionExtraction of real-world cellular tower coordinates (Manila) and conversion to Cartesian (x,y) metric space.Pandas, Geopy2. Classical FilteringApplication of Greedy Algorithms to remove redundant overlaps and Integer Linear Programming (ILP) to generate a feasible candidate set.Python, PuLP3. Quantum OptimizationFormulation of the topology problem as a QUBO (Quadratic Unconstrained Binary Optimization) matrix. Solved using CVaR-VQE (Conditional Value-at-Risk Variational Quantum Eigensolver) to minimize energy and interference risks.IBM Qiskit, NumPy4. Simulation (Digital Twin)Large-scale validation of the optimized topology (22 Active Nodes vs. 243 Baseline) in a realistic urban propagation model.NS-3 (C++), LTE Module5. Physical DeploymentSmall-scale experimental validation using TP-Link PharOS routers configured as 5G base stations at PUP Main Campus.Programmable Routers, PoE📊 Key Results1. Simulation Findings (Manila City Scale)Energy Reduction: 90.9% (Reduced active nodes from 243 to 22).Throughput Retention: Maintained 1.20 Mbps (87% of baseline capacity) despite the massive reduction in hardware.Interference: Significant reduction in Co-Channel Interference (CCI) due to increased spatial separation.2. Experimental Findings (PUP Testbed)Signal Quality: +40.6% improvement in Mean SNR (Signal-to-Noise Ratio) compared to the "Always-On" baseline.Energy Efficiency: 50% reduction in hardware power consumption (Reduced active routers from 16 to 8).Validation: RMSE of 13.76 dB between Simulation and Physical results, confirming model accuracy.🛠️ Technologies & HardwareCategoryStackSimulation EngineNS-3 (Network Simulator 3.3x) with LTE/mmWave modulesQuantum SDKIBM Qiskit (Circuit construction, VQE primitives, Aer Simulator)Classical SolversPuLP (CBC Solver for ILP), SciPyHardware TestbedTP-Link CPE210/510 (PharOS), PoE Injectors, Gigabit SwitchesData AnalysisPandas, Matplotlib (Heatmaps/Voronoi), Seaborn⚙️ How to Run1. Setup EnvironmentBash# Clone the repository
git clone https://github.com/your-username/OPTIC-5G.git
cd OPTIC-5G

# Create Virtual Environment
python3 -m venv venv
source venv/bin/activate

# Install Dependencies
pip install -r requirements.txt
2. Run the Optimization PipelineThe main script runs the full Hybrid Classical-Quantum flow.Bashpython main_optimizer.py
Input: data/real_towers_ns3.csvOutput: optimized_mask.txt (Binary string of ON/OFF states)3. Run NS-3 SimulationRequires a working NS-3 installation (C++).Bash# Copy the simulation script to your NS-3 scratch folder
cp simulations/manila_5g.cc ~/ns-3-dev/scratch/

# Run the simulation with the optimized mask
./ns3 run "scratch/manila_5g --mask=$(cat optimized_mask.txt)"
📸 Hardware DeploymentPhysical validation conducted at the Polytechnic University of the Philippines (PUP) Tennis Court.(Insert Image of Deployment Map / Router Setup here)👥 ContributorsPolytechnic University of the Philippines – Sta. Mesa, ManilaBachelor of Science in Electronics Engineering (BSECE)Thesis – Academic Year 2025-2026Jann Lei Randolf A. Aguillon

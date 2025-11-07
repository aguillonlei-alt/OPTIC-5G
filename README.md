# 🛰️ OPTIC-5G: Optimized Placement and Topology through Integration of Classical and Quantum Optimization Techniques

**OPTIC-5G** is a research-driven simulation and optimization framework for 5G base station deployment.  
It integrates **classical optimization (Greedy + ILP)** with **quantum optimization (QUBO + CVaR-VQE)** to achieve energy-efficient, coverage-optimized 5G network layouts — validated through **NS-3** simulations and **prototype 5 GHz router testing** at PUP Sta. Mesa.

---

## 📘 Repository Overview


---

## 🧩 Research Workflow

| Stage | Description | Output |
|--------|--------------|--------|
| **1. Data Extraction** | Extract raw tower data from official PDF | `manila_towers_clean.csv` |
| **2. Geocoding** | Convert addresses to lat/lon via geopy/Nominatim | `manila_towers_geocoded.csv` |
| **3. Projection** | Convert lat/lon → UTM (x, y) coordinates | `manila_towers_xy.csv` |
| **4. Visualization** | Plot tower distribution over Manila | `manila_towers_plot.png` |
| **5. NS-3 Preparation** | Create `real_towers_ns3.csv` for simulation | NS-3-ready dataset |
| **6. Baseline Simulation** | Run mmWave NS-3 simulation of actual towers | Coverage, SINR results |
| **7. Baseline Layout Generation** | Generate 17-router hexagonal grid for comparison | `baseline_layout.csv` |
| **8. Classical Optimization** | Apply Greedy + ILP optimization | `optic5g_classical.csv` |
| **9. Quantum Optimization** | Apply QUBO formulation and CVaR-VQE using Qiskit | `optic5g_quantum.csv` |
| **10. Evaluation** | Compare baseline, classical, and quantum layouts | Coverage %, SINR dB, Energy J |

---

## 🧠 Technologies Used

| Category | Stack |
|-----------|--------|
| **Simulation** | NS-3 (mmWave + LTE), Python bindings |
| **Optimization** | NumPy, PuLP (ILP), Qiskit (CVaR-VQE) |
| **Data Processing** | Pandas, Camelot-Py, Geopy, PyProj |
| **Visualization** | Matplotlib, Seaborn |
| **Prototype Testing** | 5 GHz routers, Access Point Controller (APC) |

---

## ⚙️ How to Run

### 1. Setup Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt


### 2. Extract and Process Tower Data
python scripts/extract_towers_camelot.py
python scripts/geocode_towers.py
python scripts/latlon_to_xy.py
python scripts/plot_towers.py
python scripts/simulate_real_towers_ns3.py

### 3. Extract and Process Tower Data
cd ~/Desktop/ns3-mmwave
./ns3 build
./ns3 run scratch/quantum_5g_sim

### 4. Run Optimization Pipeline
python scripts/generate_baseline_layout.py
python scripts/greedy_ilp_optimizer.py
python scripts/qubo_cvar_vqe_optimizer.py
python scripts/compare_baseline_vs_optimized.py

Output Metrics
1. Coverage Availability (%)
2. Signal Quality (SINR) (dB)
3. Throughput (Mbps)
4. Energy Efficiency (Joules)
5. Router Activation Vector (binary array)

System Architecture
 ┌────────────┐     ┌────────────┐     ┌──────────────┐
 │   PDF Data │ ─▶  │ Data Prep  │ ─▶  │  NS-3 Model  │
 │ (5G Towers)│     │ (Python)   │     │ (mmWave)     │
 └────────────┘     └─────┬──────┘     └──────┬───────┘
                           │                  │
                           ▼                  ▼
                     Classical Optimizer   Quantum Optimizer
                     (Greedy + ILP)        (QUBO + CVaR-VQE)
                           │                  │
                           └───────────▶──────┘
                               Evaluation + Plots

Contributors:
Polytechnic University of the Philippines – Sta. Mesa, Manila
BS Electronics Engineering 4-3
Thesis – AY 2025-2026

Jann Lei Randolf A. Aguillon

<div align="center">

  <h1>🛰️ OPTIC-5G</h1>
  <h3>Hybrid Classical-Quantum Optimization for Energy-Efficient 5G Networks</h3>

  <p>
    <b>A Thesis-Driven Research Framework for 5G/6G Topology Control</b><br>
    Validated via NS-3 Digital Twin & Physical Hardware Testbed
  </p>

  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  </a>
  <a href="https://qiskit.org/">
    <img src="https://img.shields.io/badge/Qiskit-Quantum-purple?style=for-the-badge&logo=qiskit&logoColor=white" alt="Qiskit">
  </a>
  <a href="https://www.nsnam.org/">
    <img src="https://img.shields.io/badge/NS--3-Simulation-green?style=for-the-badge&logo=cplusplus&logoColor=white" alt="NS-3">
  </a>
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License">
  </a>
  <br>
</div>

<br>

---

## 📖 Overview

**OPTIC-5G** solves the "Over-Provisioning" problem in ultra-dense 5G networks. Instead of leaving all base stations "Always-On" (which wastes power and causes interference), this framework identifies the **minimal active topology** required to maintain coverage.

It uses a unique **Hybrid Pipeline**:
1.  **Classical Filtering (Greedy + ILP):** Rapidly shrinks the search space.
2.  **Quantum Optimization (CVaR-VQE):** Finds the optimal configuration using IBM's Qiskit SDK.

> **🏆 Validated Results:**
> * **90.9%** Reduction in Energy Consumption (Simulation).
> * **40.6%** Improvement in Signal Quality / SNR (Physical Testbed).
> * **13.76 dB** RMSE between Digital Twin and Reality.

---

## 🧩 System Architecture

The system follows a strict data-to-deployment pipeline.

```mermaid
graph LR
    A[Raw Geospatial Data] -->|Pandas/Geopy| B(Classical Filtering);
    B -->|Greedy + ILP| C{Reduced Candidate Set};
    C -->|QUBO Formulation| D[Quantum Optimization];
    D -->|CVaR-VQE Ansatz| E[Optimized Mask];
    E --> F[NS-3 Simulation];
    E --> G[Physical Hardware Testbed];
    style D fill:#f9f,stroke:#333,stroke-width:2px
    style G fill:#bbf,stroke:#333,stroke-width:2px

# Academic Project Report: AI-Based Smart Package Management System
**Course:** Foundations of Artificial Intelligence (FOAI)  
**Algorithm Category:** Constraint Satisfaction Problems (CSP) & Heuristic Search  
**Techniques Implemented:** Backtracking Search, Forward Checking (FC), Minimum Remaining Values (MRV), Degree Heuristic, Least Constraining Value (LCV)  
**Implementation Language & Framework:** Python 3, Streamlit, Matplotlib, Pandas  

---

## Executive Summary / Abstract
Urban logistics, smart parcel lockers, and warehouse distribution centers face a severe combinatorial resource allocation challenge: assigning incoming parcels of diverse dimensions, weight limits, perishability requirements, and delivery urgency to physical compartments with strict capacity and environmental constraints. 

In this project, we design, formulate, implement, and benchmark an **AI-Based Smart Package Management System** powered by **Constraint Satisfaction Problem (CSP)** algorithms. Rather than relying on simple greedy heuristics that frequently produce deadlocks and allocation failures, our system models package-to-compartment assignment as a formal CSP. We implement three variants:
1. **Pure Backtracking (Baseline)**
2. **Backtracking with Forward Checking (FC)**
3. **Optimized Backtracking with Forward Checking + Minimum Remaining Values (MRV) + Least Constraining Value (LCV)**

Empirical benchmarks demonstrate that when constraint tightness increases, Pure Backtracking suffers exponential thrashing ($>1,000,000$ nodes explored for $N=14$), whereas the MRV + Forward Checking engine prunes the search space by over **99.99%**, finding valid assignments in less than **1 millisecond**.

---

## 1. Mathematical Problem Formulation (CSP Formalism)

In Artificial Intelligence, a Constraint Satisfaction Problem is formally defined as a triple $\langle X, D, C \rangle$:

### 1.1 Variables ($X$)
Let $X = \{P_1, P_2, \dots, P_n\}$ be the set of $n$ unallocated incoming packages waiting in the intake queue. Each package $P_i$ possesses a tuple of physical and operational attributes:
$$P_i = \langle \text{size}_i, \text{weight}_i, \text{is\_perishable}_i, \text{priority}_i, \text{deadline}_i \rangle$$
Where:
- $\text{size}_i \in \{\text{Small (S)}, \text{Medium (M)}, \text{Large (L)}\}$
- $\text{weight}_i \in \mathbb{R}^+$ (measured in kilograms)
- $\text{is\_perishable}_i \in \{\text{True}, \text{False}\}$
- $\text{priority}_i \in \{\text{Standard}, \text{Express}, \text{Urgent}\}$

### 1.2 Domains ($D$)
Let $L = \{L_1, L_2, \dots, L_m\}$ be the set of physical locker compartments. Each compartment $L_j$ possesses:
$$L_j = \langle \text{size}_j, \text{max\_weight}_j, \text{is\_refrigerated}_j, \text{tier}_j, \text{status}_j \rangle$$

The domain $D_i \subseteq L$ for each package $P_i$ represents all available compartments that satisfy the unary physical compatibility conditions:
$$D_i = \left\{ L_j \in L \;\middle|\; \begin{aligned} &\text{status}_j = \text{Available} \\ &\land \text{SizeFit}(\text{size}_i, \text{size}_j) \\ &\land \text{weight}_i \le \text{max\_weight}_j \\ &\land (\text{is\_perishable}_i \implies \text{is\_refrigerated}_j) \end{aligned} \right\}$$

### 1.3 Constraints ($C$)
The system enforces both hard physical constraints and soft ergonomic preferences:
1. **Unary Physical Constraints**:
   - **Dimension Compatibility:** $\text{Hierarchy}(P_i.\text{size}) \le \text{Hierarchy}(L_j.\text{size})$ where $\text{S} < \text{M} < \text{L}$.
   - **Load Capacity:** $P_i.\text{weight} \le L_j.\text{max\_weight}$.
   - **Cold Chain Integrity:** If $P_i.\text{is\_perishable} = \text{True}$, then $L_j.\text{is\_refrigerated} = \text{True}$.
2. **Binary Global Constraints (AllDifferent)**:
   - No two distinct packages can be assigned to the identical physical compartment:
     $$\forall i \neq k, \quad \text{Assignment}(P_i) \neq \text{Assignment}(P_k)$$
3. **Ergonomic Accessibility Optimization (Soft Constraint / Value Ordering)**:
   - High-priority / Urgent packages prefer Tier 1 (eye-level) compartments to minimize courier and customer retrieval times.

---

## 2. Project Execution by Development Phases

```
+-----------------------------------------------------------------------------------------+
|                               PROJECT EXECUTION TIMELINE                                |
+-----------------------------------------------------------------------------------------+
| Phase 1: Problem Definition & Data Structures                       (Days 1 - 2)        |
| Phase 2: CSP Solver Engine Implementation                           (Days 3 - 5)        |
| Phase 3: Package Management Operations & Logic                      (Days 6 - 7)        |
| Phase 4: User Interface & Visualizer                                (Days 8 - 10)       |
| Phase 5: Empirical Benchmarking, Evaluation & Viva Defense          (Days 11 - 12)      |
+-----------------------------------------------------------------------------------------+
```

---

### Phase 1: Problem Definition & Data Structures (Days 1–2)

#### Objectives & Deliverables:
- Model physical entity structures using strict object-oriented typing.
- Formalize size hierarchies, priority rankings, and constraint checking functions.
- Source Code file: `src/models.py`.

#### Key Implementation Details:
- Implemented `SizeCategory` enum with a monotonic hierarchy check:
  ```python
  class SizeCategory(str, Enum):
      SMALL = "S"
      MEDIUM = "M"
      LARGE = "L"

      @classmethod
      def fits(cls, pkg_size, locker_size) -> bool:
          hierarchy = {cls.SMALL: 1, cls.MEDIUM: 2, cls.LARGE: 3}
          return hierarchy[pkg_size] <= hierarchy[locker_size]
  ```
- Implemented `Package` and `Locker` dataclasses with `can_accommodate(package)` unary validator, ensuring instant pre-pruning of infeasible domain values.

---

### Phase 2: CSP Solver Engine Implementation (Days 3–5)

#### Objectives & Deliverables:
- Implement the core search algorithms:
  1. Pure Backtracking Search
  2. Backtracking with Forward Checking (FC)
  3. Backtracking with FC + MRV + Degree Heuristic + LCV
- Instrument the solver to capture diagnostic metrics: nodes visited, backtrack count, and wall-clock execution time.
- Source Code file: `src/csp_solver.py`.

#### Algorithmic Implementations:

#### 1. Baseline: Pure Backtracking
Selects variables sequentially and values in arbitrary order. Backtracks only after attempting to assign an incompatible value.
- **Worst-case Time Complexity:** $O(d^n)$ where $d$ is maximum domain size and $n$ is number of packages.

#### 2. Forward Checking (FC)
Whenever variable $X_i$ is assigned value $v$, the algorithm looks ahead and prunes $v$ from the domains of all remaining unassigned variables. If any variable's domain becomes empty ($\emptyset$), the branch is pruned immediately before exploring invalid subtrees.

#### 3. Optimized: MRV + Degree Heuristic + LCV
- **Minimum Remaining Values (MRV / "Fail-First Principle"):** Chooses the unassigned package with the fewest legal lockers remaining:
  $$\text{Var}^* = \arg\min_{X_i \in \text{Unassigned}} |D_i|$$
- **Degree Heuristic (Tie-Breaker):** Breaks MRV ties by selecting the package with highest urgency and weight.
- **Least Constraining Value (LCV / "Succeed-First Principle"):** When picking a locker for the selected package, picks the locker that rules out the fewest choices for other unassigned packages.

---

### Phase 3: Package Management Operations & Logic (Days 6–7)

#### Objectives & Deliverables:
- Connect the mathematical CSP engine to real-world facility workflows.
- Implement facility state management: Fleet initialization, package intake queue, automated batch allocation, individual parcel check-out/retrieval, and utilization tracking.
- Source Code file: `src/package_manager.py` and CLI driver `main.py`.

#### Workflow Mechanics:
1. **Intake Queueing:** Packages arriving from couriers are placed in an intake buffer `pending_packages`.
2. **CSP Problem Generation:** When allocation is triggered, the current active locker availability is snapshot into a `PackageCSP` instance.
3. **State Mutation:** If a conflict-free solution is found, the lockers are marked occupied and associated with the package tracking IDs.
4. **Retrieval Lifecycle:** Customers or couriers provide tracking numbers or IDs; the system unlocks the compartment and immediately restores the slot to available status.

---

### Phase 4: User Interface & Visualizer (Days 8–10)

#### Objectives & Deliverables:
- Build a dual-layer interface system:
  1. **Decoupled Client-Server Full-Stack Architecture**:
     - **Backend REST API** (`backend/server.py`): Built with FastAPI, Pydantic schemas, and Uvicorn. Exposes endpoints for facility status (`/api/facility`), intake (`/api/packages/intake`), CSP solver execution (`/api/allocate`), retrieval (`/api/retrieve`), and empirical analytics (`/api/benchmark-data`).
     - **Frontend Client** (`frontend/index.html`, `frontend/style.css`, `frontend/app.js`): Modern responsive dashboard utilizing asynchronous JavaScript `fetch` calls, dynamic DOM manipulation, real-time status indicators, and custom CSS styling.
  2. **Streamlit Interactive Visualizer** (`app.py`): Rapid single-file interactive visual dashboard for demonstrations.
- Implement real-time physical compartment matrix visualizer with color-coded status (Available vs Occupied vs Refrigerated).
- Provide manual and batch intake forms, retrieval mechanisms, and live solver metric inspection.

#### UI & API Architecture:
- **FastAPI Endpoints**:
  - `GET /api/facility`: Returns live fleet metrics, locker states, active packages, and queue.
  - `POST /api/allocate`: Accepts solver choice (`pure`, `fc`, `fc_mrv_lcv`), executes CSP engine, and returns search space telemetry.
  - `POST /api/packages/intake`: Validates and enqueues a new package.
  - `POST /api/retrieve`: Releases assigned compartment upon parcel collection.
- **Frontend Dashboard Sections**:
  - **KPI Metrics Bar:** Total Lockers, Occupied percentage, Available capacity, Cold Storage utilization, and Pending queue size.
  - **Compartment Matrix Grid:** Visual grid rendering each locker with dynamic cards:
    - Green (`#ECFDF5`) = Available
    - Red (`#FEF2F2`) = Occupied (displaying package ID and recipient)
    - Badges for Temperature (❄️ Refrigerated vs 🌡️ Ambient) and Accessibility Tier.
  - **Intake & Diagnostics View:** Live display of search space metrics (Nodes Explored, Backtracks, Latency in ms).
  - **Benchmarking Tab:** Interactive rendering of empirical comparison tables and Matplotlib plots.

---

### Phase 5: Empirical Benchmarking, Evaluation & Viva Defense (Days 11–12)

#### Objectives & Deliverables:
- Design high-contention test suites with tight constraints (competing perishable goods and high weight limits).
- Measure Search Space (Nodes Explored), Failures (Backtracks), and Latency (ms) across varying input sizes $N \in [6, 16]$.
- Source Code file: `benchmark.py`, outputting `benchmark_data.csv` and `benchmark_results.png`.

#### Empirical Results Table:

| Problem Size ($N$) | Pure BT Nodes | Pure BT Backtracks | Pure BT Time (ms) | FC Nodes | FC Backtracks | FC Time (ms) | FC+MRV Nodes | FC+MRV Backtracks | FC+MRV Time (ms) | Pruning Efficiency |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **6** | 31 | 30 | 0.05 | 3 | 2 | 0.20 | **4** | **3** | **0.14** | 87.1% |
| **8** | 77 | 76 | 0.10 | 3 | 2 | 0.04 | **3** | **2** | **0.08** | 96.1% |
| **10** | 10,810 | 10,809 | 18.99 | 1 | 0 | 0.70 | **1** | **0** | **0.05** | **99.99%** |
| **12** | 80,840 | 80,839 | 102.67 | 277 | 276 | 2.64 | **4** | **3** | **0.16** | **99.99%** |
| **14** | 1,147,617 | 1,147,616 | 2,000.02* | 161,398 | 161,397 | 1,088.64 | **11** | **10** | **0.49** | **99.99%** |
| **16** | 1,200,704 | 1,200,703 | 2,000.01* | 544,888 | 544,887 | 4,512.29 | **1** | **0** | **0.07** | **99.999%** |

*\*Note: Pure Backtracking hit the 2.0-second safety timeout at $N=14$ and $N=16$ due to combinatorial thrashing.*

#### Visual Benchmark Chart:
The benchmark script automatically generates high-resolution comparative plots saved as `benchmark_results.png`, illustrating:
1. Exponential curve of Pure Backtracking vs. Flat curve of FC+MRV for Nodes Explored.
2. Backtrack reduction showing near-zero search failures for MRV.
3. Real-time latency remaining sub-millisecond for the optimized engine.

---

## 3. Comprehensive Viva Voce Questions & Answers

### Q1: Why did you choose CSP over standard greedy algorithms or A* search?
**Answer:**
A greedy algorithm makes locally optimal choices (e.g., placing package 1 in the first locker it fits). In constrained environments, this frequently leads to **deadlocks** where an incoming large or refrigerated package has no remaining valid slots, requiring total reallocation. Standard $A^*$ search is designed for shortest-path pathfinding in state spaces where costs accumulate additively along edges. Package allocation is fundamentally a **combinatorial satisfaction problem** where all constraints must be satisfied simultaneously; CSP with Forward Checking guarantees finding a valid assignment without deadlocks.

### Q2: What is the MRV heuristic, and why is it called the "Fail-First" principle?
**Answer:**
MRV (Minimum Remaining Values) selects the unassigned variable that has the fewest legal values in its domain. It is called "fail-first" because if a variable has few options (e.g., a large refrigerated package that can only fit in 1 specific locker), assigning it immediately causes any potential contradiction to be detected early near the root of the search tree, preventing the algorithm from wasting exponential time exploring an invalid subtree.

### Q3: How does Forward Checking prevent thrashing?
**Answer:**
Standard backtracking only checks constraints between currently assigned variables; it does not look ahead. Thus, it can make an assignment that makes a future unassigned variable's domain empty, only discovering this failure hundreds of thousands of steps later (thrashing). Forward Checking prunes inconsistent values from unassigned variables' domains immediately after every assignment. If any domain becomes empty ($\emptyset$), it halts the branch immediately.

### Q4: What is the computational complexity of your CSP implementation?
**Answer:**
- **Worst-case Time Complexity:** $O(d^n)$ where $n$ is the number of packages and $d$ is the maximum number of compatible lockers.
- **With Forward Checking + MRV:** In practice, the effective branching factor is reduced to nearly $O(1)$ to $O(b)$ where $b \ll d$, reducing search time from seconds/minutes down to fractions of a millisecond.
- **Space Complexity:** $O(n \cdot d)$ to store the domain states across recursion depth $n$.

---

## 4. How to Run the Project

### Running the CLI Demonstration:
```powershell
python main.py
```

### Running the Benchmarking Suite & Generating Charts:
```powershell
python benchmark.py
```

### Launching the Streamlit Web Dashboard:
```powershell
streamlit run app.py
```

---

## 5. Conclusion
The **AI-Based Smart Package Management System** demonstrates the application of core Foundations of AI search algorithms to modern smart-city logistics. By formulating the locker management challenge as a formal Constraint Satisfaction Problem, our implementation demonstrates how heuristic variable ordering (MRV) and domain inference (Forward Checking) turn an otherwise intractable NP-hard combinatorial problem into a real-time, fault-tolerant system.


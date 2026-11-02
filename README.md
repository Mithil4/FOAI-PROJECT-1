# AI-Based Smart Package Management System (FOAI Project)

An intelligent package allocation and smart locker management system built using **Constraint Satisfaction Problem (CSP)** algorithms from the Foundations of Artificial Intelligence (FOAI) syllabus.

## Core AI Algorithms & Heuristics
- **Constraint Satisfaction Problem (CSP) Formulation**: Variables ($X$), Domains ($D$), Constraints ($C$).
- **Pure Backtracking Search** (Baseline).
- **Forward Checking (FC)** (Domain lookahead & pruning).
- **Minimum Remaining Values (MRV)** ("Fail-First" variable ordering heuristic).
- **Degree Heuristic** (Tie-breaker on urgency and weight).
- **Least Constraining Value (LCV)** (Value ordering heuristic).

---

## Architecture & Options

The project is structured with a decoupled **Full-Stack Client-Server Architecture** as well as a standalone Streamlit application:

```
foai/
├── backend/
│   ├── __init__.py
│   └── server.py              # FastAPI REST API (CORS, Endpoints, Swagger Docs)
├── frontend/
│   ├── index.html             # Responsive Dashboard UI (HTML5)
│   ├── style.css              # Custom Modern CSS (Tailwind aesthetic)
│   ├── app.js                 # Async Client JavaScript (Fetch API & DOM)
│   └── benchmark_results.png  # Static assets
├── src/
│   ├── models.py              # Package, Locker, and Size/Priority schemas
│   ├── csp_solver.py          # Backtracking, FC, MRV, and LCV solver engines
│   └── package_manager.py     # Facility state, intake, check-in, check-out
├── app.py                     # Streamlit Full-Stack Dashboard
├── main.py                    # Terminal CLI runner and test harness
├── benchmark.py               # Empirical evaluation and comparative plotting
├── benchmark_results.png      # High-resolution benchmark comparison visualization
├── benchmark_data.csv         # Generated metrics CSV table
├── PROJECT_REPORT.md          # Full phased academic report (Days 1–12 format)
└── README.md                  # Quick-start documentation
```

---

## Quick Start (Running on Any Computer)

### 1. Clone the repository
```bash
git clone <your-repo-url>
cd foai
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Launch the Application
Choose any of the run options below:

#### Option 1: Full-Stack Web App (FastAPI Backend + Modern Frontend) - Recommended
```bash
python -m uvicorn backend.server:app --reload --port 8000
```
Open **http://127.0.0.1:8000** in your browser.

#### Option 2: Streamlit Dashboard
```bash
streamlit run app.py
```

#### Option 3: Terminal CLI Runner
```bash
python main.py
```

#### Option 4: Re-run Benchmarking & Plot Generation
```bash
python benchmark.py
```

---

## Complete Project Report
See [PROJECT_REPORT.md](file:///c:/Users/Mohamed%20Aseel/OneDrive/Desktop/foai/PROJECT_REPORT.md) for the full 12-day phased documentation, mathematical formulations, complexity analysis, and viva defense Q&A.


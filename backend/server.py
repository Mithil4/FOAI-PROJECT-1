"""
FastAPI REST API Backend for Smart Package Management System.
Exposes REST endpoints for:
- Facility status & locker matrix
- Package intake into queue
- CSP Solver automated allocation
- Package checkout / retrieval
- Algorithmic benchmarking data
- Serves the static Frontend dashboard
"""

import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.models import Package, Locker, SizeCategory, PriorityLevel
from src.package_manager import SmartPackageManager
from src.csp_solver import PackageCSP

app = FastAPI(
    title="Smart Package Management System API",
    description="REST API backend powered by Constraint Satisfaction Problem (CSP) algorithms (MRV, FC, LCV)",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Facility Manager Instance
manager = SmartPackageManager()
manager.initialize_default_facility(total_lockers=15)
manager.load_sample_packages()


# ---------------- REQUEST & RESPONSE SCHEMAS ----------------
class IntakePackageRequest(BaseModel):
    tracking_number: str
    recipient_name: str
    size: str  # "S", "M", "L"
    weight_kg: float
    is_perishable: bool = False
    priority: str = "Standard"  # "Standard", "Express", "Urgent"


class AllocationRequest(BaseModel):
    algorithm: str = "fc_mrv_lcv"  # "pure", "fc", "fc_mrv_lcv"


class ReconfigureFacilityRequest(BaseModel):
    total_lockers: int = 15


class RetrievePackageRequest(BaseModel):
    package_id_or_tracking: str


# ---------------- API ENDPOINTS (BACKEND) ----------------

@app.get("/api/health")
def health_check():
    return {"status": "online", "system": "SmartPack AI Backend"}


@app.get("/api/facility")
def get_facility_state():
    """Returns the full state of all lockers, active packages, queue, and statistics."""
    stats = manager.get_facility_stats()
    lockers = [l.to_dict() for l in manager.lockers.values()]
    active = [p.to_dict() for p in manager.active_packages.values()]
    queue = [p.to_dict() for p in manager.pending_packages]
    last_metrics = manager.last_solver_metrics.to_dict() if manager.last_solver_metrics else None

    return {
        "stats": stats,
        "lockers": lockers,
        "active_packages": active,
        "pending_queue": queue,
        "last_solver_metrics": last_metrics
    }


@app.post("/api/facility/reconfigure")
def reconfigure_facility(req: ReconfigureFacilityRequest):
    """Reconfigures locker fleet capacity."""
    if req.total_lockers < 4 or req.total_lockers > 50:
        raise HTTPException(status_code=400, detail="Total lockers must be between 4 and 50.")
    manager.initialize_default_facility(total_lockers=req.total_lockers)
    return {"message": f"Facility reconfigured with {req.total_lockers} lockers.", "stats": manager.get_facility_stats()}


@app.post("/api/packages/intake")
def intake_package(pkg_in: IntakePackageRequest):
    """Enqueues a new package into the pending allocation queue."""
    try:
        size_enum = SizeCategory(pkg_in.size)
        prio_enum = PriorityLevel(pkg_in.priority)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid size or priority: {str(e)}")

    new_id = f"PKG-{len(manager.active_packages) + len(manager.pending_packages) + 1:02d}"
    pkg = Package(
        id=new_id,
        tracking_number=pkg_in.tracking_number,
        recipient_name=pkg_in.recipient_name,
        size=size_enum,
        weight_kg=pkg_in.weight_kg,
        is_perishable=pkg_in.is_perishable,
        priority=prio_enum
    )
    manager.add_package_to_queue(pkg)
    return {"message": "Package enqueued successfully", "package": pkg.to_dict()}


@app.post("/api/packages/load-sample")
def load_sample_packages():
    """Populates queue with representative test packages."""
    manager.load_sample_packages()
    return {"message": "Sample packages loaded into queue", "queue_count": len(manager.pending_packages)}


@app.post("/api/queue/clear")
def clear_queue():
    """Clears all packages in pending queue."""
    manager.clear_pending_queue()
    return {"message": "Pending queue cleared."}


@app.post("/api/facility/reset")
def reset_facility():
    """Resets all lockers to available and clears queue."""
    manager.reset_facility()
    return {"message": "Facility completely reset. All lockers are now available."}


@app.post("/api/allocate")
def trigger_allocation(req: AllocationRequest):
    """Executes the CSP solver on pending packages against available lockers."""
    if not manager.pending_packages:
        return {"success": True, "message": "Pending queue is empty. No packages to allocate.", "metrics": None}

    try:
        success, metrics, unassigned = manager.process_allocation(req.algorithm)
        return {
            "success": success,
            "algorithm_used": metrics.algorithm_name,
            "metrics": metrics.to_dict(),
            "unassigned_count": len(unassigned),
            "unassigned_packages": [p.to_dict() for p in unassigned]
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Solver execution error: {str(e)}")


@app.post("/api/retrieve")
def retrieve_package(req: RetrievePackageRequest):
    """Checks out a package by ID or tracking number, releasing the compartment."""
    res = manager.retrieve_package(req.package_id_or_tracking.strip())
    if not res:
        raise HTTPException(status_code=404, detail="Package not found or already picked up.")
    pkg, locker = res
    return {
        "message": f"Package {pkg.id} successfully retrieved.",
        "package": pkg.to_dict(),
        "freed_locker": locker.to_dict()
    }


@app.get("/api/benchmark-data")
def get_benchmark_data():
    """Returns stored empirical benchmarking data."""
    csv_path = "benchmark_data.csv"
    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail="Benchmark data not generated yet. Run benchmark.py first.")
    import pandas as pd
    df = pd.read_csv(csv_path)
    return df.to_dict(orient="records")


# ---------------- MOUNT FRONTEND STATIC ASSETS ----------------
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    def serve_frontend():
        return FileResponse(os.path.join(frontend_dir, "index.html"))


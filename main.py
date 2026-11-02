"""
Main CLI Driver for Smart Package Management System.
Demonstrates facility initialization, CSP problem formulation,
solving via multiple heuristics, and package lifecycle.
"""

from src.package_manager import SmartPackageManager
from src.models import Package, SizeCategory, PriorityLevel



def print_header(title: str):
    print("\n" + "=" * 70)
    print(f" {title.upper()} ")
    print("=" * 70)


def main():
    print_header("AI-Based Smart Package Management System (FOAI Project)")
    print("Core Algorithm: Backtracking with Constraint Satisfaction (CSP)")
    print("Heuristics: Minimum Remaining Values (MRV) + Forward Checking (FC) + LCV\n")

    # 1. Initialize Facility
    manager = SmartPackageManager()
    manager.initialize_default_facility(total_lockers=12)
    print(f"[+] Initialized Smart Locker Facility with {len(manager.lockers)} compartments.")
    
    # 2. Enqueue Sample Packages
    manager.load_sample_packages()
    print(f"[+] Enqueued {len(manager.pending_packages)} pending incoming packages with diverse constraints.")
    
    print("\nIncoming Packages Preview:")
    for p in manager.pending_packages:
        print(f"  - {p.id}: Size={p.size.value}, Wt={p.weight_kg}kg, Perishable={p.is_perishable}, Priority={p.priority.value}")

    # 3. Benchmark CSP Solvers on this batch
    print_header("Algorithm Execution Comparison")
    
    # Run Pure Backtracking
    test_csp = SmartPackageManager()
    test_csp.initialize_default_facility(total_lockers=12)
    test_csp.load_sample_packages()
    _, pure_metrics, _ = test_csp.process_allocation("pure")

    # Run Forward Checking
    test_csp_fc = SmartPackageManager()
    test_csp_fc.initialize_default_facility(total_lockers=12)
    test_csp_fc.load_sample_packages()
    _, fc_metrics, _ = test_csp_fc.process_allocation("fc")

    # Run Optimized MRV + LCV + FC
    success, opt_metrics, unassigned = manager.process_allocation("fc_mrv_lcv")

    print(f"{'Algorithm':<40} | {'Nodes Explored':<14} | {'Backtracks':<10} | {'Time (ms)':<10}")
    print("-" * 82)
    for m in [pure_metrics, fc_metrics, opt_metrics]:
        print(f"{m.algorithm_name:<40} | {m.nodes_visited:<14} | {m.backtracks:<10} | {m.execution_time_ms:<10.3f}")

    print_header("Allocation Results & Compartment Status")
    for pkg_id, locker_id in opt_metrics.assignment.items():
        pkg = manager.active_packages[pkg_id]
        lck = manager.lockers[locker_id]
        print(f"  * Package {pkg.id} ({pkg.tracking_number}) -> Assigned to Compartment {lck.id} "
              f"[Size: {lck.size.value}, Refrig: {lck.is_refrigerated}, Tier: {lck.accessibility_tier}]")

    print("\nFacility Summary:")
    for k, v in manager.get_facility_stats().items():
        print(f"  - {k}: {v}")

    # 4. Test Package Retrieval
    print_header("Package Retrieval / Check-Out Test")
    test_tracking = "TRK-9802"  # Perishable, Urgent
    result = manager.retrieve_package(test_tracking)
    if result:
        pkg, locker = result
        print(f"[OK] Package {pkg.id} ({pkg.recipient_name}) successfully retrieved from {locker.id}.")
        print(f"[OK] Compartment {locker.id} status is now: {'Occupied' if locker.is_occupied else 'Available'}.")

    print("\n[OK] System operations completed successfully.")


if __name__ == "__main__":
    main()

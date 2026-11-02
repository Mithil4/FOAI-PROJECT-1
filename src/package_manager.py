"""
Smart Package Management System Engine.
Integrates the CSP solver with facility operations:
- Fleet initialization
- Package intake & check-in
- Constraint-optimized automated allocation
- Package retrieval & checkout
- Fleet status and utilization monitoring
"""

from typing import List, Dict, Optional, Tuple, Any
from .models import Package, Locker, SizeCategory, PriorityLevel
from .csp_solver import PackageCSP, SolverMetrics


class SmartPackageManager:
    def __init__(self):
        self.lockers: Dict[str, Locker] = {}
        self.active_packages: Dict[str, Package] = {}
        self.pending_packages: List[Package] = []
        self.last_solver_metrics: Optional[SolverMetrics] = None

    def initialize_default_facility(self, total_lockers: int = 18):
        """Initializes a realistic smart locker facility with diverse specs."""
        self.lockers.clear()
        self.active_packages.clear()
        self.pending_packages.clear()

        # Distribution: 40% Small, 40% Medium, 20% Large
        # 30% Refrigerated, Tier 1 (eye level) vs Tier 2 (top/bottom)
        for i in range(1, total_lockers + 1):
            locker_id = f"LCK-{i:02d}"
            
            # Determine size
            if i <= int(total_lockers * 0.4):
                size = SizeCategory.SMALL
                max_weight = 5.0
            elif i <= int(total_lockers * 0.8):
                size = SizeCategory.MEDIUM
                max_weight = 15.0
            else:
                size = SizeCategory.LARGE
                max_weight = 30.0

            # Determine refrigeration (compartments 3, 4, 7, 8, etc.)
            is_refrigerated = (i % 3 == 0)
            
            # Accessibility: middle compartments (tier 1) vs top/bottom (tier 2)
            tier = 1 if (i % 2 == 1) else 2

            self.lockers[locker_id] = Locker(
                id=locker_id,
                compartment_number=i,
                size=size,
                max_weight_kg=max_weight,
                is_refrigerated=is_refrigerated,
                accessibility_tier=tier
            )

    def add_package_to_queue(self, package: Package):
        """Adds incoming package to pending intake queue."""
        self.pending_packages.append(package)

    def process_allocation(self, algorithm_type: str = "fc_mrv_lcv") -> Tuple[bool, SolverMetrics, List[Package]]:
        """
        Executes CSP allocation for pending packages against available lockers.
        Prioritizes packages by urgency and allocates up to available capacity.
        Returns: (success, metrics, unassigned_packages)
        """
        if not self.pending_packages:
            dummy_metric = SolverMetrics("None")
            dummy_metric.is_successful = True
            return True, dummy_metric, []

        # Available compartments check
        available_lockers = [l for l in self.lockers.values() if not l.is_occupied]
        if not available_lockers:
            metrics = SolverMetrics("No Available Lockers")
            metrics.is_successful = False
            return False, metrics, self.pending_packages

        # Deduplicate pending packages by ID to ensure CSP variable integrity
        seen_ids = set()
        unique_queue = []
        for p in self.pending_packages:
            if p.id not in seen_ids:
                seen_ids.add(p.id)
                unique_queue.append(p)

        # Prioritize queue: Urgent/Perishable first, then by priority score
        priority_weights = {PriorityLevel.URGENT: 3, PriorityLevel.EXPRESS: 2, PriorityLevel.STANDARD: 1}
        sorted_queue = sorted(
            unique_queue,
            key=lambda p: (priority_weights[p.priority], p.is_perishable, p.weight_kg),
            reverse=True
        )

        # Allocate up to the number of available physical compartments
        batch_to_allocate = sorted_queue[:len(available_lockers)]
        overflow_packages = sorted_queue[len(available_lockers):]

        csp = PackageCSP(batch_to_allocate, available_lockers)

        if algorithm_type == "pure":
            metrics = csp.solve_pure_backtracking()
        elif algorithm_type == "fc":
            metrics = csp.solve_forward_checking()
        else:
            metrics = csp.solve_fc_mrv_lcv()

        self.last_solver_metrics = metrics

        assigned_any = False
        unassigned: List[Package] = []

        if metrics.is_successful and len(metrics.assignment) == len(batch_to_allocate):
            # All items in batch successfully allocated!
            for pkg in batch_to_allocate:
                locker_id = metrics.assignment.get(pkg.id)
                if locker_id and locker_id in self.lockers:
                    pkg.assigned_locker_id = locker_id
                    self.lockers[locker_id].current_package_id = pkg.id
                    self.active_packages[pkg.id] = pkg
                    assigned_any = True
                else:
                    unassigned.append(pkg)
            unassigned.extend(overflow_packages)
            self.pending_packages = unassigned
            return True, metrics, unassigned
        else:
            # Scarce-resource contention: not all items in batch could fit simultaneously.
            # Perform Priority-Driven Incremental CSP to place as many as possible!
            temp_free_lockers = {l.id: l for l in available_lockers}
            incremental_assignment: Dict[str, str] = {}
            total_nodes = metrics.nodes_visited
            total_backtracks = metrics.backtracks

            for pkg in sorted_queue:
                current_free = [l for lid, l in temp_free_lockers.items() if lid not in incremental_assignment.values()]
                if not current_free:
                    unassigned.append(pkg)
                    continue

                sub_csp = PackageCSP([pkg], current_free)
                if algorithm_type == "pure":
                    sub_m = sub_csp.solve_pure_backtracking()
                elif algorithm_type == "fc":
                    sub_m = sub_csp.solve_forward_checking()
                else:
                    sub_m = sub_csp.solve_fc_mrv_lcv()

                total_nodes += sub_m.nodes_visited
                total_backtracks += sub_m.backtracks

                if sub_m.is_successful and sub_m.assignment:
                    chosen_locker = sub_m.assignment[pkg.id]
                    incremental_assignment[pkg.id] = chosen_locker
                    pkg.assigned_locker_id = chosen_locker
                    self.lockers[chosen_locker].current_package_id = pkg.id
                    self.active_packages[pkg.id] = pkg
                    assigned_any = True
                else:
                    unassigned.append(pkg)

            # Update metrics
            metrics.nodes_visited = total_nodes
            metrics.backtracks = total_backtracks
            metrics.assignment = incremental_assignment
            metrics.is_successful = assigned_any
            self.last_solver_metrics = metrics
            self.pending_packages = unassigned

            return assigned_any, metrics, unassigned

    def clear_pending_queue(self):
        """Clears all packages in pending queue."""
        self.pending_packages.clear()

    def reset_facility(self):
        """Empties all lockers and clears all queues."""
        for locker in self.lockers.values():
            locker.current_package_id = None
        self.active_packages.clear()
        self.pending_packages.clear()
        self.last_solver_metrics = None

    def retrieve_package(self, package_id_or_tracking: str) -> Optional[Tuple[Package, Locker]]:
        """Retrieves and releases locker for a package."""
        target_pkg = None
        for pkg in self.active_packages.values():
            if pkg.id == package_id_or_tracking or pkg.tracking_number == package_id_or_tracking:
                target_pkg = pkg
                break

        if not target_pkg or not target_pkg.assigned_locker_id:
            return None

        locker = self.lockers[target_pkg.assigned_locker_id]
        locker.current_package_id = None
        del self.active_packages[target_pkg.id]
        return target_pkg, locker

    def get_facility_stats(self) -> Dict[str, Any]:
        """Calculates real-time fleet utilization."""
        total = len(self.lockers)
        occupied = sum(1 for l in self.lockers.values() if l.is_occupied)
        available = total - occupied
        cold_total = sum(1 for l in self.lockers.values() if l.is_refrigerated)
        cold_occupied = sum(1 for l in self.lockers.values() if l.is_refrigerated and l.is_occupied)

        return {
            "Total Lockers": total,
            "Occupied Lockers": occupied,
            "Available Lockers": available,
            "Utilization Rate (%)": round((occupied / total * 100) if total > 0 else 0, 1),
            "Cold Storage Occupied": f"{cold_occupied}/{cold_total}",
            "Pending in Queue": len(self.pending_packages),
            "Active Packages": len(self.active_packages)
        }

    def load_sample_packages(self):
        """Loads representative sample packages with unique IDs covering all constraint scenarios."""
        start_idx = len(self.active_packages) + len(self.pending_packages) + 1
        samples_data = [
            ("Alice Smith", SizeCategory.SMALL, 1.2, False, PriorityLevel.STANDARD),
            ("Dr. Robert", SizeCategory.SMALL, 0.8, True, PriorityLevel.URGENT),
            ("Elena Rostova", SizeCategory.LARGE, 18.5, False, PriorityLevel.EXPRESS),
            ("Marcus Vance", SizeCategory.MEDIUM, 4.2, False, PriorityLevel.STANDARD),
            ("Fresh Farms Ltd", SizeCategory.MEDIUM, 6.0, True, PriorityLevel.EXPRESS),
            ("Tech Labs Inc", SizeCategory.SMALL, 2.5, False, PriorityLevel.URGENT),
            ("Sophia Patel", SizeCategory.LARGE, 22.0, False, PriorityLevel.STANDARD),
            ("BioPharma Care", SizeCategory.SMALL, 0.5, True, PriorityLevel.URGENT),
        ]
        for i, (name, size, wt, cold, prio) in enumerate(samples_data):
            idx = start_idx + i
            pkg = Package(
                id=f"PKG-{idx:02d}",
                tracking_number=f"TRK-{9800 + idx}",
                recipient_name=name,
                size=size,
                weight_kg=wt,
                is_perishable=cold,
                priority=prio
            )
            self.add_package_to_queue(pkg)

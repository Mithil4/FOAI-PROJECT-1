"""
Constraint Satisfaction Problem (CSP) Solver for Smart Package Management.
Implements:
1. Pure Backtracking
2. Backtracking with Forward Checking
3. Backtracking with Forward Checking + MRV (Minimum Remaining Values) + LCV Heuristic
Includes full diagnostic instrumentation (nodes visited, backtracks, execution time).
"""

import time
from typing import List, Dict, Optional, Tuple, Set, Any
from copy import deepcopy
from .models import Package, Locker, PriorityLevel


class SolverMetrics:
    def __init__(self, algorithm_name: str):
        self.algorithm_name = algorithm_name
        self.nodes_visited = 0
        self.backtracks = 0
        self.execution_time_ms = 0.0
        self.is_successful = False
        self.assignment: Dict[str, str] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "Algorithm": self.algorithm_name,
            "Solved": self.is_successful,
            "Assigned Packages": len(self.assignment),
            "Nodes Explored": self.nodes_visited,
            "Backtracks": self.backtracks,
            "Execution Time (ms)": round(self.execution_time_ms, 3)
        }


class PackageCSP:
    """
    Formal CSP Definition for Package-Locker Allocation:
    - Variables X: Set of Packages {P_1, P_2, ..., P_n}
    - Domains D: For each P_i, D(P_i) = {L_j in Lockers | L_j satisfies unary physical constraints}
    - Constraints C:
        1. AllDifferent: For all P_a != P_b, Assignment(P_a) != Assignment(P_b)
        2. Capacity/Refrigeration/Weight: Handled in initial domain reduction.
        3. Priority Preference: High priority items prefer Tier 1 lockers.
    """

    def __init__(self, packages: List[Package], lockers: List[Locker]):
        self.packages = packages
        self.lockers = lockers
        # Ensure variables are unique and preserve order
        self.variables = list(dict.fromkeys(p.id for p in packages))
        self.package_map = {p.id: p for p in packages}
        self.locker_map = {l.id: l for l in lockers}

        # Build initial domains based on unary physical constraints
        # Only lockers that are currently unoccupied and can accommodate package
        self.initial_domains: Dict[str, List[str]] = {}
        for p in self.packages:
            valid_lockers = [
                l.id for l in self.lockers
                if (not l.is_occupied) and l.can_accommodate(p)
            ]
            self.initial_domains[p.id] = valid_lockers

    # -------------------------------------------------------------
    # 1. PURE BACKTRACKING (Baseline)
    # -------------------------------------------------------------
    def solve_pure_backtracking(self, timeout_sec: float = 2.0) -> SolverMetrics:
        metrics = SolverMetrics("Pure Backtracking (Baseline)")
        start_time = time.perf_counter()
        assignment: Dict[str, str] = {}

        def backtrack(index: int) -> bool:
            metrics.nodes_visited += 1
            if time.perf_counter() - start_time > timeout_sec:
                return False  # Timeout safeguard against combinatorial explosion

            if index == len(self.variables):
                return True

            var = self.variables[index]
            for val in self.initial_domains[var]:
                # Check binary constraint: no other variable already has this locker
                if val not in assignment.values():
                    assignment[var] = val
                    if backtrack(index + 1):
                        return True
                    # Backtrack
                    metrics.backtracks += 1
                    del assignment[var]

            return False

        metrics.is_successful = backtrack(0)
        metrics.execution_time_ms = (time.perf_counter() - start_time) * 1000
        metrics.assignment = assignment if metrics.is_successful else {}
        return metrics

    # -------------------------------------------------------------
    # 2. BACKTRACKING WITH FORWARD CHECKING
    # -------------------------------------------------------------
    def solve_forward_checking(self) -> SolverMetrics:
        metrics = SolverMetrics("Backtracking + Forward Checking")
        start_time = time.perf_counter()
        assignment: Dict[str, str] = {}
        domains = {var: list(self.initial_domains[var]) for var in self.variables}

        def forward_check(var: str, value: str, current_domains: Dict[str, List[str]]) -> Optional[Dict[str, List[str]]]:
            """Prunes value from remaining unassigned variables. Returns None if domain wipeout."""
            new_domains = {}
            for other_var, other_domain in current_domains.items():
                if other_var not in assignment and other_var != var:
                    pruned = [l for l in other_domain if l != value]
                    if not pruned:  # Domain wipeout!
                        return None
                    new_domains[other_var] = pruned
                else:
                    new_domains[other_var] = other_domain
            return new_domains

        best_assignment: Dict[str, str] = {}

        def backtrack(index: int, current_domains: Dict[str, List[str]]) -> bool:
            nonlocal best_assignment
            metrics.nodes_visited += 1

            if len(assignment) > len(best_assignment):
                best_assignment = dict(assignment)

            if index == len(self.variables):
                return True

            var = self.variables[index]
            for val in current_domains[var]:
                if val not in assignment.values():
                    # Attempt forward check
                    pruned_domains = forward_check(var, val, current_domains)
                    if pruned_domains is not None:
                        assignment[var] = val
                        if backtrack(index + 1, pruned_domains):
                            return True
                        # Backtrack
                        metrics.backtracks += 1
                        del assignment[var]

            return False

        full_success = backtrack(0, domains)
        metrics.is_successful = full_success or (len(best_assignment) > 0)
        metrics.execution_time_ms = (time.perf_counter() - start_time) * 1000
        metrics.assignment = assignment if full_success else best_assignment
        return metrics

    # -------------------------------------------------------------
    # 3. BACKTRACKING + FORWARD CHECKING + MRV + DEGREE + LCV
    # -------------------------------------------------------------
    def solve_fc_mrv_lcv(self) -> SolverMetrics:
        metrics = SolverMetrics("Backtracking + FC + MRV + LCV (Optimized)")
        start_time = time.perf_counter()
        assignment: Dict[str, str] = {}
        domains = {var: list(self.initial_domains[var]) for var in self.variables}

        def select_unassigned_variable(current_domains: Dict[str, List[str]]) -> str:
            """
            MRV (Minimum Remaining Values) heuristic:
            Selects the variable with the fewest available locker options.
            Tie-breaker: Degree Heuristic (package with Urgent priority / largest weight).
            """
            unassigned = [v for v in self.variables if v not in assignment]
            if not unassigned:
                return None
            
            def variable_key(var: str):
                # Primary: domain size (MRV)
                dom_size = len(current_domains[var])
                # Secondary: priority level (Urgent > Express > Standard)
                pkg = self.package_map[var]
                priority_score = {
                    PriorityLevel.URGENT: 3,
                    PriorityLevel.EXPRESS: 2,
                    PriorityLevel.STANDARD: 1
                }[pkg.priority]
                # We want MIN domain size, then MAX priority (hence negative)
                return (dom_size, -priority_score, -pkg.weight_kg)

            return min(unassigned, key=variable_key)

        def order_domain_values(var: str, current_domains: Dict[str, List[str]]) -> List[str]:
            """
            LCV (Least Constraining Value) & Ergonomic Tier Heuristic:
            Prefers lockers that eliminate the fewest options for remaining unassigned variables.
            Urgent items prefer Tier 1 (accessible) lockers.
            """
            pkg = self.package_map[var]
            unassigned = [v for v in self.variables if v not in assignment and v != var]
            
            def value_cost(val: str) -> Tuple[int, int]:
                # How many other unassigned variables have this locker in their domain?
                conflicts = sum(1 for other_var in unassigned if val in current_domains[other_var])
                
                # Accessibility preference:
                locker = self.locker_map[val]
                tier_penalty = 0
                if pkg.priority in (PriorityLevel.URGENT, PriorityLevel.EXPRESS):
                    tier_penalty = locker.accessibility_tier  # Tier 1 = preferred (lower penalty)

                return (conflicts, tier_penalty)

            return sorted(current_domains[var], key=value_cost)

        def forward_check(var: str, value: str, current_domains: Dict[str, List[str]]) -> Optional[Dict[str, List[str]]]:
            new_domains = {}
            for other_var, other_domain in current_domains.items():
                if other_var not in assignment and other_var != var:
                    pruned = [l for l in other_domain if l != value]
                    if not pruned:  # Forward-check caught a wipeout
                        return None
                    new_domains[other_var] = pruned
                else:
                    new_domains[other_var] = other_domain
            return new_domains

        best_assignment: Dict[str, str] = {}

        def backtrack(current_domains: Dict[str, List[str]]) -> bool:
            nonlocal best_assignment
            metrics.nodes_visited += 1

            if len(assignment) > len(best_assignment):
                best_assignment = dict(assignment)

            if len(assignment) >= len(self.variables):
                return True

            var = select_unassigned_variable(current_domains)
            if var is None:
                return True

            ordered_values = order_domain_values(var, current_domains)

            for val in ordered_values:
                if val not in assignment.values():
                    pruned_domains = forward_check(var, val, current_domains)
                    if pruned_domains is not None:
                        assignment[var] = val
                        if backtrack(pruned_domains):
                            return True
                        # Backtrack
                        metrics.backtracks += 1
                        del assignment[var]

            return False

        full_success = backtrack(domains)
        metrics.is_successful = full_success or (len(best_assignment) > 0)
        metrics.execution_time_ms = (time.perf_counter() - start_time) * 1000
        metrics.assignment = assignment if full_success else best_assignment
        return metrics

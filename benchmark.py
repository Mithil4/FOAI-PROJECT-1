"""
Empirical Benchmark and Evaluation Script for FOAI Project.
Generates complex high-contention package allocation scenarios
and benchmarks Pure Backtracking vs Forward Checking vs FC + MRV + LCV.
Saves comparison plots to 'benchmark_results.png'.
"""

import time
import random
import matplotlib.pyplot as plt
import pandas as pd
from typing import List
from src.models import Package, Locker, SizeCategory, PriorityLevel
from src.csp_solver import PackageCSP


def generate_benchmark_scenario(num_packages: int, tightness_ratio: float = 0.9):
    """
    Generates a tight constraint problem where lockers are scarce
    and constraint conflicts (size, refrigeration, weight) trigger extensive backtracking.
    """
    random.seed(42)  # For reproducible academic benchmarks
    num_lockers = max(num_packages, int(num_packages / tightness_ratio))

    lockers: List[Locker] = []
    for i in range(1, num_lockers + 1):
        # Locker distribution
        if i <= int(num_lockers * 0.45):
            size = SizeCategory.SMALL
            max_w = 5.0
        elif i <= int(num_lockers * 0.8):
            size = SizeCategory.MEDIUM
            max_w = 15.0
        else:
            size = SizeCategory.LARGE
            max_w = 35.0

        is_refrig = (i % 4 == 0)  # Only 25% refrigerated (scarce resource!)
        tier = 1 if (i % 2 == 1) else 2
        lockers.append(Locker(f"L-{i:02d}", i, size, max_w, is_refrig, tier))

    packages: List[Package] = []
    sizes = [SizeCategory.SMALL, SizeCategory.MEDIUM, SizeCategory.LARGE]
    priorities = [PriorityLevel.STANDARD, PriorityLevel.EXPRESS, PriorityLevel.URGENT]

    for p in range(1, num_packages + 1):
        pkg_size = random.choice(sizes)
        # Weight proportional to size
        base_w = {"S": random.uniform(0.5, 4.5), "M": random.uniform(5.0, 14.0), "L": random.uniform(15.0, 30.0)}
        weight = round(base_w[pkg_size.value], 1)
        # 20% perishable packages competing for 25% refrigerated lockers
        perishable = (p % 5 == 0)
        prio = random.choice(priorities)

        packages.append(Package(
            id=f"P-{p:02d}",
            tracking_number=f"TRK-{1000+p}",
            recipient_name=f"User-{p}",
            size=pkg_size,
            weight_kg=weight,
            is_perishable=perishable,
            priority=prio
        ))

    return packages, lockers


def run_benchmark():
    print("================================================================")
    print(" Running Empirical Evaluation & Benchmarking for CSP Solvers")
    print("================================================================")

    test_sizes = [6, 8, 10, 12, 14, 16]
    results = []

    for size in test_sizes:
        print(f"\nEvaluating Problem Size: N = {size} packages...")
        pkgs, lcks = generate_benchmark_scenario(size, tightness_ratio=0.85)

        # 1. Pure Backtracking
        csp_pure = PackageCSP(pkgs, lcks)
        m_pure = csp_pure.solve_pure_backtracking()

        # 2. Forward Checking
        csp_fc = PackageCSP(pkgs, lcks)
        m_fc = csp_fc.solve_forward_checking()

        # 3. Optimized FC + MRV + LCV
        csp_opt = PackageCSP(pkgs, lcks)
        m_opt = csp_opt.solve_fc_mrv_lcv()

        results.append({
            "N": size,
            "Pure_Nodes": m_pure.nodes_visited,
            "Pure_Backtracks": m_pure.backtracks,
            "Pure_Time_ms": m_pure.execution_time_ms,
            "FC_Nodes": m_fc.nodes_visited,
            "FC_Backtracks": m_fc.backtracks,
            "FC_Time_ms": m_fc.execution_time_ms,
            "Opt_Nodes": m_opt.nodes_visited,
            "Opt_Backtracks": m_opt.backtracks,
            "Opt_Time_ms": m_opt.execution_time_ms,
        })
        print(f"  Pure BT : Nodes={m_pure.nodes_visited:4d}, Backtracks={m_pure.backtracks:3d}, Time={m_pure.execution_time_ms:.2f}ms")
        print(f"  FC      : Nodes={m_fc.nodes_visited:4d}, Backtracks={m_fc.backtracks:3d}, Time={m_fc.execution_time_ms:.2f}ms")
        print(f"  FC+MRV  : Nodes={m_opt.nodes_visited:4d}, Backtracks={m_opt.backtracks:3d}, Time={m_opt.execution_time_ms:.2f}ms")

    df = pd.DataFrame(results)
    df.to_csv("benchmark_data.csv", index=False)
    print("\n[OK] Saved benchmark data to 'benchmark_data.csv'.")

    # Generate Academic Charts
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig.suptitle("Performance Comparison of CSP Algorithms in Smart Package Allocation", fontsize=14, fontweight="bold")

    # Subplot 1: Search Space Explored (Nodes Visited)
    axes[0].plot(df["N"], df["Pure_Nodes"], marker="o", color="#e74c3c", label="Pure Backtracking", linewidth=2)
    axes[0].plot(df["N"], df["FC_Nodes"], marker="s", color="#f39c12", label="Backtracking + FC", linewidth=2)
    axes[0].plot(df["N"], df["Opt_Nodes"], marker="^", color="#27ae60", label="FC + MRV + LCV", linewidth=2)
    axes[0].set_title("Search Space (Nodes Visited)", fontweight="bold")
    axes[0].set_xlabel("Number of Packages (N)")
    axes[0].set_ylabel("Nodes Explored")
    axes[0].grid(True, linestyle="--", alpha=0.6)
    axes[0].legend()

    # Subplot 2: Backtracks Required
    axes[1].plot(df["N"], df["Pure_Backtracks"], marker="o", color="#e74c3c", label="Pure Backtracking", linewidth=2)
    axes[1].plot(df["N"], df["FC_Backtracks"], marker="s", color="#f39c12", label="Backtracking + FC", linewidth=2)
    axes[1].plot(df["N"], df["Opt_Backtracks"], marker="^", color="#27ae60", label="FC + MRV + LCV", linewidth=2)
    axes[1].set_title("Search Failures (Backtracks)", fontweight="bold")
    axes[1].set_xlabel("Number of Packages (N)")
    axes[1].set_ylabel("Backtrack Count")
    axes[1].grid(True, linestyle="--", alpha=0.6)
    axes[1].legend()

    # Subplot 3: Execution Time
    axes[2].plot(df["N"], df["Pure_Time_ms"], marker="o", color="#e74c3c", label="Pure Backtracking", linewidth=2)
    axes[2].plot(df["N"], df["FC_Time_ms"], marker="s", color="#f39c12", label="Backtracking + FC", linewidth=2)
    axes[2].plot(df["N"], df["Opt_Time_ms"], marker="^", color="#27ae60", label="FC + MRV + LCV", linewidth=2)
    axes[2].set_title("Execution Latency (ms)", fontweight="bold")
    axes[2].set_xlabel("Number of Packages (N)")
    axes[2].set_ylabel("Time (ms)")
    axes[2].grid(True, linestyle="--", alpha=0.6)
    axes[2].legend()

    plt.tight_layout()
    chart_path = "benchmark_results.png"
    plt.savefig(chart_path, dpi=300)
    plt.close()
    print(f"[OK] Saved high-resolution benchmark visualization to '{chart_path}'.")


if __name__ == "__main__":
    run_benchmark()

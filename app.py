"""
Streamlit Web Dashboard for AI-Based Smart Package Management System.
Features:
- Real-time Visual Locker Grid
- Automated CSP Package Allocation
- Multi-Algorithm Selection & Diagnostic Metrics
- Package Retrieval / Check-out
- Empirical Benchmark & Complexity Analytics
"""

import os
import streamlit as st
import pandas as pd
from PIL import Image

from src.models import Package, Locker, SizeCategory, PriorityLevel
from src.package_manager import SmartPackageManager
from src.csp_solver import PackageCSP


# ---------------- PAGE CONFIG & STYLING ----------------
st.set_page_config(
    page_title="SmartPack AI - Package Management System",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        color: #4B5563;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #F3F4F6;
        padding: 1rem;
        border-radius: 8px;
        border-left: 5px solid #2563EB;
    }
    .locker-card {
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.06);
        transition: transform 0.15s ease-in-out;
    }
    .locker-card:hover {
        transform: translateY(-2px);
    }
    .locker-available {
        background-color: #ECFDF5;
        border: 1.5px solid #10B981;
    }
    .locker-occupied {
        background-color: #FEF2F2;
        border: 1.5px solid #EF4444;
    }
</style>
""", unsafe_allow_html=True)


# ---------------- SESSION STATE INITIALIZATION ----------------
if "manager" not in st.session_state:
    mgr = SmartPackageManager()
    mgr.initialize_default_facility(total_lockers=15)
    st.session_state.manager = mgr

manager: SmartPackageManager = st.session_state.manager


# ---------------- SIDEBAR CONTROLS ----------------
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2830/2830305.png", width=60)
    st.title("SmartPack AI")
    st.caption("Foundations of AI (FOAI) Course Project")
    st.markdown("---")

    st.subheader("⚙️ Facility Management")
    num_lockers = st.slider("Total Compartments", min_value=6, max_value=30, value=len(manager.lockers), step=3)
    if st.button("🔄 Reset / Re-initialize Facility"):
        manager.initialize_default_facility(total_lockers=num_lockers)
        st.session_state.last_metrics = None
        st.success(f"Facility reconfigured with {num_lockers} lockers.")
        st.rerun()

    if st.button("📥 Load Sample Intake Queue"):
        manager.load_sample_packages()
        st.success(f"Loaded {len(manager.pending_packages)} test packages into pending queue.")
        st.rerun()

    st.markdown("---")
    st.subheader("🧠 CSP Solver Algorithm")
    algo_choice = st.radio(
        "Select Solver Engine:",
        options=[
            ("fc_mrv_lcv", "FC + MRV + LCV (Optimized)"),
            ("fc", "Forward Checking (Pruning)"),
            ("pure", "Pure Backtracking (Baseline)")
        ],
        format_func=lambda x: x[1]
    )[0]

    st.info("💡 **FOAI Heuristic Notice:** MRV selects the most constrained package first, while Forward Checking prevents domain wipeouts early.")


# ---------------- MAIN CONTENT HEADER ----------------
st.markdown('<div class="main-title">📦 Smart Package Management System</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Automated locker compartment allocation using <b>Constraint Satisfaction Problems (CSP)</b> with <b>MRV & Forward Checking</b>.</div>', unsafe_allow_html=True)


# ---------------- TOP METRICS DASHBOARD ----------------
stats = manager.get_facility_stats()
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Lockers", stats["Total Lockers"])
col2.metric("Occupied", f"{stats['Occupied Lockers']} ({stats['Utilization Rate (%)']}%)")
col3.metric("Available", stats["Available Lockers"])
col4.metric("Cold Storage Occupied", stats["Cold Storage Occupied"])
col5.metric("Pending in Queue", stats["Pending in Queue"])

st.markdown("---")

# ---------------- TABS INTERFACE ----------------
tab1, tab2, tab3, tab4 = st.tabs(["🏢 Locker Grid & Fleet View", "📥 Intake & CSP Allocation", "📤 Retrieve Package", "📊 Empirical Benchmarks"])


# ---------------- TAB 1: VISUAL LOCKER GRID ----------------
with tab1:
    st.subheader("Physical Compartment Matrix")
    st.caption("Visual representation of lockers with capacity, temperature control, and occupancy status.")

    cols_per_row = 5
    locker_list = list(manager.lockers.values())

    for i in range(0, len(locker_list), cols_per_row):
        row_lockers = locker_list[i:i + cols_per_row]
        cols = st.columns(cols_per_row)
        for idx, locker in enumerate(row_lockers):
            with cols[idx]:
                status_class = "locker-occupied" if locker.is_occupied else "locker-available"
                status_text = "OCCUPIED" if locker.is_occupied else "AVAILABLE"
                status_color = "#DC2626" if locker.is_occupied else "#059669"
                refrig_badge = "❄️ Cold" if locker.is_refrigerated else "🌡️ Normal"
                tier_badge = "👁️ Eye Level" if locker.accessibility_tier == 1 else "📐 Low/High"
                
                content = f"""
                <div class="locker-card {status_class}">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <b style="font-size:1.1rem;">{locker.id}</b>
                        <span style="font-size:0.75rem; font-weight:bold; color:{status_color};">{status_text}</span>
                    </div>
                    <hr style="margin:6px 0;">
                    <div style="font-size:0.85rem; line-height:1.4;">
                        <b>Size:</b> {locker.size.value} (Max {locker.max_weight_kg}kg)<br>
                        <b>Environment:</b> {refrig_badge}<br>
                        <b>Position:</b> {tier_badge}<br>
                    </div>
                """
                if locker.is_occupied:
                    pkg = manager.active_packages.get(locker.current_package_id)
                    pkg_info = f"<b>Pkg:</b> {pkg.id}<br><b>To:</b> {pkg.recipient_name}" if pkg else f"ID: {locker.current_package_id}"
                    content += f"""
                    <div style="margin-top:6px; padding:4px 6px; background:#FEE2E2; border-radius:4px; font-size:0.8rem; color:#991B1B;">
                        {pkg_info}
                    </div>
                    """
                content += "</div>"
                st.markdown(content, unsafe_allow_html=True)


# ---------------- TAB 2: INTAKE & CSP ALLOCATION ----------------
with tab2:
    left_col, right_col = st.columns([1, 1])

    with left_col:
        st.subheader("➕ Intake New Package")
        with st.form("new_package_form", clear_on_submit=True):
            f_trk = st.text_input("Tracking Number", value=f"TRK-{len(manager.active_packages)+len(manager.pending_packages)+101}")
            f_recipient = st.text_input("Recipient Name", value="John Doe")
            f_col1, f_col2 = st.columns(2)
            f_size = f_col1.selectbox("Size Category", options=[SizeCategory.SMALL, SizeCategory.MEDIUM, SizeCategory.LARGE], format_func=lambda s: s.value)
            f_weight = f_col2.number_input("Weight (kg)", min_value=0.1, max_value=35.0, value=2.5, step=0.5)
            f_col3, f_col4 = st.columns(2)
            f_cold = f_col3.checkbox("Perishable / Needs Refrigeration", value=False)
            f_priority = f_col4.selectbox("Priority Level", options=[PriorityLevel.STANDARD, PriorityLevel.EXPRESS, PriorityLevel.URGENT], format_func=lambda p: p.value)

            submit_btn = st.form_submit_button("Enqueue Package")
            if submit_btn:
                new_id = f"PKG-{len(manager.active_packages)+len(manager.pending_packages)+1:02d}"
                pkg = Package(new_id, f_trk, f_recipient, f_size, f_weight, f_cold, f_priority)
                manager.add_package_to_queue(pkg)
                st.success(f"Package {pkg.id} ({pkg.tracking_number}) added to queue.")
                st.rerun()

    with right_col:
        st.subheader(f"📋 Pending Queue ({len(manager.pending_packages)})")
        if manager.pending_packages:
            queue_data = [p.to_dict() for p in manager.pending_packages]
            st.dataframe(pd.DataFrame(queue_data), use_container_width=True)

            if st.button("🚀 Run CSP Allocation Solver", type="primary"):
                with st.spinner("Solving Constraint Satisfaction Problem..."):
                    success, metrics, unassigned = manager.process_allocation(algo_choice)
                    st.session_state.last_metrics = metrics
                    if success:
                        st.success(f"Successfully allocated {len(metrics.assignment)} packages using {metrics.algorithm_name}!")
                    else:
                        st.error(f"Solver could not satisfy all constraints. Unassigned items: {len(unassigned)}")
                    st.rerun()
        else:
            st.info("Queue is currently empty. Use the form on the left or click 'Load Sample Intake Queue' in the sidebar.")

    # Show Solver Diagnostic Metrics
    if hasattr(st.session_state, "last_metrics") and st.session_state.last_metrics:
        m = st.session_state.last_metrics
        st.markdown("---")
        st.subheader("🔍 CSP Solver Diagnostic Metrics")
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("Algorithm Used", m.algorithm_name)
        m_col2.metric("Nodes Explored", m.nodes_visited)
        m_col3.metric("Backtracks Count", m.backtracks)
        m_col4.metric("Execution Latency", f"{m.execution_time_ms:.3f} ms")


# ---------------- TAB 3: PACKAGE RETRIEVAL ----------------
with tab3:
    st.subheader("Package Retrieval / Check-Out")
    st.caption("Release compartment upon customer pickup or courier collection.")

    if manager.active_packages:
        retrieve_col1, retrieve_col2 = st.columns([2, 1])
        with retrieve_col1:
            active_options = [
                f"{pkg.id} | {pkg.tracking_number} | {pkg.recipient_name} (Locker: {pkg.assigned_locker_id})"
                for pkg in manager.active_packages.values()
            ]
            selected_option = st.selectbox("Select Package to Check-Out:", options=active_options)

        with retrieve_col2:
            st.write("")
            st.write("")
            if st.button("🔓 Check-Out & Release Locker", type="secondary"):
                pkg_id = selected_option.split(" | ")[0]
                result = manager.retrieve_package(pkg_id)
                if result:
                    pkg, locker = result
                    st.success(f"Package {pkg.id} picked up. Compartment {locker.id} is now available!")
                    st.rerun()

        st.markdown("#### Currently Stored Packages")
        stored_df = pd.DataFrame([p.to_dict() for p in manager.active_packages.values()])
        st.dataframe(stored_df, use_container_width=True)
    else:
        st.info("No packages currently stored in the facility.")


# ---------------- TAB 4: BENCHMARK ANALYTICS ----------------
with tab4:
    st.subheader("Algorithmic Performance Comparison (FOAI Empirical Study)")
    st.markdown("""
    This section evaluates the computational efficiency of the three CSP algorithms:
    1. **Pure Backtracking** (Baseline search without heuristics)
    2. **Backtracking + Forward Checking (FC)** (Pruning invalid locker options immediately)
    3. **Backtracking + FC + MRV + LCV** (Minimum Remaining Values variable ordering + Least Constraining Value)
    """)

    if os.path.exists("benchmark_results.png"):
        st.image("benchmark_results.png", caption="Empirical Evaluation of CSP Pruning Heuristics across varying Problem Sizes (N)")

    if os.path.exists("benchmark_data.csv"):
        df_bench = pd.read_csv("benchmark_data.csv")
        st.markdown("#### Empirical Benchmark Data Table")
        st.dataframe(df_bench, use_container_width=True)
        st.caption("Notice how FC + MRV achieves near O(1) backtracks even as Pure Backtracking hits exponential blowup.")


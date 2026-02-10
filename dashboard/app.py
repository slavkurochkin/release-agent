"""Streamlit dashboard for visualizing eval results.

This dashboard displays:
- Pass rate trends over time
- False GO/NO_GO rates
- Explanation quality scores
- Per-eval-type breakdowns
- Model version comparisons

Usage:
    streamlit run dashboard/app.py

The dashboard reads from either:
- Local JSON files in eval_results/ (development)
- BigQuery tables (production)
"""

from __future__ import annotations

# TODO: Implement the Streamlit dashboard.
#
# Steps:
# 1. Import streamlit and plotting libraries:
#    import streamlit as st
#    import plotly.express as px
#    import plotly.graph_objects as go
#    import pandas as pd
#    import json
#    from pathlib import Path
#
# 2. Set up the page:
#    st.set_page_config(
#        page_title="Release Agent Evals",
#        page_icon="📊",
#        layout="wide",
#    )
#    st.title("Release Risk Agent — Eval Dashboard")
#
# 3. Load eval results:
#    @st.cache_data
#    def load_results():
#        results_dir = Path("eval_results")
#        if not results_dir.exists():
#            return pd.DataFrame()
#        all_results = []
#        for f in sorted(results_dir.glob("eval_*.json")):
#            with open(f) as fh:
#                data = json.load(fh)
#                for r in data.get("results", []):
#                    r["run_id"] = data["run_id"]
#                    r["timestamp"] = data["timestamp"]
#                    all_results.append(r)
#        return pd.DataFrame(all_results)
#
# 4. Create dashboard sections:
#
#    ## Section 1: Overall Pass Rate
#    st.header("Overall Pass Rate")
#    df = load_results()
#    if df.empty:
#        st.warning("No eval results found. Run evals first.")
#        st.stop()
#    pass_rate = df["passed"].mean()
#    st.metric("Overall Pass Rate", f"{pass_rate:.1%}")
#
#    ## Section 2: Pass Rate by Eval Type
#    st.header("Pass Rate by Eval Type")
#    by_type = df.groupby("eval_type")["passed"].mean().reset_index()
#    fig = px.bar(by_type, x="eval_type", y="passed",
#                 labels={"passed": "Pass Rate"},
#                 title="Pass Rate by Evaluation Type")
#    st.plotly_chart(fig, use_container_width=True)
#
#    ## Section 3: Trend Over Time
#    st.header("Pass Rate Trend")
#    by_run = df.groupby("run_id").agg(
#        pass_rate=("passed", "mean"),
#        timestamp=("timestamp", "first"),
#    ).reset_index()
#    fig2 = px.line(by_run, x="timestamp", y="pass_rate",
#                   title="Pass Rate Over Time")
#    st.plotly_chart(fig2, use_container_width=True)
#
#    ## Section 4: Failed Checks Detail
#    st.header("Failed Checks")
#    failed = df[~df["passed"]]
#    if failed.empty:
#        st.success("All checks passed!")
#    else:
#        st.dataframe(failed[["eval_type", "eval_name", "example_id",
#                             "score", "details"]])

print("Dashboard stub — install streamlit and run: streamlit run dashboard/app.py")
print("See the TODO comments in this file for implementation guidance.")

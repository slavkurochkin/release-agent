"""Streamlit dashboard for visualizing eval results.

This dashboard displays:
- Pass rate trends over time
- False GO/NO_GO rates
- Explanation quality scores
- Per-eval-type breakdowns
- Failed checks detail

Usage:
    streamlit run dashboard/app.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Release Agent Evals", layout="wide")
st.title("Release Risk Agent -- Eval Dashboard")


@st.cache_data
def load_results():
    results_dir = Path("eval_results")
    if not results_dir.exists():
        return pd.DataFrame()
    all_results = []
    for f in sorted(results_dir.glob("eval_*.json")):
        with open(f) as fh:
            data = json.load(fh)
        metadata = data.get("metadata") or {}
        model_version = metadata.get("model", "unknown")
        for r in data.get("results", []):
            r["run_id"] = data["run_id"]
            r["timestamp"] = data["timestamp"]
            r["model_version"] = model_version
            r["run_pass_rate"] = data.get("pass_rate", None)
            r["run_false_go_rate"] = data.get("false_go_rate", None)
            all_results.append(r)
    return pd.DataFrame(all_results)


df = load_results()
if df.empty:
    st.warning("No eval results found. Run evals first: python -m release_agent.evals.runner")
    st.stop()

# ---------------------------------------------------------------------------
# Section 1: Overall Pass Rate and Trend
# ---------------------------------------------------------------------------
st.metric("Overall Pass Rate", f"{df['passed'].mean():.1%}")

by_run = df.groupby("run_id").agg(
    pass_rate=("passed", "mean"),
    timestamp=("timestamp", "first"),
).reset_index()
fig = px.line(
    by_run.sort_values("timestamp"),
    x="timestamp",
    y="pass_rate",
    title="Pass Rate Over Time",
    labels={"pass_rate": "Pass Rate", "timestamp": "Date"},
)
fig.update_yaxes(range=[0, 1])
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Section 2: Pass Rate by Eval Type (Bar Chart)
# ---------------------------------------------------------------------------
st.header("Pass Rate by Eval Type")
by_type = df.groupby("eval_type")["passed"].mean().reset_index()
by_type.columns = ["eval_type", "pass_rate"]
fig2 = px.bar(
    by_type,
    x="eval_type",
    y="pass_rate",
    title="Pass Rate by Evaluation Type",
    labels={"pass_rate": "Pass Rate", "eval_type": "Eval Type"},
)
fig2.update_yaxes(range=[0, 1])
st.plotly_chart(fig2, use_container_width=True)

# ---------------------------------------------------------------------------
# Section 3: Score Distribution (Histogram)
# ---------------------------------------------------------------------------
st.header("Explanation Quality Scores")
scored = df[df["score"] > 0]
if not scored.empty:
    fig3 = px.histogram(
        scored,
        x="score",
        nbins=20,
        title="Score Distribution",
        labels={"score": "Score", "count": "Count"},
    )
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("No scored results available.")

# ---------------------------------------------------------------------------
# Section 4: Failed Checks Detail (latest run only)
# ---------------------------------------------------------------------------
st.header("Failed Checks (latest run)")
latest_run = df.sort_values("timestamp").iloc[-1]["run_id"]
latest_df = df[df["run_id"] == latest_run]
failed = latest_df[~latest_df["passed"]]
if failed.empty:
    st.success("All checks passed!")
else:
    st.dataframe(
        failed[["eval_type", "eval_name", "example_id", "score", "details"]].reset_index(drop=True),
        use_container_width=True,
    )

# ---------------------------------------------------------------------------
# Section 5: Model Comparison
# ---------------------------------------------------------------------------
st.header("Model Comparison")

models = sorted(df["model_version"].dropna().unique().tolist())

if len(models) < 2:
    st.info(
        f"Only one model version found (`{models[0] if models else 'none'}`). "
        "Run evals with a different model to enable comparison."
    )
else:
    col1, col2 = st.columns(2)
    with col1:
        model_a = st.selectbox("Model A", models, index=0)
    with col2:
        model_b = st.selectbox("Model B", models, index=min(1, len(models) - 1))

    def compute_metrics(model_df: pd.DataFrame) -> dict:
        # Use the latest run for this model to get report-level metrics
        latest = model_df.sort_values("timestamp").iloc[-1]
        return {
            "Pass Rate": f"{model_df['passed'].mean():.1%}",
            "Avg Score": f"{model_df['score'].mean():.3f}",
            "False GO Rate": f"{latest['run_false_go_rate']:.1%}" if latest["run_false_go_rate"] is not None else "n/a",
            "Total Checks": len(model_df),
            "Failed Checks": int((~model_df["passed"]).sum()),
        }

    df_a = df[df["model_version"] == model_a]
    df_b = df[df["model_version"] == model_b]

    comparison = pd.DataFrame({model_a: compute_metrics(df_a), model_b: compute_metrics(df_b)})
    st.table(comparison)

    # Per-eval-type pass rate breakdown
    st.subheader("Pass Rate by Eval Type")
    by_type_a = df_a.groupby("eval_type")["passed"].mean().rename(model_a)
    by_type_b = df_b.groupby("eval_type")["passed"].mean().rename(model_b)
    type_comparison = pd.concat([by_type_a, by_type_b], axis=1).fillna(0)
    fig5 = px.bar(
        type_comparison.reset_index().melt(id_vars="eval_type", var_name="model", value_name="pass_rate"),
        x="eval_type",
        y="pass_rate",
        color="model",
        barmode="group",
        labels={"pass_rate": "Pass Rate", "eval_type": "Eval Type", "model": "Model"},
    )
    fig5.update_yaxes(range=[0, 1])
    st.plotly_chart(fig5, use_container_width=True)

    # Per-example decision comparison (functional evals only)
    st.subheader("Decision Match by Example")
    decision_a = (
        df_a[df_a["eval_name"] == "decision_match"]
        .groupby("example_id")["passed"]
        .mean()
        .rename(model_a)
    )
    decision_b = (
        df_b[df_b["eval_name"] == "decision_match"]
        .groupby("example_id")["passed"]
        .mean()
        .rename(model_b)
    )
    decision_cmp = pd.concat([decision_a, decision_b], axis=1).fillna(0).reset_index()
    fig6 = px.bar(
        decision_cmp.melt(id_vars="example_id", var_name="model", value_name="pass_rate"),
        x="example_id",
        y="pass_rate",
        color="model",
        barmode="group",
        labels={"pass_rate": "Decision Match", "example_id": "Example", "model": "Model"},
    )
    fig6.update_yaxes(range=[0, 1])
    fig6.update_xaxes(tickangle=30)
    st.plotly_chart(fig6, use_container_width=True)

"""Eval result storage for persisting results to BigQuery.

This module handles storing evaluation results in BigQuery so they can
be tracked over time. This enables:
- Tracking eval pass rates across model versions
- Detecting regressions when prompts or models change
- Building dashboards showing quality trends
- Comparing different agent configurations

BigQuery schema:
    eval_results (table)
    ├── run_id: STRING (UUID for each eval run)
    ├── timestamp: TIMESTAMP
    ├── model_version: STRING (e.g., "gpt-4o-2024-01-25")
    ├── eval_type: STRING (functional, semantic, judge, adversarial)
    ├── eval_name: STRING (specific check name)
    ├── example_id: STRING (gold example identifier)
    ├── passed: BOOLEAN
    ├── score: FLOAT
    ├── details: STRING
    └── metadata: JSON (additional context)

Usage:
    storage = BigQueryEvalStorage(project_id="my-project", dataset="evals")
    await storage.store_results(report)
    trends = await storage.get_pass_rate_trend(days=30)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from release_agent.evals.runner import EvalReport

# ---------------------------------------------------------------------------
# Local File Storage (development fallback)
# ---------------------------------------------------------------------------


class LocalEvalStorage:
    """Stores eval results as JSON files locally.

    This is the development-mode storage backend. Results are saved to
    the eval_results/ directory as timestamped JSON files. Simple but
    sufficient for local development and CI.
    """

    def __init__(self, output_dir: str | Path = "eval_results") -> None:
        """Initialize with output directory.

        Args:
            output_dir: Directory to store result files
        """
        self._output_dir = Path(output_dir)

    async def store_report(self, report: EvalReport) -> str:
        """Store an eval report as a JSON file.

        Args:
            report: The eval report to store

        Returns:
            Path to the saved file
        """
        # TODO: Implement local storage.
        #
        # Steps:
        # 1. Create the output directory:
        #    self._output_dir.mkdir(parents=True, exist_ok=True)
        #
        # 2. Generate a filename:
        #    run_id = uuid.uuid4().hex[:8]
        #    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        #    filename = f"eval_{timestamp}_{run_id}.json"
        #
        # 3. Convert report to dict and save:
        #    filepath = self._output_dir / filename
        #    data = {
        #        "run_id": run_id,
        #        "timestamp": report.timestamp,
        #        "total_examples": report.total_examples,
        #        "pass_rate": report.pass_rate,
        #        "false_go_rate": report.false_go_rate,
        #        "results": [
        #            {
        #                "eval_type": r.eval_type,
        #                "eval_name": r.eval_name,
        #                "passed": r.passed,
        #                "score": r.score,
        #                "details": r.details,
        #                "example_id": r.example_id,
        #            }
        #            for r in report.results
        #        ],
        #        "metadata": report.metadata,
        #    }
        #    with open(filepath, "w") as f:
        #        json.dump(data, f, indent=2)
        #
        # 4. Return the filepath:
        #    return str(filepath)
        raise NotImplementedError("TODO: Implement local eval storage")


# ---------------------------------------------------------------------------
# BigQuery Storage (production)
# ---------------------------------------------------------------------------


class BigQueryEvalStorage:
    """Stores eval results in BigQuery for production tracking.

    Requires:
    - google-cloud-bigquery package
    - GCP project with BigQuery dataset created
    - Service account with BigQuery write permissions

    The table is auto-created on first write if it doesn't exist.
    """

    def __init__(
        self,
        project_id: str | None = None,
        dataset: str = "release_agent_evals",
        table: str = "eval_results",
    ) -> None:
        """Initialize BigQuery storage.

        Args:
            project_id: GCP project ID. Reads from GCP_PROJECT_ID env var if None.
            dataset: BigQuery dataset name
            table: BigQuery table name
        """
        # TODO: Initialize BigQuery client.
        #
        # Steps:
        # 1. Resolve project_id from env var if not provided
        # 2. Store dataset and table names
        # 3. Initialize the BigQuery client:
        #    from google.cloud import bigquery
        #    self._client = bigquery.Client(project=project_id)
        #    self._table_ref = f"{project_id}.{dataset}.{table}"
        self._project_id = project_id
        self._dataset = dataset
        self._table = table

    async def store_report(self, report: EvalReport) -> str:
        """Store eval results as rows in BigQuery.

        Each EvalResult becomes one row in the table. This makes it easy
        to query individual checks, aggregate by type, etc.

        Args:
            report: The eval report to store

        Returns:
            The run_id for this eval run
        """
        # TODO: Implement BigQuery storage.
        #
        # Steps:
        # 1. Generate a run_id:
        #    run_id = uuid.uuid4().hex
        #
        # 2. Convert results to BigQuery rows:
        #    rows = [
        #        {
        #            "run_id": run_id,
        #            "timestamp": report.timestamp,
        #            "model_version": report.metadata.get("model", "unknown"),
        #            "eval_type": r.eval_type,
        #            "eval_name": r.eval_name,
        #            "example_id": r.example_id,
        #            "passed": r.passed,
        #            "score": r.score,
        #            "details": r.details,
        #            "metadata": json.dumps(report.metadata),
        #        }
        #        for r in report.results
        #    ]
        #
        # 3. Insert rows:
        #    errors = self._client.insert_rows_json(self._table_ref, rows)
        #    if errors:
        #        raise RuntimeError(f"BigQuery insert errors: {errors}")
        #
        # 4. Return run_id
        raise NotImplementedError("TODO: Implement BigQuery eval storage")

    async def get_pass_rate_trend(
        self,
        days: int = 30,
        eval_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query pass rate trend over time.

        Args:
            days: Number of days to look back
            eval_type: Filter by eval type (optional)

        Returns:
            List of dicts with date, pass_rate, total_checks
        """
        # TODO: Implement trend query.
        #
        # SQL:
        #   SELECT
        #     DATE(timestamp) as date,
        #     COUNTIF(passed) / COUNT(*) as pass_rate,
        #     COUNT(*) as total_checks
        #   FROM `{table_ref}`
        #   WHERE timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
        #   GROUP BY date
        #   ORDER BY date
        raise NotImplementedError("TODO: Implement pass rate trend query")

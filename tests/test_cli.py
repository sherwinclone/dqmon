"""Tests for dqmon CLI exit codes."""

import json
from pathlib import Path

from typer.testing import CliRunner

from dqmon.cli import app


runner = CliRunner()


def _write_project(project_dir: Path, nodes: dict) -> None:
    target = project_dir / "target"
    target.mkdir(parents=True)
    manifest = {
        "metadata": {"project_name": "exit_codes"},
        "nodes": nodes,
        "sources": {},
    }
    (target / "manifest.json").write_text(json.dumps(manifest))


def _model(name: str, *, description: str) -> dict:
    return {
        "resource_type": "model",
        "name": name,
        "unique_id": f"model.exit_codes.{name}",
        "schema": "analytics",
        "description": description,
        "columns": {
            "id": {
                "name": "id",
                "data_type": "integer",
                "description": "Primary key",
            }
        },
        "config": {"materialized": "view"},
        "depends_on": {"nodes": []},
    }


def _pk_tests(model_name: str) -> dict:
    nodes = {}
    for test_type in ("not_null", "unique"):
        test_name = f"{test_type}_{model_name}_id"
        nodes[f"test.exit_codes.{test_name}"] = {
            "resource_type": "test",
            "name": test_name,
            "unique_id": f"test.exit_codes.{test_name}",
            "test_metadata": {"name": test_type},
            "column_name": "id",
            "depends_on": {"nodes": [f"model.exit_codes.{model_name}"]},
        }
    return nodes


def _clean_nodes() -> dict:
    nodes = {"model.exit_codes.fct_clean": _model("fct_clean", description="Clean fact")}
    nodes.update(_pk_tests("fct_clean"))
    return nodes


def _warning_nodes() -> dict:
    nodes = {
        "model.exit_codes.fct_warn": _model("fct_warn", description=""),
    }
    nodes.update(_pk_tests("fct_warn"))
    return nodes


def _failure_nodes() -> dict:
    return {
        "model.exit_codes.fct_fail": _model("fct_fail", description="Missing tests"),
    }


def test_report_clean_run_exits_zero(tmp_path):
    project = tmp_path / "proj"
    _write_project(project, _clean_nodes())

    result = runner.invoke(app, ["report", str(project)])

    assert result.exit_code == 0


def test_report_clean_run_exits_zero_with_fail_on_warnings(tmp_path):
    project = tmp_path / "proj"
    _write_project(project, _clean_nodes())

    result = runner.invoke(app, ["report", str(project), "--fail-on-warnings"])

    assert result.exit_code == 0


def test_report_failure_exits_nonzero(tmp_path):
    project = tmp_path / "proj"
    _write_project(project, _failure_nodes())
    output = tmp_path / "dqmon-report.md"

    result = runner.invoke(
        app, ["report", str(project), "--output", str(output)]
    )

    assert result.exit_code == 1
    assert output.exists()
    assert "| 1 failed" in output.read_text()


def test_report_warnings_exit_zero_without_fail_on_warnings(tmp_path):
    project = tmp_path / "proj"
    _write_project(project, _warning_nodes())

    result = runner.invoke(app, ["report", str(project)])

    assert result.exit_code == 0


def test_report_warnings_exit_nonzero_with_fail_on_warnings(tmp_path):
    project = tmp_path / "proj"
    _write_project(project, _warning_nodes())
    output = tmp_path / "dqmon-report.md"

    result = runner.invoke(
        app,
        ["report", str(project), "--output", str(output), "--fail-on-warnings"],
    )

    assert result.exit_code == 1
    assert output.exists()
    text = output.read_text()
    assert "| 0 failed" in text
    assert "| 1 warnings" in text

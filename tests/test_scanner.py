"""Tests for dqmon scanner module."""

import json
from pathlib import Path

from dqmon.scanner import scan_dbt_project, Model, Source, Test


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_scan_project_name():
    project = scan_dbt_project(FIXTURES_DIR / "manifest.json")
    assert project.name == "jaffle_shop"


def test_scan_models_count():
    project = scan_dbt_project(FIXTURES_DIR / "manifest.json")
    assert len(project.models) == 4


def test_scan_sources_count():
    project = scan_dbt_project(FIXTURES_DIR / "manifest.json")
    assert len(project.sources) == 2


def test_scan_tests_count():
    project = scan_dbt_project(FIXTURES_DIR / "manifest.json")
    assert len(project.tests) == 3


def test_model_has_columns():
    project = scan_dbt_project(FIXTURES_DIR / "manifest.json")
    fct_orders = next(m for m in project.models if m.name == "fct_orders")
    assert len(fct_orders.columns) == 4
    col_names = {c.name for c in fct_orders.columns}
    assert "order_id" in col_names
    assert "amount" in col_names


def test_model_has_tests_flag():
    project = scan_dbt_project(FIXTURES_DIR / "manifest.json")
    stg_customers = next(m for m in project.models if m.name == "stg_customers")
    stg_orders = next(m for m in project.models if m.name == "stg_orders")
    assert stg_customers.has_tests is True
    assert stg_orders.has_tests is False


def test_model_materialization():
    project = scan_dbt_project(FIXTURES_DIR / "manifest.json")
    fct_orders = next(m for m in project.models if m.name == "fct_orders")
    stg_customers = next(m for m in project.models if m.name == "stg_customers")
    assert fct_orders.materialization == "table"
    assert stg_customers.materialization == "view"


def test_model_depends_on():
    project = scan_dbt_project(FIXTURES_DIR / "manifest.json")
    fct_orders = next(m for m in project.models if m.name == "fct_orders")
    assert len(fct_orders.depends_on) == 2


def test_source_freshness():
    project = scan_dbt_project(FIXTURES_DIR / "manifest.json")
    customers_source = next(s for s in project.sources if "customers" in s.name)
    orders_source = next(s for s in project.sources if "orders" in s.name)
    assert customers_source.freshness_warn_after is not None
    assert orders_source.loaded_at_field is None


def test_models_sorted_by_name():
    project = scan_dbt_project(FIXTURES_DIR / "manifest.json")
    names = [m.name for m in project.models]
    assert names == sorted(names)


def test_empty_manifest(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "metadata": {"project_name": "empty"},
        "nodes": {},
        "sources": {},
    }))
    project = scan_dbt_project(manifest)
    assert project.name == "empty"
    assert len(project.models) == 0
    assert len(project.sources) == 0
    assert len(project.tests) == 0

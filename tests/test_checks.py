"""Tests for dqmon checks module."""

from pathlib import Path

from dqmon.scanner import scan_dbt_project
from dqmon.checks import run_checks, CheckResult


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _get_results_by_check(results: list[CheckResult], check_name: str) -> list[CheckResult]:
    return [r for r in results if r.check_name == check_name]


def _get_results_by_model(results: list[CheckResult], model_name: str) -> list[CheckResult]:
    return [r for r in results if r.model_name == model_name]


def test_run_checks_returns_results():
    project = scan_dbt_project(FIXTURES_DIR / "manifest.json")
    results = run_checks(project)
    assert len(results) > 0
    assert all(isinstance(r, CheckResult) for r in results)


def test_all_statuses_present():
    project = scan_dbt_project(FIXTURES_DIR / "manifest.json")
    results = run_checks(project)
    statuses = {r.status for r in results}
    assert "pass" in statuses
    assert "warn" in statuses
    assert "fail" in statuses


def test_documented_model_passes():
    project = scan_dbt_project(FIXTURES_DIR / "manifest.json")
    results = run_checks(project)
    desc_results = _get_results_by_check(results, "model_has_description")
    fct = next(r for r in desc_results if r.model_name == "fct_orders")
    assert fct.status == "pass"


def test_undocumented_model_warns():
    project = scan_dbt_project(FIXTURES_DIR / "manifest.json")
    results = run_checks(project)
    desc_results = _get_results_by_check(results, "model_has_description")
    stg_orders = next(r for r in desc_results if r.model_name == "stg_orders")
    assert stg_orders.status == "warn"


def test_untested_model_fails():
    project = scan_dbt_project(FIXTURES_DIR / "manifest.json")
    results = run_checks(project)
    test_results = _get_results_by_check(results, "has_tests")
    stg_orders = next(r for r in test_results if r.model_name == "stg_orders")
    assert stg_orders.status == "fail"


def test_tested_model_with_pk_passes():
    project = scan_dbt_project(FIXTURES_DIR / "manifest.json")
    results = run_checks(project)
    test_results = _get_results_by_check(results, "has_tests")
    stg_customers = next(r for r in test_results if r.model_name == "stg_customers")
    assert stg_customers.status == "pass"


def test_low_column_documentation_fails():
    project = scan_dbt_project(FIXTURES_DIR / "manifest.json")
    results = run_checks(project)
    col_results = _get_results_by_check(results, "columns_documented")
    stg_orders = next(r for r in col_results if r.model_name == "stg_orders")
    assert stg_orders.status == "fail"  # 25% < 50% threshold


def test_full_column_documentation_passes():
    project = scan_dbt_project(FIXTURES_DIR / "manifest.json")
    results = run_checks(project)
    col_results = _get_results_by_check(results, "columns_documented")
    fct = next(r for r in col_results if r.model_name == "fct_orders")
    assert fct.status == "pass"  # 100%


def test_orphan_model_detected():
    project = scan_dbt_project(FIXTURES_DIR / "manifest.json")
    results = run_checks(project)
    orphan_results = _get_results_by_check(results, "orphan_model")
    orphan_names = [r.model_name for r in orphan_results]
    assert "unused_model" in orphan_names


def test_naming_convention_warning():
    project = scan_dbt_project(FIXTURES_DIR / "manifest.json")
    results = run_checks(project)
    naming_results = _get_results_by_check(results, "naming_convention")
    bad_names = [r.model_name for r in naming_results if r.status == "warn"]
    assert "unused_model" in bad_names


def test_source_freshness_pass():
    project = scan_dbt_project(FIXTURES_DIR / "manifest.json")
    results = run_checks(project)
    fresh_results = _get_results_by_check(results, "source_freshness")
    customers = next(r for r in fresh_results if "customers" in r.model_name)
    assert customers.status == "pass"


def test_source_freshness_warn():
    project = scan_dbt_project(FIXTURES_DIR / "manifest.json")
    results = run_checks(project)
    fresh_results = _get_results_by_check(results, "source_freshness")
    orders = next(r for r in fresh_results if "orders" in r.model_name)
    assert orders.status == "warn"


def test_check_result_counts():
    project = scan_dbt_project(FIXTURES_DIR / "manifest.json")
    results = run_checks(project)
    failed = sum(1 for r in results if r.status == "fail")
    warned = sum(1 for r in results if r.status == "warn")
    passed = sum(1 for r in results if r.status == "pass")
    assert failed == 3
    assert warned == 9
    assert passed == 5

"""Zero-config data quality checks for dbt projects."""

from dataclasses import dataclass
from typing import Optional

from dqmon.scanner import DbtProject, Model


@dataclass
class CheckResult:
    check_name: str
    model_name: str
    status: str  # "pass", "warn", "fail"
    message: str
    details: Optional[str] = None


def run_checks(project: DbtProject, verbose: bool = False) -> list[CheckResult]:
    """Run all quality checks against the dbt project metadata."""
    results = []

    for model in project.models:
        results.extend(_check_model_documentation(model))
        results.extend(_check_column_documentation(model))
        results.extend(_check_test_coverage(model, project))
        results.extend(_check_materialization(model))
        results.extend(_check_naming_conventions(model))

    for source in project.sources:
        results.extend(_check_source_freshness_config(source))

    results.extend(_check_orphan_models(project))

    return results


def _check_model_documentation(model: Model) -> list[CheckResult]:
    """Check if model has a description."""
    if not model.description or model.description.strip() == "":
        return [CheckResult(
            check_name="model_has_description",
            model_name=model.name,
            status="warn",
            message=f"Model `{model.name}` has no description",
            details="Add a description in your schema.yml to help teammates understand this model.",
        )]
    return [CheckResult(
        check_name="model_has_description",
        model_name=model.name,
        status="pass",
        message=f"Model `{model.name}` is documented",
    )]


def _check_column_documentation(model: Model) -> list[CheckResult]:
    """Check if columns have descriptions."""
    if not model.columns:
        return [CheckResult(
            check_name="columns_documented",
            model_name=model.name,
            status="warn",
            message=f"Model `{model.name}` has no column definitions in schema.yml",
        )]

    undocumented = [c for c in model.columns if not c.description or c.description.strip() == ""]
    total = len(model.columns)
    documented = total - len(undocumented)
    pct = (documented / total * 100) if total > 0 else 0

    if pct < 50:
        status = "fail"
    elif pct < 80:
        status = "warn"
    else:
        status = "pass"

    return [CheckResult(
        check_name="columns_documented",
        model_name=model.name,
        status=status,
        message=f"Model `{model.name}`: {documented}/{total} columns documented ({pct:.0f}%)",
        details=", ".join(c.name for c in undocumented[:5]) if undocumented else None,
    )]


def _check_test_coverage(model: Model, project: DbtProject) -> list[CheckResult]:
    """Check if model has tests defined."""
    model_tests = [t for t in project.tests if t.depends_on_model == model.unique_id]

    if not model_tests:
        return [CheckResult(
            check_name="has_tests",
            model_name=model.name,
            status="fail",
            message=f"Model `{model.name}` has NO tests",
            details="Add at least not_null and unique tests for primary key columns.",
        )]

    # Check for primary key tests (not_null + unique)
    has_not_null = any(t.test_type == "not_null" for t in model_tests)
    has_unique = any(t.test_type == "unique" for t in model_tests)

    if has_not_null and has_unique:
        status = "pass"
        msg = f"Model `{model.name}` has {len(model_tests)} tests (includes PK tests)"
    elif len(model_tests) > 0:
        status = "warn"
        msg = f"Model `{model.name}` has {len(model_tests)} tests but missing PK tests (not_null + unique)"
    else:
        status = "fail"
        msg = f"Model `{model.name}` has no tests"

    return [CheckResult(
        check_name="has_tests",
        model_name=model.name,
        status=status,
        message=msg,
    )]


def _check_materialization(model: Model) -> list[CheckResult]:
    """Flag potentially expensive materializations."""
    if model.materialization == "table" and len(model.depends_on) == 0:
        return [CheckResult(
            check_name="materialization",
            model_name=model.name,
            status="warn",
            message=f"Model `{model.name}` is materialized as table with no upstream dependencies",
            details="Consider if this should be a view or seed instead.",
        )]
    return []


def _check_naming_conventions(model: Model) -> list[CheckResult]:
    """Check basic naming conventions."""
    results = []

    # Check model name uses snake_case
    if model.name != model.name.lower():
        results.append(CheckResult(
            check_name="naming_convention",
            model_name=model.name,
            status="warn",
            message=f"Model `{model.name}` is not snake_case",
        ))

    # Check for common prefixes (stg_, int_, fct_, dim_)
    known_prefixes = ("stg_", "int_", "fct_", "dim_", "base_", "src_", "rpt_", "mart_")
    if not model.name.startswith(known_prefixes) and model.materialization != "ephemeral":
        results.append(CheckResult(
            check_name="naming_convention",
            model_name=model.name,
            status="warn",
            message=f"Model `{model.name}` doesn't follow common naming conventions (stg_/int_/fct_/dim_)",
            details="Consider prefixing with a layer indicator for better organization.",
        ))

    return results


def _check_source_freshness_config(source) -> list[CheckResult]:
    """Check if sources have freshness configured."""
    if source.loaded_at_field and not source.freshness_warn_after:
        return [CheckResult(
            check_name="source_freshness",
            model_name=source.name,
            status="warn",
            message=f"Source `{source.name}` has loaded_at_field but no freshness thresholds",
            details="Add warn_after and error_after to your source freshness config.",
        )]

    if not source.loaded_at_field:
        return [CheckResult(
            check_name="source_freshness",
            model_name=source.name,
            status="warn",
            message=f"Source `{source.name}` has no freshness tracking configured",
        )]

    return [CheckResult(
        check_name="source_freshness",
        model_name=source.name,
        status="pass",
        message=f"Source `{source.name}` has freshness tracking configured",
    )]


def _check_orphan_models(project: DbtProject) -> list[CheckResult]:
    """Check for models that nothing depends on (potential dead code)."""
    all_dependencies = set()
    for model in project.models:
        all_dependencies.update(model.depends_on)

    model_ids = {m.unique_id for m in project.models}
    referenced = model_ids & all_dependencies
    orphans = model_ids - all_dependencies

    # Filter: only flag non-mart/non-report models as orphans
    results = []
    for model in project.models:
        if model.unique_id in orphans:
            # End models (marts, reports) are expected to be leaf nodes
            if model.name.startswith(("fct_", "dim_", "rpt_", "mart_")):
                continue
            if model.materialization in ("ephemeral",):
                continue
            results.append(CheckResult(
                check_name="orphan_model",
                model_name=model.name,
                status="warn",
                message=f"Model `{model.name}` is not referenced by any other model",
                details="This might be dead code. If it's an end-user model, prefix with fct_/dim_/rpt_.",
            ))

    return results

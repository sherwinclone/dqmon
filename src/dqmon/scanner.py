"""Scan dbt manifest.json and extract project metadata."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Column:
    name: str
    data_type: Optional[str] = None
    description: Optional[str] = None


@dataclass
class Model:
    name: str
    unique_id: str
    schema_name: Optional[str] = None
    database: Optional[str] = None
    columns: list[Column] = field(default_factory=list)
    has_tests: bool = False
    depends_on: list[str] = field(default_factory=list)
    materialization: Optional[str] = None
    description: Optional[str] = None


@dataclass
class Source:
    name: str
    unique_id: str
    schema_name: Optional[str] = None
    database: Optional[str] = None
    loaded_at_field: Optional[str] = None
    freshness_warn_after: Optional[dict] = None
    freshness_error_after: Optional[dict] = None


@dataclass
class Test:
    name: str
    unique_id: str
    test_type: str  # "generic" or "singular"
    depends_on_model: Optional[str] = None
    column_name: Optional[str] = None


@dataclass
class DbtProject:
    name: str
    models: list[Model] = field(default_factory=list)
    sources: list[Source] = field(default_factory=list)
    tests: list[Test] = field(default_factory=list)


def scan_dbt_project(manifest_path: Path) -> DbtProject:
    """Parse manifest.json and return structured project data."""
    with open(manifest_path) as f:
        manifest = json.load(f)

    metadata = manifest.get("metadata", {})
    project_name = metadata.get("project_name", metadata.get("project_id", "unknown"))

    models = _extract_models(manifest)
    sources = _extract_sources(manifest)
    tests = _extract_tests(manifest)

    # Mark models that have tests
    tested_models = set()
    for test in tests:
        if test.depends_on_model:
            tested_models.add(test.depends_on_model)
    for model in models:
        model.has_tests = model.unique_id in tested_models

    return DbtProject(
        name=project_name,
        models=models,
        sources=sources,
        tests=tests,
    )


def _extract_models(manifest: dict) -> list[Model]:
    """Extract models from manifest nodes."""
    models = []
    nodes = manifest.get("nodes", {})

    for node_id, node in nodes.items():
        if node.get("resource_type") != "model":
            continue

        columns = [
            Column(
                name=col_name,
                data_type=col_data.get("data_type"),
                description=col_data.get("description"),
            )
            for col_name, col_data in node.get("columns", {}).items()
        ]

        config = node.get("config", {})
        depends = node.get("depends_on", {}).get("nodes", [])

        models.append(Model(
            name=node.get("name", ""),
            unique_id=node_id,
            schema_name=node.get("schema"),
            database=node.get("database"),
            columns=columns,
            depends_on=depends,
            materialization=config.get("materialized"),
            description=node.get("description"),
        ))

    return sorted(models, key=lambda m: m.name)


def _extract_sources(manifest: dict) -> list[Source]:
    """Extract sources from manifest."""
    sources = []
    source_nodes = manifest.get("sources", {})

    for source_id, source in source_nodes.items():
        freshness = source.get("freshness", {}) or {}
        sources.append(Source(
            name=f"{source.get('source_name', '')}.{source.get('name', '')}",
            unique_id=source_id,
            schema_name=source.get("schema"),
            database=source.get("database"),
            loaded_at_field=source.get("loaded_at_field"),
            freshness_warn_after=freshness.get("warn_after"),
            freshness_error_after=freshness.get("error_after"),
        ))

    return sorted(sources, key=lambda s: s.name)


def _extract_tests(manifest: dict) -> list[Test]:
    """Extract tests from manifest nodes."""
    tests = []
    nodes = manifest.get("nodes", {})

    for node_id, node in nodes.items():
        if node.get("resource_type") != "test":
            continue

        depends_on = node.get("depends_on", {}).get("nodes", [])
        model_ref = None
        for dep in depends_on:
            if dep.startswith("model."):
                model_ref = dep
                break

        tests.append(Test(
            name=node.get("name", ""),
            unique_id=node_id,
            test_type=node.get("test_metadata", {}).get("name", "singular"),
            depends_on_model=model_ref,
            column_name=node.get("column_name"),
        ))

    return tests

# dqmon

Zero-config data quality monitoring for dbt projects. **pytest for your data.**

```bash
pip install dqmon
dqmon init          # auto-detect dbt project
dqmon check         # run quality checks
dqmon report        # generate quality report
```

## What it checks

- Model documentation coverage
- Column documentation coverage
- Test coverage (not_null, unique on primary keys)
- Source freshness configuration
- Naming conventions (stg_/int_/fct_/dim_ prefixes)
- Orphan models (potential dead code)
- Materialization sanity checks

## Zero config required

dqmon reads your existing `target/manifest.json` — no additional YAML, no new config files, no account needed.

## GitHub Action

```yaml
- uses: sherwinclone/dqmon@master
  id: dqmon
  with:
    dbt-project-path: .
    fail-on-warnings: false
```

`dqmon report` exits 0 when every check passes. It exits 1 when any check fails. Warnings exit 1 only when `fail-on-warnings` is `true`. The action step uses that exit code, so the job fails on the same conditions. Counts are still published when the step fails.

| Output | Meaning |
| --- | --- |
| `passed` | Number of checks that passed |
| `warnings` | Number of checks that warned |
| `failed` | Number of checks that failed |
| `report` | Path to the markdown report (`dqmon-report.md`), or empty if it was not written |

```yaml
- run: echo "${{ steps.dqmon.outputs.passed }} passed, ${{ steps.dqmon.outputs.failed }} failed"
```

## License

MIT

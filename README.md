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

## License

MIT

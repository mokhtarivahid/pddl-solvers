# Tests

Two test scripts live in this directory. Run them from the repo root.

## Analysis tests

Validate the PDDL analyzer, capability catalog, and planner matching:

```bash
python tests/test_analysis.py            # full suite
python tests/test_analysis.py --quick    # skip heavy domain scans
```

## Planner execution tests

Run planners against IPC benchmark problems:

```bash
python tests/run_tests.py --quick                  # smoke test
python tests/run_tests.py --planners ff downward   # specific planners
python tests/run_tests.py --timeout 120            # full suite
```

Reports and JSON results are written to `tests/results/`.

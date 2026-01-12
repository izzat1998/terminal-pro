---
name: test
description: Run tests for the MTT Container Terminal project
---

# Test Skill

Run tests for the MTT Container Terminal project.

## When to Use This Skill

Claude should invoke this skill when:
- User asks to run tests
- After making code changes that need verification
- User reports test failures
- Before committing code

## Backend Tests (pytest)

Run all backend tests:
```bash
cd backend && pytest -v
```

With coverage:
```bash
cd backend && pytest --cov=apps --cov-report=term-missing
```

Run specific test file:
```bash
cd backend && pytest tests/terminal_operations/test_api.py -v
```

Filter by name pattern:
```bash
cd backend && pytest -k "container" -v
```

## Test Markers

```bash
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests only
pytest -m "not slow"     # Skip slow tests
```

## Quick Reference

| Command | Description |
|---------|-------------|
| `pytest` | All tests |
| `pytest -v` | Verbose output |
| `pytest -x` | Stop on first failure |
| `pytest --lf` | Rerun last failed |
| `pytest -k "name"` | Filter by name pattern |
| `pytest --cov=apps` | With coverage |

## Frontend Tests

Run frontend tests:
```bash
cd frontend && npm run test
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| ModuleNotFoundError | Activate venv: `source .venv/bin/activate` |
| Database errors | Run migrations: `python manage.py migrate` |
| Fixture not found | Check `tests/conftest.py` |
| Import errors | Verify `PYTHONPATH` includes project root |

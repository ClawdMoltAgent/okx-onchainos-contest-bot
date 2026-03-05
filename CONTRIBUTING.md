# Contributing

Thanks for contributing.

## Development
1. Create a virtual env and install deps:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e . pytest
   ```
2. Run tests:
   ```bash
   pytest -q
   ```

## Branch & PR rules
- Use feature branches: `feat/*`, `fix/*`, `docs/*`.
- Keep PRs small and focused.
- Fill PR template checklist.
- Never commit secrets (`.env`, private keys, API keys).

## Safety
- Any change to execution/risk logic must include:
  - tests (or explicit rationale)
  - docs update (`docs/STRATEGY.md` or `docs/FLOW.md`)
  - rollback plan for live trading impact

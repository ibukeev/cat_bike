# Tests

Use this area for verification.

- `manual/` - checklists for bench tests, bike installation checks, night tests, and playa readiness.
- `automated/` - tests for any scripts, pattern transforms, generated files, or configuration validators.

Run the cat-head configuration checks with
`python3 -m unittest discover -s tests/automated -p 'test_*.py'`. Use
`manual/cat-head-lighting-gates.md` for physical coupon and integration gates.

Document the exact hardware setup used for manual tests.

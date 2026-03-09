# OpenClaw Development Workflow

## Branching Rule

The active development workflow is:

1. branch from `main`
2. make the change
3. validate locally
4. merge back into `main`
5. push `main`

Recommended branch naming:

- `feature/<topic>`
- `fix/<topic>`
- `docs/<topic>`

## Validation Rule

For code changes, validate at least the relevant subset of:

```bash
python3 -m compileall app tests
docker compose run --rm openclaw python -m unittest discover -s tests -v
docker compose run --rm openclaw python -m app.cli doctor
```

For pipeline-affecting changes, run a smoke flow such as:

```bash
docker compose run --rm openclaw python -m app.cli initdb
docker compose run --rm openclaw python -m app.cli collect-ebay "walking pad" --demo --limit 5
docker compose run --rm openclaw python -m app.cli normalize-listings
docker compose run --rm openclaw python -m app.cli cluster-products
docker compose run --rm openclaw python -m app.cli score-products
docker compose run --rm openclaw python -m app.cli top-products --limit 10
```

## Source Integration Pattern

When adding a new marketplace:

- create a source-specific module under `app/sources/`
- add a source-specific CLI command
- map provider payloads into the shared raw listing contract
- do not overload `collect-ebay` to represent multiple providers

Good examples:

- `app/sources/amazon.py`
- `app/sources/etsy.py`
- `app/sources/tiktok.py`
- `collect-amazon`
- `collect-etsy`
- `collect-tiktok`

## Keep The Downstream Stable

Changes should preserve:

- `raw_listings` compatibility
- normalization inputs
- cluster scoring inputs
- reporting contracts where practical

Avoid redesigning the stack around a provider abstraction that forces all sources into one generic collector.

## Database Change Rule

The project currently relies on `initdb` for additive schema updates.

That means:

- additive tables are created through `Base.metadata.create_all()`
- additive columns used by newer features are added through the initdb compatibility path
- destructive or rename-style changes should be treated carefully
- documentation should note when `initdb` must be rerun

If schema changes become frequent or more invasive, add a migration tool later. It is not required today.

## Testing Guidance

Prefer small, targeted tests around:

- source mapping
- dedupe behavior
- trend snapshot logic
- scoring edge cases

Avoid writing broad integration tests first when a focused unit test would catch the regression more cheaply.

## Documentation Rule

When behavior changes:

- update the operator docs if command usage changes
- update the technical docs if architecture, schema, or extension points change
- update the README if setup or quickstart flow changes

## Release/Handoff Rule

Before handing the stack to an operator:

- confirm docs match the real command surface
- confirm `doctor`, `initdb`, and the demo pipeline still work
- confirm any new environment variables are documented
- confirm README points to the deeper docs

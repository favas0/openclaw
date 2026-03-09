# OpenClaw V1

Low-cost AI-assisted product research agent for UK dropshipping.

## Local structure
- Repo: ~/projects/openclaw
- Secrets: ~/.config/openclaw/.env
- Data: ~/data/openclaw

## First commands
docker compose build
docker compose run --rm openclaw
docker compose run --rm openclaw python -m app.cli doctor
docker compose run --rm openclaw python -m app.cli initdb

## eBay collection
docker compose run --rm openclaw python -m app.cli collect-ebay "walking pad" --demo --limit 5
docker compose run --rm openclaw python -m app.cli collect-ebay "walking pad" --api --limit 20

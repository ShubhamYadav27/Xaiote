#!/bin/bash
export DATABASE_URL="postgresql+asyncpg://user:password@db:5432/xaiote_test"
export TEST_DATABASE_URL="postgresql+asyncpg://user:password@db:5432/xaiote_test"
alembic upgrade head
pytest -v > /app/pytest.txt
ruff check --fix .
ruff check . > /app/ruff.txt
black .
black --check . > /app/black.txt
mypy --config-file mypy.ini . > /app/mypy.txt
alembic current > /app/alembic_current.txt
alembic heads > /app/alembic_heads.txt
alembic upgrade head > /app/alembic_upgrade.txt

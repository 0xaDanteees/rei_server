# Simple Makefile to manage Alembic migrations per microservice on a shared DB
# Usage examples:
#   make partners-rev m="init partners"
#   make partners-up
#   make auth-rev m="add new field"
#   make auth-up

# WHAT THE FUCK IS THIS ?
# [redacted]-rev -> means "make [redacted]-rev m="" which is the same as "make [redacted]-rev m="init partners"" and this makes a new migration file
# [redacted]-up -> means "make [redacted]-up" which is the same as "make [redacted]-up" and this upgrades the database to the latest migration
# [redacted]-down -> means "make [redacted]-down" which is the same as "make [redacted]-down" and this downgrades the database to the previous migration
# [redacted]-stamp -> means "make [redacted]-stamp" which is the same as "make [redacted]-stamp" and this stamps the database to the latest migration

PY := PYTHONPATH=$(PWD)

# Partners
partners-rev:
	$(PY) alembic -c services/partners/alembic.ini revision --autogenerate -m "$(m)"

partners-up:
	$(PY) alembic -c services/partners/alembic.ini upgrade head

partners-down:
	$(PY) alembic -c services/partners/alembic.ini downgrade -1

partners-stamp:
	$(PY) alembic -c services/partners/alembic.ini stamp head

# Auth
auth-rev:
	$(PY) alembic -c services/auth/alembic.ini revision --autogenerate -m "$(m)"

auth-up:
	$(PY) alembic -c services/auth/alembic.ini upgrade head

auth-down:
	$(PY) alembic -c services/auth/alembic.ini downgrade -1

auth-stamp:
	$(PY) alembic -c services/auth/alembic.ini stamp head

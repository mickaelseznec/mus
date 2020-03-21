.PHONY := run test

run:
	@poetry run python pymus/telegram.py

test:
	@poetry run python -m unittest

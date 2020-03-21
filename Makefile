.PHONY := run test

run:
	@poetry run python pymus/telegram.py .secret

test:
	@poetry run python -m unittest

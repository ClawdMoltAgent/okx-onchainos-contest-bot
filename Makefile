run:
	python -m okx_contest_bot.main

dry:
	python -m okx_contest_bot.main --dry-run

test:
	pytest -q

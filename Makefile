.PHONY: verify test smoke

verify:
	. .venv/bin/activate && pytest -q
	. .venv/bin/activate && python test_server.py
	. .venv/bin/activate && python -m compileall -q app tests

test:
	. .venv/bin/activate && pytest -q

smoke:
	. .venv/bin/activate && python test_server.py

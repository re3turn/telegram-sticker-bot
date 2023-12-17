init:
	rye sync --no-dev --no-lock

test:
	nose2

.PHONY: init test

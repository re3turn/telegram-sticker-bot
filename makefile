init:
	pip install -r requirements.txt

test:
	nose2

.PHONY: init test

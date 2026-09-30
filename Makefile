.PHONY: install test run tf-fmt tf-validate

install:
	python -m pip install -r requirements.txt

test:
	python -m pytest -q

run:
	uvicorn app.main:app --reload

tf-fmt:
	terraform fmt -recursive infra

tf-validate:
	terraform -chdir=infra init -backend=false
	terraform -chdir=infra validate

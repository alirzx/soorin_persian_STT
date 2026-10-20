.PHONY: install dev test models download verify docker docker-studio preflight ui
install:
	python -m pip install -e '.[sherpa,test]'
dev:
	uvicorn soorin_stt.main:app --reload --host 127.0.0.1 --port 8080
test:
	PYTHONPATH=src pytest -q
models:
	soorin-models list
download:
	soorin-models download --model $(MODEL)
verify:
	soorin-models verify --model $(MODEL)
preflight:
	./scripts/deploy/preflight.sh
	./scripts/deploy/prepare-network.sh
docker: preflight
	docker compose --env-file .env -f deploy/compose.yaml up --build -d
docker-studio: preflight
	docker compose --env-file .env -f deploy/compose.yaml --profile studio up --build -d
ui:
	cd ui && npm install && npm run dev

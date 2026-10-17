.PHONY: install dev test models download verify docker ui
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
docker:
	docker compose --env-file .env -f deploy/compose.yaml up --build -d
ui:
	cd ui && npm install && npm run dev

IMAGE_NAME=my-fastapi-app
TAG=latest
APP_DIR=app

.PHONY: lint scan test build run clean

lint:
	ruff $(APP_DIR)

scan:
	grype $(APP_DIR) --fail-on=high || (echo "❌ Vulns found!" && exit 1)

test:
	pytest

build:
	docker build -t $(IMAGE_NAME):$(TAG) .

run:
	docker run --rm -p 8000:8000 $(IMAGE_NAME):$(TAG)

clean:
	docker rmi $(IMAGE_NAME):$(TAG)

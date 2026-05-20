.PHONY: help install dev test clean docker-up docker-down migrate lint format

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install all dependencies
	@echo "Installing Python dependencies..."
	cd services/event-collector && poetry install
	cd services/recommendation-engine && poetry install
	cd services/stream-processor && poetry install
	cd services/model-serving && poetry install
	cd services/ad-server && poetry install
	@echo "Installing Node.js dependencies..."
	cd services/tracker-sdk && npm install
	@echo "Installing Go dependencies..."
	cd services/bidding-engine && go mod download

dev: docker-up ## Start all services in development mode
	@echo "Starting development environment..."
	@echo "Event Collector:      http://localhost:8001"
	@echo "Recommendation API:   http://localhost:8002"
	@echo "Ad Server:            http://localhost:8003"
	@echo "Bidding Engine:       http://localhost:8004"
	@echo "Grafana:              http://localhost:3001"
	@echo "Kafka UI:             http://localhost:8080"

docker-up: ## Start infrastructure services (Kafka, PostgreSQL, Redis)
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 10

docker-down: ## Stop infrastructure services
	docker-compose down

docker-clean: ## Stop and remove all containers, volumes, and networks
	docker-compose down -v --remove-orphans

migrate: ## Run database migrations
	cd services/event-collector && poetry run alembic upgrade head

migrate-create: ## Create a new migration
	cd services/event-collector && poetry run alembic revision --autogenerate -m "$(name)"

test: ## Run all tests
	@echo "Running Python tests..."
	cd services/event-collector && poetry run pytest
	cd services/recommendation-engine && poetry run pytest
	cd services/ad-server && poetry run pytest
	@echo "Running Node.js tests..."
	cd services/tracker-sdk && npm test
	@echo "Running Go tests..."
	cd services/bidding-engine && go test ./...

test-unit: ## Run unit tests only
	find . -name "*_test.py" -o -name "*.test.js" -o -name "*_test.go" | xargs pytest

test-integration: ## Run integration tests
	docker-compose -f docker-compose.test.yml up --abort-on-container-exit

test-load: ## Run load tests
	cd tests/load && poetry run locust -f locustfile.py

lint: ## Run linters
	@echo "Linting Python code..."
	cd services/event-collector && poetry run ruff check .
	cd services/recommendation-engine && poetry run ruff check .
	@echo "Linting Node.js code..."
	cd services/tracker-sdk && npm run lint
	@echo "Linting Go code..."
	cd services/bidding-engine && golangci-lint run

format: ## Format code
	@echo "Formatting Python code..."
	cd services/event-collector && poetry run black .
	cd services/recommendation-engine && poetry run black .
	@echo "Formatting Node.js code..."
	cd services/tracker-sdk && npm run format
	@echo "Formatting Go code..."
	cd services/bidding-engine && go fmt ./...

clean: ## Clean build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "node_modules" -exec rm -rf {} +
	find . -type d -name "dist" -exec rm -rf {} +

build: ## Build Docker images
	docker-compose build

deploy-local: ## Deploy to local Kubernetes
	kubectl apply -f infrastructure/kubernetes/local/

deploy-prod: ## Deploy to production
	helm upgrade --install ad-platform ./infrastructure/helm/ad-platform -f infrastructure/helm/values-prod.yaml

k8s-logs: ## Tail logs from Kubernetes
	kubectl logs -f -l app=ad-platform -n ad-platform --all-containers=true

monitoring-up: ## Start monitoring stack
	docker-compose -f docker-compose.monitoring.yml up -d

seed-data: ## Seed database with sample data
	cd services/event-collector && poetry run python scripts/seed_data.py

train-models: ## Train recommendation models
	cd ml/training && poetry run python train_all.py

backup-db: ## Backup PostgreSQL database
	docker exec -t postgres pg_dumpall -c -U postgres > backup_$$(date +%Y%m%d_%H%M%S).sql

restore-db: ## Restore PostgreSQL database
	cat $(file) | docker exec -i postgres psql -U postgres

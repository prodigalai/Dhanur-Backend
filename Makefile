.PHONY: help install run dev test clean lint format requirements docker-build docker-run setup production

help: ## Show this help message
	@echo "Content Crew Prodigal API - Production Commands"
	@echo "=============================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install Python dependencies
	pip install -r requirements.txt

run: ## Run the production server
	python main.py

dev: ## Run development server with auto-reload
	uvicorn main:app --reload --host 0.0.0.0 --port 8080

test: ## Run tests
	python -m pytest

clean: ## Clean up Python cache files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -delete

lint: ## Run code linting
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

format: ## Format code with black
	black . --line-length=127

requirements: ## Update requirements.txt
	pip freeze > requirements.txt

docker-build: ## Build Docker image
	docker build -t content-crew-api .

docker-run: ## Run Docker container
	docker run -p 8080:8080 content-crew-api

setup: install ## Setup development environment
	@echo "Development environment setup complete!"

production: install ## Setup production environment
	@echo "Production environment setup complete!"

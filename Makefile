.PHONY: help build up down dev logs clean install test

help: ## Show this help message
	@echo "EmailBuilder - Available commands:"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "\033[36m\033[0m"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Development
dev: ## Start all services in development mode
	docker-compose up --build

up: ## Start all services
	docker-compose up -d

down: ## Stop all services
	docker-compose down

logs: ## Show logs from all services
	docker-compose logs -f

##@ Building
build: ## Build all Docker images
	docker-compose build

install: ## Install dependencies for all services
	cd frontend && npm install
	cd renderer && npm install
	cd orchestrator && pip install -r requirements.txt
	cd style-mining && pip install -r requirements.txt

##@ Style Mining
mine-cart-abandon: ## Run style mining for cart abandonment templates
	docker-compose run --rm style-mining python src/main.py cart_abandon

mine-post-purchase: ## Run style mining for post purchase templates
	docker-compose run --rm style-mining python src/main.py post_purchase

mine-order-confirmation: ## Run style mining for order confirmation templates
	docker-compose run --rm style-mining python src/main.py order_confirmation

mine-all: ## Run style mining for all template types
	$(MAKE) mine-cart-abandon
	$(MAKE) mine-post-purchase
	$(MAKE) mine-order-confirmation

##@ Testing
test-frontend: ## Run frontend tests
	cd frontend && npm test

test-renderer: ## Run renderer tests
	cd renderer && npm test

test-all: ## Run all tests
	$(MAKE) test-frontend
	$(MAKE) test-renderer

##@ Maintenance
clean: ## Clean up Docker containers and images
	docker-compose down -v
	docker system prune -f

clean-all: ## Deep clean (removes all Docker data)
	docker-compose down -v --remove-orphans
	docker system prune -af
	docker volume prune -f

##@ Health Checks
health: ## Check health of all services
	@echo "Checking service health..."
	@curl -s http://localhost:3000 > /dev/null && echo "✅ Frontend (3000)" || echo "❌ Frontend (3000)"
	@curl -s http://localhost:8000/health > /dev/null && echo "✅ Orchestrator (8000)" || echo "❌ Orchestrator (8000)"
	@curl -s http://localhost:3001/health > /dev/null && echo "✅ Renderer (3001)" || echo "❌ Renderer (3001)"

##@ Quick Start
setup: ## First-time setup
	@echo "🚀 Setting up EmailBuilder..."
	cp .env.example .env
	@echo "📝 Please edit .env file with your API keys"
	@echo "💡 Then run: make dev"

demo: ## Start demo with sample data
	@echo "🎬 Starting EmailBuilder demo..."
	$(MAKE) up
	@echo ""
	@echo "🌐 Frontend: http://localhost:3000"
	@echo "🔧 API: http://localhost:8000/docs"
	@echo "🎨 Renderer: http://localhost:3001/health"
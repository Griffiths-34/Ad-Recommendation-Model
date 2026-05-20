# Quick Start Script for Windows
# Run this script to start the entire Ad Recommendation Platform

Write-Host "🚀 Starting Ad Recommendation Platform..." -ForegroundColor Green
Write-Host ""

# Check if Docker is running
Write-Host "Checking Docker..." -ForegroundColor Yellow
docker info 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}
Write-Host "✅ Docker is running" -ForegroundColor Green
Write-Host ""

# Start infrastructure services
Write-Host "Starting infrastructure services (Kafka, PostgreSQL, Redis, etc.)..." -ForegroundColor Yellow
docker-compose up -d

Write-Host "Waiting for services to be ready (30 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Check service health
Write-Host ""
Write-Host "Service Status:" -ForegroundColor Cyan
docker-compose ps

Write-Host ""
Write-Host "✅ Infrastructure is ready!" -ForegroundColor Green
Write-Host ""
Write-Host "Access points:" -ForegroundColor Cyan
Write-Host "  - Kafka UI:      http://localhost:8080" -ForegroundColor White
Write-Host "  - Grafana:       http://localhost:3001 (admin/admin)" -ForegroundColor White
Write-Host "  - Prometheus:    http://localhost:9090" -ForegroundColor White
Write-Host "  - Jaeger:        http://localhost:16686" -ForegroundColor White
Write-Host "  - MinIO Console: http://localhost:9001 (minioadmin/minioadmin)" -ForegroundColor White
Write-Host ""

# Check if Node.js is installed
Write-Host "Checking Node.js installation..." -ForegroundColor Yellow
$nodeVersion = node --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Node.js $nodeVersion installed" -ForegroundColor Green
    
    Write-Host ""
    Write-Host "Building Tracker SDK..." -ForegroundColor Yellow
    Push-Location "services\tracker-sdk"
    
    if (-not (Test-Path "node_modules")) {
        Write-Host "Installing npm dependencies..." -ForegroundColor Yellow
        npm install
    }
    
    Write-Host "Building SDK..." -ForegroundColor Yellow
    npm run build
    
    Pop-Location
    Write-Host "✅ Tracker SDK built successfully" -ForegroundColor Green
} else {
    Write-Host "⚠️  Node.js not found. Tracker SDK needs to be built manually." -ForegroundColor Yellow
    Write-Host "   Install from: https://nodejs.org/" -ForegroundColor White
}

Write-Host ""
Write-Host "To start Event Collector service:" -ForegroundColor Cyan
Write-Host "  cd services\event-collector" -ForegroundColor White
Write-Host "  poetry install" -ForegroundColor White
Write-Host "  copy .env.example .env" -ForegroundColor White
Write-Host "  poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8001" -ForegroundColor White

Write-Host ""
Write-Host "To open the demo e-commerce site:" -ForegroundColor Cyan
Write-Host "  cd services\tracker-sdk" -ForegroundColor White
Write-Host "  start demo.html" -ForegroundColor White

Write-Host ""
Write-Host "📚 Read GETTING_STARTED.md for detailed instructions" -ForegroundColor Magenta
Write-Host ""
Write-Host "🎉 Setup complete! Happy building!" -ForegroundColor Green

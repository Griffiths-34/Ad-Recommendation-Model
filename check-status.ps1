# Ad Recommendation System - Complete Status Check
# Run this script anytime to check system status and troubleshoot

Write-Host "`n🔍 SYSTEM HEALTH CHECK`n" -ForegroundColor Cyan

# Check Docker services
Write-Host "Docker Services:" -ForegroundColor Yellow
$dockerServices = @("kafka", "postgres", "redis", "zookeeper", "jaeger", "kafka-ui")
foreach ($service in $dockerServices) {
    $status = docker ps --filter "name=$service" --format "{{.Names}}: {{.Status}}" 2>$null
    if ($status) {
        Write-Host "  ✅ $status" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $service not running" -ForegroundColor Red
    }
}

# Check Event Collector API
Write-Host "`nEvent Collector API:" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  ✅ API Healthy - $($response.Content)" -ForegroundColor Green
} catch {
    Write-Host "  ❌ API Not Responding" -ForegroundColor Red
    Write-Host "  Fix: cd services/event-collector; python -m poetry run uvicorn app.main:app --host 0.0.0.0 --port 8001" -ForegroundColor Yellow
}

# Check Kafka topics
Write-Host "`nKafka Topics:" -ForegroundColor Yellow
try {
    $topics = docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list 2>$null
    if ($topics) {
        Write-Host "  ✅ Topics: $topics" -ForegroundColor Green
    }
} catch {
    Write-Host "  ❌ Cannot list topics" -ForegroundColor Red
}

# Check for events in Kafka
Write-Host "`nKafka Events:" -ForegroundColor Yellow
$eventCount = docker exec kafka kafka-run-class kafka.tools.GetOffsetShell --broker-list localhost:9092 --topic user_events 2>$null | Select-String -Pattern ":(\d+)" | ForEach-Object { $_.Matches.Groups[1].Value }
if ($eventCount -and [int]$eventCount -gt 0) {
    Write-Host "  ✅ $eventCount events in user_events topic" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  No events yet - interact with demo to generate events" -ForegroundColor Yellow
}

# Summary
Write-Host "`n📊 Access Points:" -ForegroundColor Cyan
Write-Host "  • Demo: file:///C:/Users/griff/Downloads/Ad%20Recommendation%20Model/services/tracker-sdk/demo.html"
Write-Host "  • API Docs: http://localhost:8001/docs"
Write-Host "  • Kafka UI: http://localhost:8081"
Write-Host "  • Jaeger: http://localhost:16686"
Write-Host "  • Health: http://localhost:8001/health`n"

# Quick fixes
Write-Host "🔧 Quick Fixes:" -ForegroundColor Yellow
Write-Host "  Start infrastructure: docker-compose up -d zookeeper kafka postgres redis jaeger kafka-ui"
Write-Host "  Start API: cd services/event-collector; python -m poetry run uvicorn app.main:app --host 0.0.0.0 --port 8001"
Write-Host "  Stop all: docker-compose down"
Write-Host "  View logs: docker-compose logs -f kafka postgres redis`n"

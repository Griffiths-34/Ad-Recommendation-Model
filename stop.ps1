# Stop all services
Write-Host "🛑 Stopping Ad Recommendation Platform..." -ForegroundColor Yellow

docker-compose down

Write-Host "✅ All services stopped" -ForegroundColor Green
Write-Host ""
Write-Host "To remove all data (volumes):" -ForegroundColor Cyan
Write-Host "  docker-compose down -v" -ForegroundColor White

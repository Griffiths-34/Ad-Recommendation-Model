# View Data - Quick Access Script
# This script helps you view all the tracked events from your demo

Write-Host "`n===================================" -ForegroundColor Cyan
Write-Host "   AD RECOMMENDATION DATA VIEWER" -ForegroundColor Cyan
Write-Host "===================================`n" -ForegroundColor Cyan

Write-Host "Where is your data?" -ForegroundColor Yellow
Write-Host "  Kafka (real-time): localhost:9092, topic: user_events"
Write-Host "  Kafka UI: http://localhost:8081"
Write-Host "  PostgreSQL (future): localhost:5433`n"

Write-Host "Choose an option:" -ForegroundColor Green
Write-Host "  1. View latest events in Kafka"
Write-Host "  2. Open Kafka UI in browser"
Write-Host "  3. View all events (scrollable)"
Write-Host "  4. Monitor events in real-time"
Write-Host "  5. Count total events"
Write-Host "  6. Exit`n"

$choice = Read-Host "Enter choice (1-6)"

switch ($choice) {
    "1" {
        Write-Host "`nFetching latest 10 events...`n" -ForegroundColor Cyan
        docker exec kafka-server kafka-console-consumer `
            --bootstrap-server localhost:9092 `
            --topic user_events `
            --from-beginning `
            --max-messages 10 `
            --timeout-ms 5000 2>$null | ForEach-Object {
                $_ | ConvertFrom-Json | ConvertTo-Json -Depth 10
            }
    }
    "2" {
        Write-Host "`nOpening Kafka UI...`n" -ForegroundColor Cyan
        Start-Process "http://localhost:8081"
    }
    "3" {
        Write-Host "`nFetching all events (press Ctrl+C to stop)...`n" -ForegroundColor Cyan
        docker exec kafka-server kafka-console-consumer `
            --bootstrap-server localhost:9092 `
            --topic user_events `
            --from-beginning `
            2>$null | ForEach-Object {
                try {
                    $event = $_ | ConvertFrom-Json
                    Write-Host "Event: " -NoNewline -ForegroundColor Yellow
                    Write-Host $event.eventName -ForegroundColor White
                    Write-Host "  Time: $(Get-Date -UnixTimeSeconds ($event.timestamp/1000) -Format 'yyyy-MM-dd HH:mm:ss')"
                    Write-Host "  User: $($event.userId)"
                    if ($event.properties) {
                        Write-Host "  Data: $($event.properties | ConvertTo-Json -Compress)"
                    }
                    Write-Host ""
                } catch {
                    Write-Host $_ -ForegroundColor Gray
                }
            }
    }
    "4" {
        Write-Host "`nMonitoring events (press Ctrl+C to stop)...`n" -ForegroundColor Cyan
        docker exec kafka-server kafka-console-consumer `
            --bootstrap-server localhost:9092 `
            --topic user_events `
            2>$null | ForEach-Object {
                try {
                    $event = $_ | ConvertFrom-Json
                    $time = Get-Date -Format 'HH:mm:ss'
                    Write-Host "[$time] " -NoNewline -ForegroundColor Gray
                    Write-Host "$($event.eventName) " -NoNewline -ForegroundColor Green
                    Write-Host "by $($event.userId)" -ForegroundColor Cyan
                } catch {
                    Write-Host $_ -ForegroundColor Gray
                }
            }
    }
    "5" {
        Write-Host "`nCounting events...`n" -ForegroundColor Cyan
        $count = 0
        docker exec kafka-server kafka-console-consumer `
            --bootstrap-server localhost:9092 `
            --topic user_events `
            --from-beginning `
            --timeout-ms 3000 `
            2>$null | ForEach-Object { $count++ }
        Write-Host "Total events in Kafka: $count`n" -ForegroundColor Green
    }
    "6" {
        Write-Host "`nGoodbye!`n" -ForegroundColor Cyan
        exit
    }
    default {
        Write-Host "`nInvalid choice. Please run again.`n" -ForegroundColor Red
    }
}

Write-Host "`n===================================" -ForegroundColor Cyan
Write-Host "TIP: Open Kafka UI for best experience: http://localhost:8081" -ForegroundColor Yellow
Write-Host "===================================`n" -ForegroundColor Cyan

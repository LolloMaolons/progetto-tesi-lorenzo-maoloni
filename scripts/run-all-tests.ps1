$scriptDir = $PSScriptRoot
$rootDir = Split-Path -Parent $scriptDir
$misurazioniDir = Join-Path $rootDir "risultati-misurazioni"
if (-not (Test-Path $misurazioniDir)) { New-Item -ItemType Directory -Path $misurazioniDir }
Set-Location $scriptDir

$tests = @(
    @{ name = 'REST vs GraphQL semplici'; cmd = 'python test-1-rest-vs-graphql-simple.py' },
    @{ name = 'REST vs GraphQL composte'; cmd = 'python test-2-rest-vs-graphql-composite.py' },
    @{ name = 'Bandwidth'; cmd = 'python test-3-bandwidth-field-selection.py' },
    @{ name = 'WebSocket vs Polling'; cmd = 'python test-4-websocket-vs-polling.py' },
    @{ name = 'Rate Limiting'; cmd = 'python test-5-rate-limiting.py' },
    @{ name = 'WebSocket Concurrent'; cmd = 'python test-6-websocket-concurrent.py' },
    @{ name = 'MCP Diretto'; cmd = 'python test-7-mcp-direct.py' },
    @{ name = 'MCP+LLM'; cmd = 'python test-8-mcp-llm-orchestration.py' },
    @{ name = 'Redis Failover'; cmd = 'powershell -ExecutionPolicy Bypass -File test-9-redis-failover.ps1' },
    @{ name = 'Prometheus'; cmd = 'powershell -ExecutionPolicy Bypass -File test-10-prometheus-metrics.ps1' },
    @{ name = 'Trace ID'; cmd = 'powershell -ExecutionPolicy Bypass -File test-11-trace-id-logging.ps1' }
)

$totalTests = $tests.Count
$testCount = 0
$startTime = Get-Date

foreach ($test in $tests) {
    $testCount++
    Write-Host "[$testCount/$totalTests] $($test.name)" -ForegroundColor Yellow
    try {
        Invoke-Expression $test.cmd
    } catch {
        Write-Host "Errore in $($test.name): $_" -ForegroundColor Red
    }
    Start-Sleep -Seconds 2
}

$endTime = Get-Date
$duration = ($endTime - $startTime).TotalSeconds

Write-Host "\nTutti i test completati in $duration secondi."
Write-Host "File generati in: $misurazioniDir"
Write-Host "Prossimi passi:"
Write-Host "python scripts/analyze-results.py"
Write-Host "python scripts/generate-report.py"
Set-Location $rootDir

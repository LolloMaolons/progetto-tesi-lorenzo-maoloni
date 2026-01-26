$OutputFile = Join-Path $PSScriptRoot '..\risultati-misurazioni\test-9-redis-failover.json'
$Result = @{
    test = 'Redis Failover'
    data = (Get-Date).ToString('o')
    steps = @()
}

function Add-Step($desc, $status, $extra) {
    $Result.steps += @{ step = $desc; status = $status; extra = $extra }
}

Write-Host ('='*70)
Write-Host 'TEST 9: Redis Failover'
Write-Host ('='*70)

Add-Step 'Stop Redis' 'start' ''
docker compose stop redis | Out-Null
Start-Sleep -Seconds 3
Add-Step 'Stop Redis' 'done' ''

try {
    $resp = Invoke-RestMethod -Uri 'http://localhost:8080/health' -TimeoutSec 5
    $status = $resp.status
    $redis = $resp.redis
    Add-Step 'Check /health degraded' $status $redis
} catch {
    Add-Step 'Check /health degraded' 'fail' $_.Exception.Message
}

try {
    $r = Invoke-RestMethod -Uri 'http://localhost:8080/products' -TimeoutSec 5
    Add-Step 'CRUD durante Redis down' 'ok' ($r | ConvertTo-Json -Compress)
} catch {
    Add-Step 'CRUD durante Redis down' 'fail' $_.Exception.Message
}

Add-Step 'Start Redis' 'start' ''
docker compose start redis | Out-Null
Start-Sleep -Seconds 5
Add-Step 'Start Redis' 'done' ''

try {
    $resp2 = Invoke-RestMethod -Uri 'http://localhost:8080/health' -TimeoutSec 5
    $status2 = $resp2.status
    $redis2 = $resp2.redis
    Add-Step 'Check /health healthy' $status2 $redis2
} catch {
    Add-Step 'Check /health healthy' 'fail' $_.Exception.Message
}

Set-Content -Path $OutputFile -Value ($Result | ConvertTo-Json -Depth 6) -Encoding utf8
Write-Host "Risultati salvati: $OutputFile"

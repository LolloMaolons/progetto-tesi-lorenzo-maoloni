$OutputFile = Join-Path $PSScriptRoot '..\risultati-misurazioni\test-11-trace-id-logging.json'
$traceId = "trace-$(Get-Date -Format 'yyyyMMddHHmmssfff')"
$Result = @{
    test = 'Trace ID Logging'
    data = (Get-Date).ToString('o')
    trace_id = $traceId
    rest_found = $false
    graphql_found = $false
    steps = @()
}

function Add-Step($desc, $status, $extra) {
    $Result.steps += @{ step = $desc; status = $status; extra = $extra }
}

Write-Host ('='*70)
Write-Host 'TEST 11: Trace ID Logging'
Write-Host ('='*70)

try {
    $headers = @{ 'X-Trace-ID' = $traceId }
    $r = Invoke-RestMethod -Uri 'http://localhost:8080/products' -Headers $headers -TimeoutSec 5
    Add-Step 'REST request sent' 'ok' ''
} catch {
    Add-Step 'REST request sent' 'fail' $_.Exception.Message
}

try {
    $logs = docker compose logs api-rest
    if ($logs -match $traceId) {
        $Result.rest_found = $true
        Add-Step 'Trace ID in REST logs' 'found' ''
    } else {
        Add-Step 'Trace ID in REST logs' 'not found' ''
    }
} catch {
    Add-Step 'Trace ID in REST logs' 'fail' $_.Exception.Message
}

try {
    $headers = @{ 'X-Trace-ID' = $traceId; 'Content-Type' = 'application/json' }
    $body = '{"query": "{ products { id } }"}'
    $r = Invoke-RestMethod -Uri 'http://localhost:4000/' -Headers $headers -Method Post -Body $body -TimeoutSec 5
    Add-Step 'GraphQL request sent' 'ok' ''
} catch {
    Add-Step 'GraphQL request sent' 'fail' $_.Exception.Message
}

try {
    $logs = docker compose logs gateway-graphql
    if ($logs -match $traceId) {
        $Result.graphql_found = $true
        Add-Step 'Trace ID in GraphQL logs' 'found' ''
    } else {
        Add-Step 'Trace ID in GraphQL logs' 'not found' ''
    }
} catch {
    Add-Step 'Trace ID in GraphQL logs' 'fail' $_.Exception.Message
}

$Result.propagation = ($Result.rest_found -and $Result.graphql_found)

Set-Content -Path $OutputFile -Value ($Result | ConvertTo-Json -Depth 6) -Encoding utf8
Write-Host "Risultati salvati: $OutputFile"

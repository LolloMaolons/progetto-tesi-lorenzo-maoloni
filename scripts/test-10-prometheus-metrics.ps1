$restMetrics = Invoke-RestMethod -Uri 'http://localhost:8080/metrics' -TimeoutSec 10
$graphqlMetrics = Invoke-RestMethod -Uri 'http://localhost:9090/metrics' -TimeoutSec 10

$restPath = Join-Path $PSScriptRoot '..\risultati-misurazioni\test-10-prometheus-metrics\rest-metrics.txt'
$graphqlPath = Join-Path $PSScriptRoot '..\risultati-misurazioni\test-10-prometheus-metrics\graphql-metrics.txt'
$summaryPath = Join-Path $PSScriptRoot '..\risultati-misurazioni\test-10-prometheus-metrics\summary.json'

$restMetrics | Out-File -Encoding utf8 $restPath
$graphqlMetrics | Out-File -Encoding utf8 $graphqlPath

function Extract-Metric($lines, $name) {
    return $lines | Where-Object { $_ -match $name }
}
$restLines = Get-Content $restPath
$graphqlLines = Get-Content $graphqlPath

$summary = @{
    rest = @{
        requests_total = (Extract-Metric $restLines 'api_rest_requests_total')
        duration_buckets = (Extract-Metric $restLines 'api_rest_request_duration_seconds_bucket')
        errors_total = (Extract-Metric $restLines 'api_rest_errors_total')
    }
    graphql = @{
        requests_total = (Extract-Metric $graphqlLines 'graphql_requests_total')
        duration = (Extract-Metric $graphqlLines 'graphql_request_duration_seconds')
        errors_total = (Extract-Metric $graphqlLines 'graphql_errors_total')
    }
}
$summary | ConvertTo-Json -Depth 6 | Out-File -Encoding utf8 $summaryPath
Write-Host "Risultati salvati: $restPath, $graphqlPath, $summaryPath"

$curl = "$env:SystemRoot\System32\curl.exe"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $root "..")

New-Item -ItemType Directory -Force -Path "misurazioni" | Out-Null
New-Item -ItemType Directory -Force -Path "query" | Out-Null

1..3 | % { & $curl -s http://localhost:8080/products/1 >$null }
1..3 | % { & $curl -s -X POST -H "Content-Type: application/json" --data-binary "@query/query_1.json" http://localhost:4000/graphql >$null }

function Get-Stats($arr) {
  $mean = ($arr | Measure-Object -Average).Average
  $sorted = $arr | Sort-Object
  $p95 = $sorted[[int]([math]::Ceiling($sorted.Count*0.95))-1]
  return @{ mean = $mean; p95 = $p95 }
}

$rest_simple = 1..30 | % {
  $t = & $curl -w "time=%{time_total} size=%{size_download}\n" -o NUL -s http://localhost:8080/products/1
  $t.Trim()
}
$rest_simple | Set-Content misurazioni/rest_simple.txt

$gql_simple = 1..30 | % {
  & $curl -w "time=%{time_total} size=%{size_download}\n" -o NUL -s -X POST -H "Content-Type: application/json" --data-binary "@query/query_1.json" http://localhost:4000/graphql
}
$gql_simple | Set-Content misurazioni/gql_simple.txt

$restS_time = Get-Content misurazioni/rest_simple.txt | % { if ($_ -match "time=([\d\.]+)") {[double]$matches[1]} }
$restS_bytes = Get-Content misurazioni/rest_simple.txt | % { if ($_ -match "size=(\d+)") {[int]$matches[1]} }
$gqlS_time = Get-Content misurazioni/gql_simple.txt | % { if ($_ -match "time=([\d\.]+)") {[double]$matches[1]} }
$gqlS_bytes = Get-Content misurazioni/gql_simple.txt | % { if ($_ -match "size=(\d+)") {[int]$matches[1]} }

$restS_stats_t = Get-Stats $restS_time
$gqlS_stats_t = Get-Stats $gqlS_time
$restS_stats_b = Get-Stats $restS_bytes
$gqlS_stats_b = Get-Stats $gqlS_bytes

$rest_complex = 1..30 | % {
  $a = & $curl -w "time=%{time_total} size=%{size_download}\n" -o NUL -s http://localhost:8080/products/1
  $b = & $curl -w "time=%{time_total} size=%{size_download}\n" -o NUL -s http://localhost:8080/products/1/recommendations?limit=3
  $c = & $curl -w "time=%{time_total} size=%{size_download}\n" -o NUL -s "http://localhost:8080/products?limit=5"
  $d = & $curl -w "time=%{time_total} size=%{size_download}\n" -o NUL -s "http://localhost:8080/products?limit=3&category=accessories"
  "$($a.Trim()) | $($b.Trim()) | $($c.Trim()) | $($d.Trim())"
}
$rest_complex | Set-Content misurazioni/rest_complex.txt

$gql_complex = 1..30 | % {
  & $curl -w "time=%{time_total} size=%{size_download}\n" -o NUL -s -X POST -H "Content-Type: application/json" --data-binary "@query/query_2.json" http://localhost:4000/graphql
}
$gql_complex | Set-Content misurazioni/gql_complex.txt

$restC_time = Get-Content misurazioni/rest_complex.txt | % {
  if ($_ -match "time=([\d\.]+).*time=([\d\.]+).*time=([\d\.]+).*time=([\d\.]+)") {
    [double]$matches[1] + [double]$matches[2] + [double]$matches[3] + [double]$matches[4]
  }
}
$restC_bytes = Get-Content misurazioni/rest_complex.txt | % {
  if ($_ -match "size=(\d+).*size=(\d+).*size=(\d+).*size=(\d+)") {
    [int]$matches[1] + [int]$matches[2] + [int]$matches[3] + [int]$matches[4]
  }
}
$gqlC_time = Get-Content misurazioni/gql_complex.txt | % { if ($_ -match "time=([\d\.]+)") {[double]$matches[1]} }
$gqlC_bytes = Get-Content misurazioni/gql_complex.txt | % { if ($_ -match "size=(\d+)") {[int]$matches[1]} }

$restC_stats_t = Get-Stats $restC_time
$gqlC_stats_t = Get-Stats $gqlC_time
$restC_stats_b = Get-Stats $restC_bytes
$gqlC_stats_b = Get-Stats $gqlC_bytes

"`n=== RISULTATI ==="
"Simple REST  : time mean={0:N4}s p95={1:N4}s ; bytes mean={2} p95={3}" -f $restS_stats_t.mean, $restS_stats_t.p95, $restS_stats_b.mean, $restS_stats_b.p95
"Simple GQL   : time mean={0:N4}s p95={1:N4}s ; bytes mean={2} p95={3}" -f $gqlS_stats_t.mean, $gqlS_stats_t.p95, $gqlS_stats_b.mean, $gqlS_stats_b.p95
"Complex REST : time mean={0:N4}s p95={1:N4}s ; bytes mean={2} p95={3}" -f $restC_stats_t.mean, $restC_stats_t.p95, $restC_stats_b.mean, $restC_stats_b.p95
"Complex GQL  : time mean={0:N4}s p95={1:N4}s ; bytes mean={2} p95={3}" -f $gqlC_stats_t.mean, $gqlC_stats_t.p95, $gqlC_stats_b.mean, $gqlC_stats_b.p95
$curl = "$env:SystemRoot\System32\curl.exe"
$runs = 20
$intervalMs = 50
$deltas = @()

for ($i = 1; $i -le $runs; $i++) {
  $expectedStock = 5
  $expectedPrice = 1200
  $tsPatch = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
  & $curl -s -o NUL -X PATCH "http://localhost:8080/products/1?price=$expectedPrice&stock=$expectedStock" | Out-Null

  while ($true) {
    $body = & $curl -s "http://localhost:8080/products/1"
    try {
      $obj = $body | ConvertFrom-Json
      if ($obj.stock -eq $expectedStock -and [int]$obj.price -eq $expectedPrice) {
        $delta = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() - $tsPatch
        $deltas += $delta
        Write-Host ("Run {0}: delta={1} ms" -f $i, $delta)
        break
      }
    } catch {}
    Start-Sleep -Milliseconds $intervalMs
  }
}

$deltasSorted = $deltas | Sort-Object
$mean = ($deltas | Measure-Object -Average).Average
$p95 = $deltasSorted[[int]([math]::Ceiling($deltasSorted.Count*0.95))-1]
Write-Host ("Polling REST: runs={0} mean={1} ms p95={2} ms (interval={3} ms)" -f $runs, [math]::Round($mean,2), $p95, $intervalMs)
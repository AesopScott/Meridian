$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$exePath = Join-Path $repoRoot "dist\win-unpacked\Meridian.exe"
$healthUri = "http://127.0.0.1:8767/bridge/health"
$messageUri = "http://127.0.0.1:8767/bridge/message"
$restartUri = "http://127.0.0.1:8767/bridge/restart"

if (-not (Test-Path $exePath)) {
  throw "Packaged Meridian executable not found at $exePath. Run npm run build:win first."
}

function Wait-MeridianBridgeHealthy {
  param([int]$Seconds = 25)

  $deadline = (Get-Date).AddSeconds($Seconds)
  do {
    Start-Sleep -Milliseconds 500
    try {
      $health = Invoke-RestMethod -Uri $healthUri -TimeoutSec 2
      if ($health.ok -and $health.state -eq "healthy") {
        return $health
      }
    } catch {
      # Keep polling until the deadline.
    }
  } while ((Get-Date) -lt $deadline)

  return $null
}

function Invoke-MeridianMessageSmoke {
  param(
    [string]$RequestPrefix,
    [string]$Prompt,
    [string]$ExpectedText,
    [array]$Attachments = @()
  )

  $body = @{
    backend = "codex"
    requestedBackend = "codex"
    channel = "prime"
    requestId = "$RequestPrefix-$([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())"
    prompt = $Prompt
    transcript = @()
    projectContext = "Meridian"
    attachments = $Attachments
    primeContract = @{
      role = "Prime"
      identity = "Prime speaks through Spark on behalf of Meridian."
      directives = @("Answer only the requested smoke phrase.")
      proofObligations = @("Do not claim unverified actions.")
      responsePreferences = @("Be concise.")
    }
  } | ConvertTo-Json -Depth 12

  $result = Invoke-RestMethod -Method Post -Uri $messageUri -ContentType "application/json" -Body $body -TimeoutSec 180
  $text = ""
  if ($null -ne $result.text) {
    $text = [string]$result.text
  }
  if (-not $result.ok) {
    throw "Message smoke failed: $($result.error)"
  }
  if ($text.Trim() -ne $ExpectedText) {
    throw "Unexpected model smoke response: '$($text.Trim())'"
  }
  return $result
}

$appProcess = $null
$summary = [ordered]@{
  ok = $false
  executable = $exePath
  health = $null
  restart = $null
  message = $null
  context = $null
  shutdown = $null
}

try {
  $appProcess = Start-Process -FilePath $exePath -PassThru -WindowStyle Hidden
  $initialHealth = Wait-MeridianBridgeHealthy 25
  if (-not $initialHealth) {
    throw "Packaged Meridian did not expose a healthy bridge."
  }
  $summary.health = @{
    ok = $true
    pid = $initialHealth.pid
    state = $initialHealth.state
    version = $initialHealth.version
  }

  $restart = Invoke-RestMethod -Method Post -Uri $restartUri -TimeoutSec 3
  $afterRestart = Wait-MeridianBridgeHealthy 25
  if (-not $restart.ok -or -not $afterRestart) {
    throw "Bridge restart smoke failed."
  }
  $summary.restart = @{
    ok = $true
    supervised = [bool]$restart.supervised
    beforePid = $initialHealth.pid
    afterPid = $afterRestart.pid
    version = $afterRestart.version
  }

  $message = Invoke-MeridianMessageSmoke `
    -RequestPrefix "v3-smoke" `
    -Prompt "Reply exactly: v3-smoke-ok" `
    -ExpectedText "v3-smoke-ok"
  $summary.message = @{
    ok = $true
    backend = $message.backend
    model = $message.model
    durationMs = $message.durationMs
    inputTokens = $message.inputTokens
    outputTokens = $message.outputTokens
  }

  $attachmentText = "Meridian V3 context smoke attachment."
  $attachmentBytes = [Text.Encoding]::UTF8.GetBytes($attachmentText)
  $attachment = @{
    name = "v3-context-smoke.txt"
    type = "text/plain"
    size = $attachmentBytes.Length
    kind = "document"
    source = "upload"
    dataUrl = "data:text/plain;base64,$([Convert]::ToBase64String($attachmentBytes))"
  }
  $context = Invoke-MeridianMessageSmoke `
    -RequestPrefix "v3-context-smoke" `
    -Prompt "Reply exactly: v3-context-ok" `
    -ExpectedText "v3-context-ok" `
    -Attachments @($attachment)
  $materialized = @($context.attachments)
  if ($materialized.Count -ne 1 -or -not $materialized[0].path) {
    throw "Context smoke did not return materialized attachment metadata."
  }
  $summary.context = @{
    ok = $true
    attachmentCount = $materialized.Count
    attachmentName = $materialized[0].name
    attachmentPathPresent = [bool]$materialized[0].path
    durationMs = $context.durationMs
  }

  $summary.ok = $true
} finally {
  if ($appProcess) {
    try { Stop-Process -Id $appProcess.Id -Force -ErrorAction SilentlyContinue } catch {}
    Start-Sleep -Seconds 1
  }
  try {
    $leftover = Invoke-RestMethod -Uri $healthUri -TimeoutSec 2
    $summary.shutdown = @{
      ok = $false
      bridgeStillReachable = $true
      pid = $leftover.pid
    }
  } catch {
    $summary.shutdown = @{
      ok = $true
      bridgeStillReachable = $false
    }
  }
}

$summary | ConvertTo-Json -Depth 12
if (-not $summary.ok -or -not $summary.shutdown.ok) {
  exit 1
}

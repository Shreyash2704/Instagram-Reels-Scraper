# Run from repo root or backend: starts RQ worker for queue "pipeline" (default).
# Requires: pip install redis rq; Redis running; REDIS_URL in environment or default below.
$ErrorActionPreference = "Stop"
$backendRoot = Split-Path -Parent $PSScriptRoot
Set-Location $backendRoot
if (-not $env:PYTHONPATH) {
    $env:PYTHONPATH = $backendRoot
}
$redisUrl = if ($env:REDIS_URL) { $env:REDIS_URL } else { "redis://127.0.0.1:6379/0" }
$queue = if ($env:RQ_QUEUE_NAME) { $env:RQ_QUEUE_NAME } else { "pipeline" }
Write-Host "RQ worker using $redisUrl queue $queue (must match app RQ_QUEUE_NAME)"
rq worker -u $redisUrl $queue

Write-Host "Stopping InternAI services..." -ForegroundColor Cyan

# 1. Stop Node backend (Port 5000)
$nodePids = (Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue).OwningProcess | Select-Object -Unique
if ($nodePids) {
    foreach ($p in $nodePids) {
        Write-Host "Stopping Node backend (PID $p)..."
        Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
    }
} else {
    Write-Host "Node backend is not running." -ForegroundColor DarkGray
}

# 2. Stop Flask AI service (Port 5001)
$aiPids = (Get-NetTCPConnection -LocalPort 5001 -ErrorAction SilentlyContinue).OwningProcess | Select-Object -Unique
if ($aiPids) {
    foreach ($p in $aiPids) {
        Write-Host "Stopping Flask AI service (PID $p)..."
        Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
    }
} else {
    Write-Host "Flask AI service is not running." -ForegroundColor DarkGray
}

# 3. Stop Ollama (Port 11434)
$ollamaPids = (Get-NetTCPConnection -LocalPort 11434 -ErrorAction SilentlyContinue).OwningProcess | Select-Object -Unique
if ($ollamaPids) {
    foreach ($p in $ollamaPids) {
        Write-Host "Stopping Ollama (PID $p)..."
        Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
    }
} else {
    Write-Host "Ollama is not running." -ForegroundColor DarkGray
}

Write-Host "All services stopped successfully." -ForegroundColor Green

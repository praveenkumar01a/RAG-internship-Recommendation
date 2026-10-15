$ErrorActionPreference = 'Stop'

function Test-PortOpen {
    param(
        [string]$HostName,
        [int]$Port
    )

    return Test-NetConnection -ComputerName $HostName -Port $Port -InformationLevel Quiet
}

function Start-DetachedProcess {
    param(
        [string]$FilePath,
        [string[]]$ArgumentList,
        [string]$WorkingDirectory,
        [string]$StdOutPath,
        [string]$StdErrPath
    )

    Start-Process `
        -FilePath $FilePath `
        -ArgumentList $ArgumentList `
        -WorkingDirectory $WorkingDirectory `
        -RedirectStandardOutput $StdOutPath `
        -RedirectStandardError $StdErrPath `
        -WindowStyle Hidden | Out-Null
}

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $rootDir 'backend'
$aiDir = Join-Path $backendDir 'ai'

$ollamaExe = if (Test-Path 'C:\Users\PRAVEENGOVIND\AppData\Local\Programs\Ollama\ollama.exe') { 'C:\Users\PRAVEENGOVIND\AppData\Local\Programs\Ollama\ollama.exe' } elseif (Get-Command 'ollama' -ErrorAction SilentlyContinue) { 'ollama' } else { 'ollama' }
$pythonExe = if (Test-Path 'C:\Users\PRAVEENGOVIND\Anaconda3\python.exe') { 'C:\Users\PRAVEENGOVIND\Anaconda3\python.exe' } elseif (Get-Command 'python' -ErrorAction SilentlyContinue) { 'python' } else { 'python' }
$nodeExe = if (Test-Path 'D:\trunk\ip\node\node.exe') { 'D:\trunk\ip\node\node.exe' } elseif (Get-Command 'node' -ErrorAction SilentlyContinue) { 'node' } else { 'node' }

$ollamaPortOpen = Test-PortOpen -HostName '127.0.0.1' -Port 11434
if (-not $ollamaPortOpen) {
    Write-Host 'Starting Ollama...'
    Start-DetachedProcess -FilePath $ollamaExe -ArgumentList @('serve') -WorkingDirectory $rootDir -StdOutPath (Join-Path $rootDir 'ollama.out.log') -StdErrPath (Join-Path $rootDir 'ollama.err.log')
    Start-Sleep -Seconds 3
} else {
    Write-Host 'Ollama is already running.'
}

if (Test-PortOpen -HostName '127.0.0.1' -Port 5001) {
    Write-Host 'Flask AI service is already running.'
} else {
    Write-Host 'Starting Flask AI service...'
    Start-DetachedProcess -FilePath $pythonExe -ArgumentList @('ai_server.py') -WorkingDirectory $aiDir -StdOutPath (Join-Path $aiDir 'ai.out.log') -StdErrPath (Join-Path $aiDir 'ai.err.log')
}

if (Test-PortOpen -HostName '127.0.0.1' -Port 5000) {
    Write-Host 'Node backend is already running.'
} else {
    Write-Host 'Starting Node backend...'
    Start-DetachedProcess -FilePath $nodeExe -ArgumentList @('server.js') -WorkingDirectory $backendDir -StdOutPath (Join-Path $backendDir 'node.out.log') -StdErrPath (Join-Path $backendDir 'node.err.log')
}

Start-Sleep -Seconds 5

$aiHealthy = $false
$nodeHealthy = $false

try {
    $aiResponse = Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:5001/api/health' -TimeoutSec 10
    $aiHealthy = $aiResponse.StatusCode -eq 200
} catch {
    $aiHealthy = $false
}

try {
    $nodeResponse = Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:5000/' -TimeoutSec 10
    $nodeHealthy = $nodeResponse.StatusCode -eq 200
} catch {
    $nodeHealthy = $false
}

Write-Host ''
Write-Host 'Project status:'
Write-Host ('- Ollama: ' + ($(if ($ollamaPortOpen) { 'already running' } else { 'started' })))
Write-Host ('- Flask AI service: ' + ($(if ($aiHealthy) { 'up on http://localhost:5001' } else { 'not responding yet' })))
Write-Host ('- Node backend: ' + ($(if ($nodeHealthy) { 'up on http://localhost:5000' } else { 'not responding yet' })))

if ($nodeHealthy) {
    Write-Host ''
    Write-Host 'Opening app in browser at http://localhost:5000 ...'
    Start-Process 'http://localhost:5000'
}

if (-not $aiHealthy -or -not $nodeHealthy) {
    Write-Host ''
    Write-Host 'If a service is not responding, check these logs:'
    Write-Host ('- ' + (Join-Path $aiDir 'ai.err.log'))
    Write-Host ('- ' + (Join-Path $backendDir 'node.err.log'))
    if (-not $ollamaPortOpen) {
        Write-Host ('- ' + (Join-Path $rootDir 'ollama.err.log'))
    }
}

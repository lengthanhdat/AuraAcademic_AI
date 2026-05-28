# Unified AI Gateway & Proctoring Server - AuraAcademic
# Run: .\start.ps1

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

# 1. Load environment variables from .env if it exists
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#")) {
            $key, $value = $line -split '=', 2
            if ($key -and $value) {
                # Trim surrounding quotes if any
                $val = $value.Trim().Trim("'").Trim('"')
                [System.Environment]::SetEnvironmentVariable($key.Trim(), $val, "Process")
            }
        }
    }
}

# LiteLLM UI Login (bypass DB requirement)
$env:UI_USERNAME = 'admin'
$env:UI_PASSWORD = $env:LITELLM_MASTER_KEY

# 2. Port Checker Helper
function Check-Port($port) {
    try {
        $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        if ($conn) {
            $pid = $conn[0].OwningProcess
            $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
            $name = if ($proc) { $proc.ProcessName } else { "Unknown" }
            return @{ Busy = $true; PID = $pid; Name = $name }
        }
    } catch {
        # Fallback to netstat if Get-NetTCPConnection is not available
        $netstat = netstat -ano | Select-String "LISTENING" | Select-String ":$port\s+"
        if ($netstat) {
            $parts = $netstat.Line -split '\s+' | Where-Object { $_ }
            $pid = $parts[-1]
            $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
            $name = if ($proc) { $proc.ProcessName } else { "Unknown" }
            return @{ Busy = $true; PID = $pid; Name = $name }
        }
    }
    return @{ Busy = $false }
}

# 3. Check and release ports if occupied
$ports = @(4000, 8001)
foreach ($port in $ports) {
    $chk = Check-Port $port
    if ($chk.Busy) {
        Write-Host "Canh bao: Cong $port dang bi chiem giu boi tien trinh $($chk.Name) (PID: $($chk.PID))." -ForegroundColor Yellow
        Write-Host "Dang giai phong cong $port bang cach dung tien trinh cu..." -ForegroundColor Cyan
        Stop-Process -Id $chk.PID -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
        
        # Double check
        $chk2 = Check-Port $port
        if ($chk2.Busy) {
            Write-Host "Khong the giai phong cong $port tu dong. Vui long dung tien trinh $($chk.Name) (PID: $($chk.PID)) thu cong." -ForegroundColor Red
            exit 1
        } else {
            Write-Host "Giai phong cong $port thanh cong!" -ForegroundColor Green
        }
    }
}

# 4. Start servers in parallel using background jobs
$currentDir = Get-Location

Write-Host "`nDang khoi tao cac may chu dich vu..." -ForegroundColor Cyan

# Start LiteLLM Proxy
$jobLite = Start-Job -ScriptBlock {
    param($dir, $username, $password)
    Set-Location $dir
    $env:PYTHONUTF8 = '1'
    $env:PYTHONIOENCODING = 'utf-8'
    $env:UI_USERNAME = $username
    $env:UI_PASSWORD = $password
    & ".\venv\Scripts\litellm.exe" --config litellm_config.yaml --port 4000 2>&1
} -ArgumentList $currentDir, $env:UI_USERNAME, $env:UI_PASSWORD

# Start YOLOv8 Proctoring Server
$jobYolo = Start-Job -ScriptBlock {
    param($dir)
    Set-Location $dir
    $env:PYTHONUTF8 = '1'
    $env:PYTHONIOENCODING = 'utf-8'
    & ".\venv\Scripts\python.exe" main.py 2>&1
} -ArgumentList $currentDir

Write-Host "--------------------------------------------------------" -ForegroundColor Gray
Write-Host "  LiteLLM Proxy dang khoi dong tren cong 4000..." -ForegroundColor Cyan
Write-Host "  YOLOv8 AI Server dang khoi dong tren cong 8001..." -ForegroundColor Yellow
Write-Host "--------------------------------------------------------" -ForegroundColor Gray
Write-Host "Nhan CTRL+C de tat dong thoi ca hai may chu dich vu an toan.`n" -ForegroundColor Green

# 5. Stream logs in real-time with color coding
try {
    while ($true) {
        # Receive output from LiteLLM
        $outLite = Receive-Job -Job $jobLite
        foreach ($line in $outLite) {
            $txt = $line.ToString()
            if ($txt.Trim()) {
                Write-Host "[LiteLLM Proxy] " -NoNewline -ForegroundColor Cyan
                Write-Host $txt
            }
        }

        # Receive output from YOLOv8
        $outYolo = Receive-Job -Job $jobYolo
        foreach ($line in $outYolo) {
            $txt = $line.ToString()
            if ($txt.Trim()) {
                Write-Host "[YOLOv8 AI]     " -NoNewline -ForegroundColor Yellow
                Write-Host $txt
            }
        }

        Start-Sleep -Milliseconds 150
    }
}
finally {
    Write-Host "`n--------------------------------------------------------" -ForegroundColor Gray
    Write-Host "Dang tat cac may chu dich vu va don dep tai nguyen..." -ForegroundColor Red
    
    # Stop PowerShell background jobs
    Stop-Job -Job $jobLite -ErrorAction SilentlyContinue
    Remove-Job -Job $jobLite -Force -ErrorAction SilentlyContinue
    Stop-Job -Job $jobYolo -ErrorAction SilentlyContinue
    Remove-Job -Job $jobYolo -Force -ErrorAction SilentlyContinue
    
    # Double check and force kill any orphan processes on the ports
    foreach ($port in $ports) {
        $chk = Check-Port $port
        if ($chk.Busy) {
            Stop-Process -Id $chk.PID -Force -ErrorAction SilentlyContinue
            Write-Host "Da giai phong thanh cong tien trinh rac tren cong $port (PID: $($chk.PID))" -ForegroundColor DarkRed
        }
    }
    Write-Host "Hoan tat don dep! Cong 4000 va 8001 da san sang cho lan chay sau." -ForegroundColor Green
    Write-Host "--------------------------------------------------------" -ForegroundColor Gray
}

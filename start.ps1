# LiteLLM Proxy - AuraAcademic AI Gateway
# Run: .\start.ps1
# Install first: pip install "litellm[proxy]"

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

# Load environment variables from .env if it exists
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

Write-Host "Starting LiteLLM Proxy at http://localhost:4000 ..." -ForegroundColor Cyan
litellm --config litellm_config.yaml --port 4000

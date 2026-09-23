while ($true) {
    Write-Host "Running classifier..."
    python -m src.main --stage classify
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Classification complete. Exiting."
        break
    }
    Write-Host "Sleeping for 30 minutes..."
    Start-Sleep -Seconds 1800
}

# setup_winutils.ps1
# Downloads winutils.exe and hadoop.dll required for running PySpark/Hadoop on Windows.
# Run this once before using any Spark scripts.

$hadoopVersion = "3.3.6"
$installDir = "C:\hadoop\bin"
$baseUrl = "https://github.com/cdarlint/winutils/raw/master/hadoop-$hadoopVersion/bin"

Write-Host "=== Setting up Hadoop winutils for Windows ===" -ForegroundColor Cyan

# Create the bin directory
if (!(Test-Path $installDir)) {
    New-Item -ItemType Directory -Path $installDir -Force | Out-Null
    Write-Host "[OK] Created: $installDir" -ForegroundColor Green
} else {
    Write-Host "[SKIP] Already exists: $installDir" -ForegroundColor Yellow
}

# Download winutils.exe
$winutilsPath = "$installDir\winutils.exe"
if (!(Test-Path $winutilsPath)) {
    Write-Host "Downloading winutils.exe..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri "$baseUrl/winutils.exe" -OutFile $winutilsPath -UseBasicParsing
    Write-Host "[OK] winutils.exe downloaded." -ForegroundColor Green
} else {
    Write-Host "[SKIP] winutils.exe already exists." -ForegroundColor Yellow
}

# Download hadoop.dll
$hadoopDllPath = "$installDir\hadoop.dll"
if (!(Test-Path $hadoopDllPath)) {
    Write-Host "Downloading hadoop.dll..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri "$baseUrl/hadoop.dll" -OutFile $hadoopDllPath -UseBasicParsing
    Write-Host "[OK] hadoop.dll downloaded." -ForegroundColor Green
} else {
    Write-Host "[SKIP] hadoop.dll already exists." -ForegroundColor Yellow
}

# Set HADOOP_HOME and JAVA_HOME permanently for this user
$javaHome = "C:\Program Files\Eclipse Adoptium\jdk-17.0.18.8-hotspot"
[System.Environment]::SetEnvironmentVariable("HADOOP_HOME", "C:\hadoop", "User")
[System.Environment]::SetEnvironmentVariable("JAVA_HOME", $javaHome, "User")

# Also update PATH if not already included
$userPath = [System.Environment]::GetEnvironmentVariable("PATH", "User")
if ($userPath -notlike "*C:\hadoop\bin*") {
    [System.Environment]::SetEnvironmentVariable("PATH", "C:\hadoop\bin;" + $userPath, "User")
    Write-Host "[OK] C:\hadoop\bin added to PATH." -ForegroundColor Green
}
if ($userPath -notlike "*$javaHome\bin*") {
    [System.Environment]::SetEnvironmentVariable("PATH", "$javaHome\bin;" + $userPath, "User")
    Write-Host "[OK] Java 17 bin added to PATH." -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Setup Complete! ===" -ForegroundColor Green
Write-Host "HADOOP_HOME = C:\hadoop" -ForegroundColor White
Write-Host "JAVA_HOME   = $javaHome" -ForegroundColor White
Write-Host ""
Write-Host "IMPORTANT: Close and reopen your terminal for env vars to take effect." -ForegroundColor Yellow
Write-Host "Then run: .\venv\Scripts\python.exe scripts/bronze_layer/create_delta_table.py" -ForegroundColor Cyan

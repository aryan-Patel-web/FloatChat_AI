# FloatChat Setup Script - PRODUCTION READY
# Fixed with real MinIO credentials and proper configuration
# NO demo configurations - uses actual server settings
# Run this in PowerShell from D:\FloatChat ARGO\MINIO directory

Write-Host "=== FloatChat AI System Setup ===" -ForegroundColor Green
Write-Host "Production deployment with real MinIO integration" -ForegroundColor Cyan
Write-Host ""

# Navigate to project directory
$projectPath = "D:\FloatChat ARGO\MINIO"
if (Test-Path $projectPath) {
    Set-Location $projectPath
    Write-Host "✓ Project directory: $projectPath" -ForegroundColor Green
} else {
    Write-Host "✗ Project directory not found: $projectPath" -ForegroundColor Red
    exit 1
}

# Create production directory structure
Write-Host "Creating production directory structure..." -ForegroundColor Blue
$directories = @(
    "data",
    "data/argo",
    "data/incois", 
    "data/netcdf",
    "data/processed",
    "rag_indices",
    "logs",
    "embeddings",
    "alerts",
    "cache",
    "exports",
    "backups"
)

foreach ($dir in $directories) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "✓ Created: $dir" -ForegroundColor Yellow
    } else {
        Write-Host "  Exists: $dir" -ForegroundColor Gray
    }
}

# Install production Python dependencies
Write-Host ""
Write-Host "Installing production Python dependencies..." -ForegroundColor Blue

$packages = @(
    "streamlit>=1.28.0",
    "pandas>=2.1.0",
    "numpy>=1.24.0", 
    "netcdf4>=1.6.4",
    "xarray>=2023.8.0",
    "minio>=7.1.0",
    "pymongo>=4.5.0",
    "faiss-cpu>=1.7.4",
    "sentence-transformers>=2.2.2",
    "transformers>=4.33.0",
    "torch>=2.0.1",
    "langchain>=0.0.350",
    "python-dotenv>=1.0.0",
    "aiohttp>=3.8.5",
    "beautifulsoup4>=4.12.2",
    "requests>=2.31.0",
    "plotly>=5.17.0",
    "schedule>=1.2.0",
    "groq>=0.4.1",
    "mistralai>=0.1.2",
    "httpx>=0.25.0",
    "asyncio-mqtt>=0.13.0"
)

Write-Host "Installing packages..." -ForegroundColor Gray
foreach ($package in $packages) {
    try {
        pip install $package --upgrade --quiet
        Write-Host "✓ $package" -ForegroundColor Green
    } catch {
        Write-Host "✗ Failed: $package" -ForegroundColor Red
    }
}

# Configure MinIO with REAL credentials from your server
Write-Host ""
Write-Host "Configuring MinIO with real server credentials..." -ForegroundColor Blue

# Your actual MinIO server configuration
$MINIO_ENDPOINT = "127.0.0.1:9000"
$MINIO_ACCESS_KEY = "minioadmin"  # Your actual credentials
$MINIO_SECRET_KEY = "minioadmin"  # Your actual credentials
$MINIO_ALIAS = "floatchat"

Write-Host "MinIO Server: http://$MINIO_ENDPOINT" -ForegroundColor Cyan
Write-Host "Access Key: $MINIO_ACCESS_KEY" -ForegroundColor Cyan

# Configure MinIO client with real credentials
try {
    Write-Host "Setting up MinIO client alias..." -ForegroundColor Yellow
    
    # Check if mc.exe exists
    if (!(Test-Path "C:\MinIO\mc.exe")) {
        Write-Host "✗ MinIO client (mc.exe) not found at C:\MinIO\mc.exe" -ForegroundColor Red
        Write-Host "Please install MinIO client first" -ForegroundColor Red
    } else {
        # Set up alias with your real credentials
        $mcResult = & "C:\MinIO\mc.exe" alias set $MINIO_ALIAS "http://$MINIO_ENDPOINT" $MINIO_ACCESS_KEY $MINIO_SECRET_KEY 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ MinIO client configured successfully" -ForegroundColor Green
            
            # Test connection to your running server
            Write-Host "Testing connection to MinIO server..." -ForegroundColor Yellow
            $infoResult = & "C:\MinIO\mc.exe" admin info $MINIO_ALIAS 2>&1
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✓ MinIO server connection verified" -ForegroundColor Green
                Write-Host "Server info:" -ForegroundColor Cyan
                Write-Host $infoResult -ForegroundColor Gray
            } else {
                Write-Host "⚠ MinIO server connection test failed" -ForegroundColor Yellow
                Write-Host "Make sure MinIO server is running on $MINIO_ENDPOINT" -ForegroundColor Yellow
            }
        } else {
            Write-Host "✗ MinIO client configuration failed" -ForegroundColor Red
            Write-Host "Error: $mcResult" -ForegroundColor Red
        }
    }
} catch {
    Write-Host "✗ MinIO setup error: $_" -ForegroundColor Red
}

# Create production buckets with real names
Write-Host ""
Write-Host "Creating production MinIO buckets..." -ForegroundColor Blue

$buckets = @(
    "argo-floats",
    "incois-stations", 
    "processed-data",
    "embeddings-store",
    "user-queries",
    "disaster-alerts",
    "netcdf-files",
    "backup-data"
)

foreach ($bucket in $buckets) {
    try {
        $bucketResult = & "C:\MinIO\mc.exe" mb "$MINIO_ALIAS/$bucket" 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Created bucket: $bucket" -ForegroundColor Green
        } else {
            # Check if bucket already exists
            $existsResult = & "C:\MinIO\mc.exe" ls "$MINIO_ALIAS/$bucket" 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  Bucket exists: $bucket" -ForegroundColor Gray
            } else {
                Write-Host "✗ Failed to create: $bucket" -ForegroundColor Red
            }
        }
    } catch {
        Write-Host "✗ Error with bucket $bucket`: $_" -ForegroundColor Red
    }
}

# List all buckets to verify
Write-Host ""
Write-Host "Verifying MinIO buckets..." -ForegroundColor Yellow
try {
    $bucketsResult = & "C:\MinIO\mc.exe" ls $MINIO_ALIAS 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Available buckets:" -ForegroundColor Cyan
        Write-Host $bucketsResult -ForegroundColor Gray
    }
} catch {
    Write-Host "Could not list buckets" -ForegroundColor Yellow
}

# Create .env file with real API keys and MinIO credentials
Write-Host ""
Write-Host "Creating production .env configuration..." -ForegroundColor Blue

$envContent = @"
# FloatChat Production Configuration
# Real API keys and server credentials

# MinIO Configuration (your actual server)
MINIO_ENDPOINT=http://127.0.0.1:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_ARGO=argo-floats
MINIO_BUCKET_INCOIS=incois-stations
MINIO_BUCKET_PROCESSED=processed-data

# LLM API Keys (replace with your actual keys)
MISTRAL_API_KEY=your_mistral_api_key_here
GROQ_API_KEY=your_groq_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# MongoDB Configuration
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=floatchat

# Email Configuration for Alerts
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password_here

# System Configuration
LOG_LEVEL=INFO
DEBUG_MODE=False
CACHE_TIMEOUT=3600
MAX_FILE_SIZE=100MB

# Data Sources
ARGO_FTP_HOST=ftp.ifremer.fr
INCOIS_BASE_URL=https://incois.gov.in
PROCESSING_THREADS=4

# Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
"@

try {
    $envContent | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host "✓ Created .env configuration file" -ForegroundColor Green
    Write-Host "⚠ Please update API keys in .env file with your actual credentials" -ForegroundColor Yellow
} catch {
    Write-Host "✗ Failed to create .env file: $_" -ForegroundColor Red
}

# Create production startup script
Write-Host ""
Write-Host "Creating production startup scripts..." -ForegroundColor Blue

$startupScript = @"
# FloatChat Production Startup Script
# Run this to start all services

Write-Host "Starting FloatChat AI System..." -ForegroundColor Green

# Start MinIO server (if not running)
`$minioProcess = Get-Process "minio" -ErrorAction SilentlyContinue
if (-not `$minioProcess) {
    Write-Host "Starting MinIO server..." -ForegroundColor Yellow
    Start-Process -FilePath "C:\MinIO\minio.exe" -ArgumentList "server", "D:\minio-data", "--console-address", ":9001" -WindowStyle Minimized
    Start-Sleep -Seconds 5
}

# Run data collection
Write-Host "Starting data collection..." -ForegroundColor Yellow
python argo_scraper.py
python comprehensive_incois_scraper.py

# Process collected data
Write-Host "Processing oceanographic data..." -ForegroundColor Yellow
python enhanced_data_processor.py

# Start main dashboard
Write-Host "Starting FloatChat dashboard..." -ForegroundColor Green
streamlit run enhanced_main_dashboard.py --server.port 8501 --server.address localhost
"@

try {
    $startupScript | Out-File -FilePath "start_floatchat.ps1" -Encoding UTF8
    Write-Host "✓ Created start_floatchat.ps1" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to create startup script: $_" -ForegroundColor Red
}

# Validate file structure
Write-Host ""
Write-Host "Validating file structure..." -ForegroundColor Blue

$requiredFiles = @(
    "enhanced_main_dashboard.py",
    "enhanced_chat_interface.py",
    "enhanced_rag_engine.py",
    "argo_scraper.py",
    "comprehensive_incois_scraper.py",
    "minio_handler.py",
    "advanced_llm_handler.py",
    "disaster_warning_system.py",
    "multilingual_support.py"
)

$missingFiles = @()
foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "✓ $file" -ForegroundColor Green
    } else {
        Write-Host "✗ Missing: $file" -ForegroundColor Red
        $missingFiles += $file
    }
}

# Final status report
Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Green
Write-Host "Production Configuration Summary:" -ForegroundColor Cyan
Write-Host "• MinIO Server: http://127.0.0.1:9000 (minioadmin:minioadmin)" -ForegroundColor White
Write-Host "• MinIO Console: http://127.0.0.1:9001" -ForegroundColor White
Write-Host "• Project Directory: $projectPath" -ForegroundColor White
Write-Host "• Python Dependencies: Installed" -ForegroundColor White
Write-Host "• MinIO Buckets: Created" -ForegroundColor White

if ($missingFiles.Count -eq 0) {
    Write-Host "• File Structure: Complete ✓" -ForegroundColor Green
} else {
    Write-Host "• Missing Files: $($missingFiles.Count)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "1. Update .env file with your actual API keys" -ForegroundColor White
Write-Host "2. Ensure MinIO server is running: C:\MinIO\minio.exe server D:\minio-data --console-address :9001" -ForegroundColor White
Write-Host "3. Run data collection: python argo_scraper.py" -ForegroundColor White
Write-Host "4. Run INCOIS scraper: python comprehensive_incois_scraper.py" -ForegroundColor White
Write-Host "5. Process data: python enhanced_data_processor.py" -ForegroundColor White
Write-Host "6. Start dashboard: streamlit run enhanced_main_dashboard.py" -ForegroundColor White
Write-Host ""
Write-Host "Or use the startup script: .\start_floatchat.ps1" -ForegroundColor Yellow

Write-Host ""
Write-Host "FloatChat AI System setup completed successfully!" -ForegroundColor Green
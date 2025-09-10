1️⃣ Launch MinIO server
# Navigate to MinIO folder
cd C:\MinIO

# Start MinIO server with data folder and console
.\minio.exe server C:\MinIO\data --console-address ":9001"


Web Console: http://127.0.0.1:9001

Default credentials: minioadmin / minioadmin

⚠️ For production, set environment variables for credentials.

2️⃣ Configure MinIO Client (mc)
# Set alias for local MinIO server
C:\MinIO\mc.exe alias set local http://127.0.0.1:9000 minioadmin minioadmin


Verify alias:

C:\MinIO\mc.exe alias list

3️⃣ Create main bucket
# Create root bucket (ignore error if it exists)
C:\MinIO\mc.exe mb local/incois-data 2>$null

# List buckets to confirm
C:\MinIO\mc.exe ls local

4️⃣ Prepare seasonal data folder
# Create local folder if missing
mkdir "C:\Users\aryan\Downloads\VIIRS-Aug2025"
mkdir "C:\Users\aryan\Downloads\VIIRS-Mar2025"


Copy your .nc files into these folders using normal copy/paste or copy command.

5️⃣ Create seasonal bucket
# August monsoon
$localFolder = "C:\Users\aryan\Downloads\VIIRS-Aug2025"
$bucket = "local/incois-data/2025-08-monsoon"

C:\MinIO\mc.exe mb $bucket 2>$null

# Pre-monsoon
$localFolder2 = "C:\Users\aryan\Downloads\VIIRS-Mar2025"
$bucket2 = "local/incois-data/2025-03-pre-monsoon"

C:\MinIO\mc.exe mb $bucket2 2>$null

6️⃣ Upload .nc files safely
# August monsoon files
Get-ChildItem $localFolder -Filter *.nc -File | ForEach-Object {
    C:\MinIO\mc.exe cp "$($_.FullName)" "$bucket/"
}

# Pre-monsoon files
Get-ChildItem $localFolder2 -Filter *.nc -File | ForEach-Object {
    C:\MinIO\mc.exe cp "$($_.FullName)" "$bucket2/"
}


This handles spaces and parentheses in filenames correctly.

7️⃣ Verify uploaded files
# Check August monsoon bucket
C:\MinIO\mc.exe ls $bucket

# Check Pre-monsoon bucket
C:\MinIO\mc.exe ls $bucket2


✅ At this point, all your seasonal VIIRS .nc files are safely uploaded to MinIO buckets:

local/incois-data/2025-08-monsoon

local/incois-data/2025-03-pre-monsoon

If you want, I can also make a single reusable PowerShell script that automatically finds any new seasonal folder and uploads it to MinIO without manually setting $localFolder each time.

Do you want me to create that script?




#️⃣ Alternative: Launch MinIO from Command Prompt















Launch MinIO from VSCode Terminal

Open VSCode → Terminal → New Terminal

Navigate to MinIO folder:

cd C:\MinIO


Start MinIO server:

.\minio.exe server C:\MinIO\data --console-address ":9001"


Web Console: http://127.0.0.1:9001

Default credentials: minioadmin / minioadmin (set new ones with env variables for production)






(base) PS D:\FloatChat ARGO> C:\MinIO\mc.exe alias set local 

http://127.0.0.1:9000 minioadmin minioadmin

Added `local` successfully.

(base) PS D:\FloatChat ARGO> C:\MinIO\mc.exe mb local/incois-data

mc.exe: <ERROR> Unable to make bucket `local/incois-data`. Your previous request to create the named bucket succeeded and you already own it.

(base) PS D:\FloatChat ARGO> C:\MinIO\mc.exe ls local

[2025-08-29 19:27:28 IST]     0B incois-data/

(base) PS D:\FloatChat ARGO> C:\MinIO\mc.exe ls local

[2025-08-29 19:27:28 IST]     0B incois-data/

(base) PS D:\FloatChat ARGO> [date]  0B  incois-data/            
ParserError: 
Line |
   1 |  [date]  0B  incois-data/
     |          ~~
     | Unexpected token '0B' in expression or statement.
(base) PS D:\FloatChat ARGO> 











(base) PS D:\FloatChat ARGO> 
(base) PS D:\FloatChat ARGO> # Define seasonal folder and MinIO bucket
(base) PS D:\FloatChat ARGO> $localFolder = "C:\Users\aryan\Downloads\VIIRS-Aug2025"
(base) PS D:\FloatChat ARGO> $bucket = "local/incois-data/2025-08-monsoon"
(base) PS D:\FloatChat ARGO> 
(base) PS D:\FloatChat ARGO> # Create bucket if it doesn't exist (suppress error if it already exists)
(base) PS D:\FloatChat ARGO> C:\MinIO\mc.exe mb $bucket 2>$null
Bucket created successfully `local/incois-data/2025-08-monsoon`.
(base) PS D:\FloatChat ARGO> 
(base) PS D:\FloatChat ARGO> # Upload all .nc files safely
(base) PS D:\FloatChat ARGO> Get-ChildItem $localFolder -Filter *.nc -File | ForEach-Object {
>>     C:\MinIO\mc.exe cp "$($_.FullName)" "$bucket/"
>> }
...-SST.nc: 8.26 MiB / 8.26 MiB [==============] 132.29 MiB/s 0s
(base) PS D:\FloatChat ARGO> 
(base) PS D:\FloatChat ARGO> # Verify upload
(base) PS D:\FloatChat ARGO> C:\MinIO\mc.exe ls $bucket          
[2025-08-29 20:09:08 IST]     0B STANDARD /
[2025-08-29 20:09:08 IST] 8.3MiB STANDARD VIIRS-SNPP-Aug2025-d05-4KM-PICountries-AOT (1).nc
[2025-08-29 20:09:09 IST] 8.3MiB STANDARD VIIRS-SNPP-Aug2025-d05-4KM-PICountries-AOT.nc
[2025-08-29 20:09:09 IST] 8.3MiB STANDARD VIIRS-SNPP-Aug2025-d05-4KM-PICountries-CHL.nc
[2025-08-29 20:09:09 IST] 8.3MiB STANDARD VIIRS-SNPP-Aug2025-d05-4KM-PICountries-K490 (1).nc
[2025-08-29 20:09:09 IST] 8.3MiB STANDARD VIIRS-SNPP-Aug2025-d05-4KM-PICountries-K490.nc
[2025-08-29 20:09:09 IST] 8.3MiB STANDARD VIIRS-SNPP-Aug2025-d05-4KM-PICountries-PIC.nc
[2025-08-29 20:09:10 IST] 8.3MiB STANDARD VIIRS-SNPP-Aug2025-d05-4KM-PICountries-POC (1).nc
[2025-08-29 20:09:10 IST] 8.3MiB STANDARD VIIRS-SNPP-Aug2025-d05-4KM-PICountries-POC.nc
[2025-08-29 20:09:10 IST] 8.3MiB STANDARD VIIRS-SNPP-Aug2025-d05-4KM-PICountries-SST (1).nc
[2025-08-29 20:09:10 IST] 8.3MiB STANDARD VIIRS-SNPP-Aug2025-d05-4KM-PICountries-SST.nc
(base) PS D:\FloatChat ARGO> 





$localFolder = "C:\Users\aryan\Downloads\VIIRS-Mar2025"
$bucket = "local/incois-data/2025-03-pre-monsoon"
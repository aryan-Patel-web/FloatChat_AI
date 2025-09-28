from google.cloud import storage
from google.oauth2 import service_account
from pathlib import Path
import os
from datetime import datetime
import json

def upload_json_files_to_gcs(bucket_name, source_dir, credentials_path, destination_prefix=''):
    """Upload JSON files to GCS"""
    
    # Load credentials from file
    try:
        with open(credentials_path, 'r') as f:
            creds_info = json.load(f)
        
        credentials = service_account.Credentials.from_service_account_info(creds_info)
        print(f"✅ Credentials loaded successfully")
        print(f"   Project ID: {creds_info.get('project_id')}")
        
    except FileNotFoundError:
        print(f"❌ Error: File not found at {credentials_path}")
        return
    except json.JSONDecodeError:
        print(f"❌ Error: Invalid JSON in credentials file")
        return
    
    # Initialize storage client
    try:
        storage_client = storage.Client(credentials=credentials, project=creds_info['project_id'])
        bucket = storage_client.bucket(bucket_name)
        print(f"✅ Connected to bucket: {bucket_name}\n")
    except Exception as e:
        print(f"❌ Error connecting to GCS: {e}")
        return
    
    # Get all JSON files
    source_path = Path(source_dir)
    json_files = list(source_path.rglob("*.json"))
    
    total_files = len(json_files)
    total_size_mb = sum(f.stat().st_size for f in json_files) / (1024 * 1024)
    
    print(f"📊 Upload Summary:")
    print(f"   Total files: {total_files}")
    print(f"   Total size: {total_size_mb:.2f} MB")
    print(f"\n🚀 Starting upload...\n")
    
    uploaded = 0
    failed = 0
    
    for idx, file_path in enumerate(json_files, 1):
        try:
            relative_path = file_path.relative_to(source_path)
            blob_name = f"{destination_prefix}{relative_path}".replace("\\", "/")
            
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(str(file_path))
            
            uploaded += 1
            
            percent = (idx / total_files) * 100
            if idx % 10 == 0 or idx == total_files:
                print(f"✓ [{idx}/{total_files}] ({percent:.1f}%) uploaded")
            
        except Exception as e:
            failed += 1
            print(f"✗ [{idx}/{total_files}] Failed: {file_path.name} - {str(e)}")
    
    print(f"\n{'='*60}")
    print(f"✅ Upload Complete!")
    print(f"   Successfully uploaded: {uploaded} files")
    print(f"   Failed: {failed} files")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    # Configuration
    BUCKET_NAME = "floatchat-ai-data"
    SOURCE_DIR = r"D:\FloatChat ARGO\MINIO\Datasetjson"
    CREDENTIALS_PATH = r"D:\FloatChat ARGO\MINIO\gcs-key.json"
    DESTINATION_PREFIX = "Datasetjson/"
    
    # Verify paths
    if not Path(CREDENTIALS_PATH).exists():
        print(f"❌ Credentials file not found: {CREDENTIALS_PATH}")
        exit(1)
    
    if not Path(SOURCE_DIR).exists():
        print(f"❌ Source directory not found: {SOURCE_DIR}")
        exit(1)
    
    # Start upload
    start_time = datetime.now()
    upload_json_files_to_gcs(BUCKET_NAME, SOURCE_DIR, CREDENTIALS_PATH, DESTINATION_PREFIX)
    
    duration = (datetime.now() - start_time).total_seconds()
    print(f"⏱️  Total time: {duration:.2f} seconds")
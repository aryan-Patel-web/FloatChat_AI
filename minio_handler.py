"""
MinIO Handler for FloatChat - SYNTAX ERROR FIXED  
Fixed unclosed parenthesis on line 214
Handles object storage for ARGO NetCDF files
"""
import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib

# Import MinIO if available
try:
    from minio import Minio
    from minio.error import S3Error
    MINIO_AVAILABLE = True
except ImportError:
    MINIO_AVAILABLE = False
    logging.warning("MinIO client not available. Install with: pip install minio")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MinIOHandler:
    """Enhanced MinIO handler for ARGO data storage and retrieval"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.client = None
        self.bucket_name = self.config.get('bucket_name', 'floatchat-argo')
        self.connected = False
        
        if MINIO_AVAILABLE:
            self._initialize_client()
        else:
            logger.warning("MinIO not available - using local file storage fallback")
    
    def _load_config(self, config_path: Optional[str] = None) -> Dict:
        """Load MinIO configuration with secure defaults"""
        default_config = {
            'endpoint': 'localhost:9000',
            'access_key': 'minioadmin', 
            'secret_key': 'minioadmin',
            'bucket_name': 'floatchat-argo',
            'secure': False,
            'region': 'us-east-1',
            'local_cache_dir': 'cache'
        }
        
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                return {**default_config, **loaded_config}
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")
        
        # Try to load from environment variables
        env_config = {
            'endpoint': os.getenv('MINIO_ENDPOINT', default_config['endpoint']),
            'access_key': os.getenv('MINIO_ACCESS_KEY', default_config['access_key']),
            'secret_key': os.getenv('MINIO_SECRET_KEY', default_config['secret_key']),
            'bucket_name': os.getenv('MINIO_BUCKET', default_config['bucket_name']),
            'secure': os.getenv('MINIO_SECURE', 'false').lower() == 'true'
        }
        
        return {**default_config, **env_config}
    
    def _initialize_client(self):
        """Initialize MinIO client with error handling"""
        if not MINIO_AVAILABLE:
            return False
        
        try:
            self.client = Minio(
                endpoint=self.config['endpoint'],
                access_key=self.config['access_key'],
                secret_key=self.config['secret_key'],
                secure=self.config['secure'],
                region=self.config['region']
            )
            
            # Test connection
            self.client.bucket_exists(self.bucket_name)
            self.connected = True
            logger.info(f"Connected to MinIO at {self.config['endpoint']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MinIO: {e}")
            self.connected = False
            return False
    
    def ensure_bucket_exists(self) -> bool:
        """Ensure the bucket exists, create if necessary"""
        if not self.connected or not self.client:
            return False
        
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to ensure bucket exists: {e}")
            return False
    
    def upload_file(self, local_path: str, object_name: Optional[str] = None) -> bool:
        """Upload a file to MinIO with metadata"""
        if not self.connected:
            return self._local_file_copy(local_path, object_name)
        
        if not object_name:
            object_name = Path(local_path).name
        
        try:
            self.ensure_bucket_exists()
            
            # Add metadata
            metadata = {
                'upload_time': datetime.now().isoformat(),
                'file_size': str(Path(local_path).stat().st_size),
                'source': 'floatchat-system',
                'content_type': self._get_content_type(local_path)
            }
            
            self.client.fput_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                file_path=local_path,
                metadata=metadata
            )
            
            logger.info(f"Uploaded {local_path} as {object_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload {local_path}: {e}")
            return False
    
    def download_file(self, object_name: str, local_path: Optional[str] = None) -> bool:
        """Download a file from MinIO"""
        if not self.connected:
            return self._local_file_retrieve(object_name, local_path)
        
        if not local_path:
            local_path = object_name
        
        try:
            self.client.fget_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                file_path=local_path
            )
            
            logger.info(f"Downloaded {object_name} to {local_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download {object_name}: {e}")
            return False
    
    def list_objects(self, prefix: str = "", recursive: bool = True) -> List[Dict]:
        """List objects in the bucket with metadata"""
        if not self.connected:
            return self._local_file_list(prefix)
        
        try:
            objects = []
            for obj in self.client.list_objects(self.bucket_name, prefix=prefix, recursive=recursive):
                objects.append({
                    'name': obj.object_name,
                    'size': obj.size,
                    'last_modified': obj.last_modified.isoformat() if obj.last_modified else None,
                    'etag': obj.etag,
                    'content_type': obj.content_type
                })
            
            logger.info(f"Found {len(objects)} objects with prefix '{prefix}'")
            return objects
            
        except Exception as e:
            logger.error(f"Failed to list objects: {e}")
            return []
    
    def delete_object(self, object_name: str) -> bool:
        """Delete an object from MinIO"""
        if not self.connected:
            return self._local_file_delete(object_name)
        
        try:
            self.client.remove_object(self.bucket_name, object_name)
            logger.info(f"Deleted object: {object_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete {object_name}: {e}")
            return False
    
    def get_object_metadata(self, object_name: str) -> Optional[Dict]:
        """Get metadata for an object"""
        if not self.connected:
            return self._local_file_metadata(object_name)
        
        try:
            response = self.client.stat_object(self.bucket_name, object_name)
            return {
                'name': object_name,
                'size': response.size,
                'last_modified': response.last_modified.isoformat() if response.last_modified else None,
                'etag': response.etag,
                'content_type': response.content_type,
                'metadata': response.metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to get metadata for {object_name}: {e}")
            return None
    
    def _get_content_type(self, file_path: str) -> str:
        """Determine content type based on file extension"""
        extension = Path(file_path).suffix.lower()
        content_types = {
            '.nc': 'application/x-netcdf',
            '.json': 'application/json',
            '.csv': 'text/csv',
            '.txt': 'text/plain',
            '.pdf': 'application/pdf',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg'
        }
        return content_types.get(extension, 'application/octet-stream')
    
    # Fallback methods for local storage when MinIO unavailable
    def _local_file_copy(self, local_path: str, object_name: Optional[str] = None) -> bool:
        """Copy file to local cache directory"""
        try:
            cache_dir = Path(self.config['local_cache_dir'])
            cache_dir.mkdir(exist_ok=True)
            
            if not object_name:
                object_name = Path(local_path).name
            
            target_path = cache_dir / object_name
            
            import shutil
            shutil.copy2(local_path, target_path)
            
            # Store metadata
            metadata = {
                'upload_time': datetime.now().isoformat(),
                'file_size': target_path.stat().st_size,
                'source_path': local_path,
                'cached_path': str(target_path)
            }
            
            metadata_file = target_path.with_suffix(target_path.suffix + '.meta')
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Cached {local_path} as {target_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache file locally: {e}")
            return False
    
    def _local_file_retrieve(self, object_name: str, local_path: Optional[str] = None) -> bool:
        """Retrieve file from local cache"""
        try:
            cache_dir = Path(self.config['local_cache_dir'])
            cached_file = cache_dir / object_name
            
            if not cached_file.exists():
                logger.error(f"File not found in cache: {object_name}")
                return False
            
            if not local_path:
                local_path = object_name
            
            import shutil
            shutil.copy2(cached_file, local_path)
            
            logger.info(f"Retrieved {object_name} from cache to {local_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to retrieve from cache: {e}")
            return False
    
    def _local_file_list(self, prefix: str = "") -> List[Dict]:
        """List files in local cache"""
        try:
            cache_dir = Path(self.config['local_cache_dir'])
            if not cache_dir.exists():
                return []
            
            objects = []
            pattern = f"{prefix}*" if prefix else "*"
            
            for file_path in cache_dir.glob(pattern):
                if file_path.suffix == '.meta':
                    continue
                
                stat = file_path.stat()
                objects.append({
                    'name': file_path.name,
                    'size': stat.st_size,
                    'last_modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'path': str(file_path)
                })
            
            return objects
            
        except Exception as e:
            logger.error(f"Failed to list cached files: {e}")
            return []
    
    def _local_file_delete(self, object_name: str) -> bool:
        """Delete file from local cache"""
        try:
            cache_dir = Path(self.config['local_cache_dir'])
            cached_file = cache_dir / object_name
            metadata_file = cached_file.with_suffix(cached_file.suffix + '.meta')
            
            if cached_file.exists():
                cached_file.unlink()
            if metadata_file.exists():
                metadata_file.unlink()
            
            logger.info(f"Deleted cached file: {object_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete cached file: {e}")
            return False
    
    def _local_file_metadata(self, object_name: str) -> Optional[Dict]:
        """Get metadata for cached file"""
        try:
            cache_dir = Path(self.config['local_cache_dir'])
            cached_file = cache_dir / object_name
            metadata_file = cached_file.with_suffix(cached_file.suffix + '.meta')
            
            if not cached_file.exists():
                return None
            
            metadata = {}
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
            
            stat = cached_file.stat()
            return {
                'name': object_name,
                'size': stat.st_size,
                'last_modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'path': str(cached_file),
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to get cached file metadata: {e}")
            return None
    
    def upload_argo_data(self, argo_files: List[str]) -> Dict[str, bool]:
        """Upload multiple ARGO NetCDF files"""
        results = {}
        
        for file_path in argo_files:
            file_name = Path(file_path).name
            object_name = f"argo/{file_name}"
            results[file_name] = self.upload_file(file_path, object_name)
        
        successful = sum(1 for success in results.values() if success)
        logger.info(f"Uploaded {successful}/{len(argo_files)} ARGO files")
        
        return results
    
    def sync_local_argo_data(self, local_dir: str = "data") -> Dict[str, Any]:
        """Synchronize local ARGO data with MinIO"""
        sync_stats = {
            'uploaded': 0,
            'failed': 0,
            'skipped': 0,
            'total_size': 0
        }
        
        local_path = Path(local_dir)
        if not local_path.exists():
            logger.warning(f"Local directory not found: {local_dir}")
            return sync_stats
        
        # Find all NetCDF files
        nc_files = list(local_path.glob("**/*.nc"))
        
        for nc_file in nc_files:
            try:
                # Check if already exists
                object_name = f"argo/{nc_file.name}"
                existing_meta = self.get_object_metadata(object_name)
                
                file_size = nc_file.stat().st_size
                
                if existing_meta and existing_meta['size'] == file_size:
                    sync_stats['skipped'] += 1
                    continue
                
                if self.upload_file(str(nc_file), object_name):
                    sync_stats['uploaded'] += 1
                    sync_stats['total_size'] += file_size
                else:
                    sync_stats['failed'] += 1
                    
            except Exception as e:
                logger.error(f"Failed to sync {nc_file}: {e}")
                sync_stats['failed'] += 1
        
        logger.info(f"Sync completed: {sync_stats['uploaded']} uploaded, {sync_stats['skipped']} skipped, {sync_stats['failed']} failed")
        return sync_stats
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        if not self.connected:
            return self._get_local_storage_stats()
        
        try:
            objects = self.list_objects()
            
            total_size = sum(obj['size'] for obj in objects)
            file_types = {}
            
            for obj in objects:
                ext = Path(obj['name']).suffix
                file_types[ext] = file_types.get(ext, 0) + 1
            
            return {
                'total_objects': len(objects),
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'file_types': file_types,
                'bucket': self.bucket_name,
                'endpoint': self.config['endpoint'],
                'connected': self.connected
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {'error': str(e)}
    
    def _get_local_storage_stats(self) -> Dict[str, Any]:
        """Get local cache storage statistics"""
        try:
            cache_dir = Path(self.config['local_cache_dir'])
            if not cache_dir.exists():
                return {'total_objects': 0, 'total_size_bytes': 0, 'connected': False}
            
            files = list(cache_dir.glob("*"))
            # Exclude metadata files
            data_files = [f for f in files if not f.name.endswith('.meta')]
            
            total_size = sum(f.stat().st_size for f in data_files)
            file_types = {}
            
            for file_path in data_files:
                ext = file_path.suffix
                file_types[ext] = file_types.get(ext, 0) + 1
            
            return {
                'total_objects': len(data_files),
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'file_types': file_types,
                'cache_dir': str(cache_dir),
                'connected': False
            }
            
        except Exception as e:
            logger.error(f"Failed to get local storage stats: {e}")
            return {'error': str(e)}

def test_minio_handler():
    """Test MinIO handler functionality"""
    print("Testing MinIO Handler...")
    
    handler = MinIOHandler()
    
    # Test connection
    print(f"Connected: {handler.connected}")
    
    # Test storage stats
    stats = handler.get_storage_stats()
    print(f"Storage Stats:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Test file operations if we have test files
    test_files = list(Path('.').glob("*.json"))[:2]  # Test with JSON files
    
    if test_files:
        print(f"\nTesting with {len(test_files)} files...")
        
        for test_file in test_files:
            object_name = f"test/{test_file.name}"
            
            # Upload
            success = handler.upload_file(str(test_file), object_name)
            print(f"Upload {test_file.name}: {'SUCCESS' if success else 'FAILED'}")
            
            if success:
                # Get metadata
                metadata = handler.get_object_metadata(object_name)
                if metadata:
                    print(f"  Size: {metadata['size']} bytes")
                
                # Download to temp location
                temp_path = f"temp_{test_file.name}"
                download_success = handler.download_file(object_name, temp_path)
                print(f"Download: {'SUCCESS' if download_success else 'FAILED'}")
                
                # Clean up
                if Path(temp_path).exists():
                    Path(temp_path).unlink()
                
                # Delete from storage
                delete_success = handler.delete_object(object_name)
                print(f"Delete: {'SUCCESS' if delete_success else 'FAILED'}")
    
    # List objects
    objects = handler.list_objects()
    print(f"\nTotal objects in storage: {len(objects)}")
    for obj in objects[:5]:  # Show first 5
        print(f"  {obj['name']} ({obj['size']} bytes)")
    
    print("MinIO Handler test completed!")

if __name__ == "__main__":
    test_minio_handler()
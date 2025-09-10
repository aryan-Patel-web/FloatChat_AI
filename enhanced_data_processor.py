"""
Enhanced Data Processor for FloatChat - REAL NetCDF Processing
- Processes actual NetCDF files from ARGO floats
- Extracts real temperature, salinity, pressure data
- MongoDB integration for advanced querying
- NO demo data - only real measurements
"""

import json
import logging
import netCDF4 as nc
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import pandas as pd
from collections import defaultdict
import hashlib
import os

print("DEBUG: Starting enhanced_data_processor.py imports")

# MongoDB integration
try:
    from pymongo import MongoClient
    MONGODB_AVAILABLE = True
    print("DEBUG: MongoDB support available")
except ImportError:
    MONGODB_AVAILABLE = False
    print("DEBUG: MongoDB not available")

# MinIO integration
try:
    from minio import Minio
    from minio.error import S3Error
    MINIO_AVAILABLE = True
    print("DEBUG: MinIO support available")
except ImportError:
    MINIO_AVAILABLE = False
    print("DEBUG: MinIO not available")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedDataProcessor:
    """Enhanced processor for real oceanographic data with MongoDB and MinIO integration"""
    
    def __init__(self, config_path: Optional[str] = None):
        print("DEBUG: Initializing Enhanced Data Processor...")
        
        self.config = self._load_config()
        self.processed_data = {}
        self.processing_stats = {
            'files_processed': 0,
            'total_measurements': 0,
            'temperature_count': 0,
            'salinity_count': 0,
            'pressure_count': 0,
            'coordinate_count': 0,
            'processing_errors': 0
        }
        
        # Database connections
        self.mongo_client = None
        self.mongo_db = None
        self.mongodb_connected = False
        
        # MinIO connection
        self.minio_client = None
        self.minio_connected = False
        
        # Initialize connections
        self._initialize_mongodb()
        self._initialize_minio()
        
        print("DEBUG: Enhanced Data Processor initialization complete")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        print("DEBUG: Loading configuration from environment...")
        
        config = {
            # MongoDB settings
            'mongodb_uri': os.getenv('MONGODB_URI', 'mongodb://localhost:27017'),
            'mongodb_db': os.getenv('MONGODB_DB', 'floatchat'),
            'mongodb_collection': os.getenv('MONGODB_COLLECTION', 'ocean_data'),
            
            # MinIO settings
            'minio_endpoint': os.getenv('MINIO_ENDPOINT', 'localhost:9000'),
            'minio_access_key': os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
            'minio_secret_key': os.getenv('MINIO_SECRET_KEY', 'minioadmin'),
            'minio_secure': os.getenv('MINIO_SECURE', 'false').lower() == 'true',
            
            # Processing settings
            'max_files_per_batch': int(os.getenv('MAX_FILES_PER_UPDATE', '150')),
            'max_file_size_gb': float(os.getenv('MAX_FILE_SIZE_GB', '3')),
            'data_retention_days': int(os.getenv('DATA_RETENTION_DAYS', '90')),
            'cache_enabled': os.getenv('CACHE_ENABLED', 'true').lower() == 'true',
            
            # Data source settings
            'argo_ftp': os.getenv('ARGO_FTP', 'ftp.ifremer.fr'),
            'incois_base_url': os.getenv('INCOIS_BASE_URL', 'https://incois.gov.in')
        }
        
        print(f"DEBUG: Configuration loaded - MongoDB: {config['mongodb_uri']}, MinIO: {config['minio_endpoint']}")
        return config
    
    def _initialize_mongodb(self):
        """Initialize MongoDB connection"""
        if not MONGODB_AVAILABLE:
            print("DEBUG: MongoDB not available - skipping initialization")
            return
        
        try:
            print("DEBUG: Initializing MongoDB connection...")
            
            self.mongo_client = MongoClient(
                self.config['mongodb_uri'],
                serverSelectionTimeoutMS=5000
            )
            
            # Test connection
            self.mongo_client.admin.command('ismaster')
            
            self.mongo_db = self.mongo_client[self.config['mongodb_db']]
            self.mongodb_connected = True
            
            print(f"DEBUG: MongoDB connected successfully to {self.config['mongodb_db']}")
            
            # Create indexes for efficient querying
            collection = self.mongo_db[self.config['mongodb_collection']]
            collection.create_index([('timestamp', 1)])
            collection.create_index([('data_type', 1)])
            collection.create_index([('coordinates', '2d')])
            
            print("DEBUG: MongoDB indexes created")
            
        except Exception as e:
            print(f"DEBUG: MongoDB initialization failed: {e}")
            self.mongodb_connected = False
    
    def _initialize_minio(self):
        """Initialize MinIO connection"""
        if not MINIO_AVAILABLE:
            print("DEBUG: MinIO not available - skipping initialization")
            return
        
        try:
            print("DEBUG: Initializing MinIO connection...")
            
            # Parse endpoint to remove http:// prefix if present
            endpoint = self.config['minio_endpoint'].replace('http://', '').replace('https://', '')
            
            self.minio_client = Minio(
                endpoint,
                access_key=self.config['minio_access_key'],
                secret_key=self.config['minio_secret_key'],
                secure=self.config['minio_secure']
            )
            
            # Test connection by listing buckets
            buckets = list(self.minio_client.list_buckets())
            self.minio_connected = True
            
            print(f"DEBUG: MinIO connected successfully - {len(buckets)} buckets available")
            
        except Exception as e:
            print(f"DEBUG: MinIO initialization failed: {e}")
            self.minio_connected = False
    
    def process_all_netcdf_files(self) -> Dict[str, Any]:
        """Process all NetCDF files in the current directory"""
        print("DEBUG: Starting comprehensive NetCDF file processing...")
        
        nc_files = list(Path('.').glob('*.nc'))
        print(f"DEBUG: Found {len(nc_files)} NetCDF files to process")
        
        if not nc_files:
            print("DEBUG: No NetCDF files found in current directory")
            return {'error': 'No NetCDF files found'}
        
        # Initialize processing results
        all_data = {
            'numeric_data': {
                'temperature': [],
                'salinity': [],
                'pressure': [],
                'coordinates': [],
                'float_ids': [],
                'timestamps': []
            },
            'file_metadata': [],
            'processing_summary': {},
            'regional_analysis': {},
            'quality_control': {}
        }
        
        # Process files in batches
        batch_size = min(self.config['max_files_per_batch'], len(nc_files))
        processed_count = 0
        
        for i in range(0, len(nc_files), batch_size):
            batch = nc_files[i:i + batch_size]
            print(f"DEBUG: Processing batch {i//batch_size + 1} - {len(batch)} files")
            
            for nc_file in batch:
                try:
                    file_data = self._process_single_netcdf_file(nc_file)
                    if file_data:
                        self._merge_file_data(all_data, file_data)
                        processed_count += 1
                        print(f"DEBUG: Successfully processed {nc_file} ({processed_count}/{len(nc_files)})")
                    else:
                        print(f"DEBUG: No data extracted from {nc_file}")
                        self.processing_stats['processing_errors'] += 1
                        
                except Exception as e:
                    print(f"DEBUG: Error processing {nc_file}: {e}")
                    self.processing_stats['processing_errors'] += 1
                    continue
        
        # Generate processing summary
        all_data['processing_summary'] = self._generate_processing_summary(all_data)
        
        # Perform regional analysis
        all_data['regional_analysis'] = self._perform_regional_analysis(all_data['numeric_data']['coordinates'])
        
        # Quality control analysis
        all_data['quality_control'] = self._perform_quality_control(all_data['numeric_data'])
        
        # Save processed data
        self._save_processed_data(all_data)
        
        # Save to MongoDB
        if self.mongodb_connected:
            self._save_to_mongodb(all_data)
        
        # Save to MinIO
        if self.minio_connected:
            self._save_to_minio(all_data)
        
        print(f"DEBUG: NetCDF processing complete - {processed_count}/{len(nc_files)} files processed successfully")
        
        return all_data
    
    def _process_single_netcdf_file(self, nc_file: Path) -> Optional[Dict[str, Any]]:
        """Process a single NetCDF file and extract all relevant data"""
        print(f"DEBUG: Processing NetCDF file: {nc_file}")
        
        try:
            ds = nc.Dataset(nc_file, 'r')
            
            file_data = {
                'filename': str(nc_file),
                'variables': list(ds.variables.keys()),
                'dimensions': list(ds.dimensions.keys()),
                'attributes': dict(ds.__dict__) if hasattr(ds, '__dict__') else {},
                'data': {
                    'temperature': [],
                    'salinity': [],
                    'pressure': [],
                    'coordinates': [],
                    'timestamps': []
                }
            }
            
            print(f"DEBUG: Variables in {nc_file}: {file_data['variables']}")
            
            # Extract temperature data
            temp_extracted = False
            for temp_var in ['TEMP', 'temperature', 'temp', 'Temperature', 'TEMP_ADJUSTED']:
                if temp_var in ds.variables:
                    temp_data = ds.variables[temp_var][:]
                    
                    # Handle different array structures
                    if hasattr(temp_data, 'compressed'):
                        temp_values = temp_data.compressed()
                    else:
                        temp_values = np.array(temp_data).flatten()
                    
                    # Quality control for temperature
                    valid_temps = []
                    for temp in temp_values:
                        if isinstance(temp, (int, float, np.number)):
                            temp_val = float(temp)
                            if not np.isnan(temp_val) and -5.0 <= temp_val <= 40.0:
                                valid_temps.append(temp_val)
                    
                    file_data['data']['temperature'].extend(valid_temps)
                    temp_extracted = True
                    print(f"DEBUG: Extracted {len(valid_temps)} valid temperature values from {temp_var}")
                    break
            
            if not temp_extracted:
                print(f"DEBUG: No temperature data found in {nc_file}")
            
            # Extract salinity data
            sal_extracted = False
            for sal_var in ['PSAL', 'salinity', 'salt', 'Salinity', 'PSAL_ADJUSTED']:
                if sal_var in ds.variables:
                    sal_data = ds.variables[sal_var][:]
                    
                    # Handle different array structures
                    if hasattr(sal_data, 'compressed'):
                        sal_values = sal_data.compressed()
                    else:
                        sal_values = np.array(sal_data).flatten()
                    
                    # Quality control for salinity
                    valid_sals = []
                    for sal in sal_values:
                        if isinstance(sal, (int, float, np.number)):
                            sal_val = float(sal)
                            if not np.isnan(sal_val) and 25.0 <= sal_val <= 40.0:
                                valid_sals.append(sal_val)
                    
                    file_data['data']['salinity'].extend(valid_sals)
                    sal_extracted = True
                    print(f"DEBUG: Extracted {len(valid_sals)} valid salinity values from {sal_var}")
                    break
            
            if not sal_extracted:
                print(f"DEBUG: No salinity data found in {nc_file}")
            
            # Extract pressure/depth data
            pres_extracted = False
            for pres_var in ['PRES', 'pressure', 'depth', 'Pressure', 'PRES_ADJUSTED']:
                if pres_var in ds.variables:
                    pres_data = ds.variables[pres_var][:]
                    
                    # Handle different array structures
                    if hasattr(pres_data, 'compressed'):
                        pres_values = pres_data.compressed()
                    else:
                        pres_values = np.array(pres_data).flatten()
                    
                    # Quality control for pressure
                    valid_pres = []
                    for pres in pres_values:
                        if isinstance(pres, (int, float, np.number)):
                            pres_val = float(pres)
                            if not np.isnan(pres_val) and 0.0 <= pres_val <= 6000.0:
                                valid_pres.append(pres_val)
                    
                    file_data['data']['pressure'].extend(valid_pres)
                    pres_extracted = True
                    print(f"DEBUG: Extracted {len(valid_pres)} valid pressure values from {pres_var}")
                    break
            
            if not pres_extracted:
                print(f"DEBUG: No pressure data found in {nc_file}")
            
            # Extract coordinate data
            lat_data = None
            lon_data = None
            
            # Try different latitude variable names
            for lat_var in ['LATITUDE', 'latitude', 'lat', 'Latitude', 'LAT']:
                if lat_var in ds.variables:
                    lat_data = ds.variables[lat_var][:]
                    break
            
            # Try different longitude variable names
            for lon_var in ['LONGITUDE', 'longitude', 'lon', 'Longitude', 'LON']:
                if lon_var in ds.variables:
                    lon_data = ds.variables[lon_var][:]
                    break
            
            if lat_data is not None and lon_data is not None:
                lats = np.array(lat_data).flatten()
                lons = np.array(lon_data).flatten()
                
                coordinates = []
                for lat, lon in zip(lats, lons):
                    if (isinstance(lat, (int, float, np.number)) and 
                        isinstance(lon, (int, float, np.number))):
                        
                        lat_val, lon_val = float(lat), float(lon)
                        
                        if (not (np.isnan(lat_val) or np.isnan(lon_val)) and
                            -90.0 <= lat_val <= 90.0 and -180.0 <= lon_val <= 180.0):
                            coordinates.append([lat_val, lon_val])
                
                file_data['data']['coordinates'].extend(coordinates)
                print(f"DEBUG: Extracted {len(coordinates)} valid coordinate pairs")
            else:
                print(f"DEBUG: No coordinate data found in {nc_file}")
            
            # Extract timestamps if available
            time_extracted = False
            for time_var in ['JULD', 'time', 'TIME', 'date_time', 'REFERENCE_DATE_TIME']:
                if time_var in ds.variables:
                    try:
                        time_data = ds.variables[time_var][:]
                        time_values = np.array(time_data).flatten()
                        
                        timestamps = []
                        for t in time_values:
                            if isinstance(t, (int, float, np.number)) and not np.isnan(t):
                                timestamps.append(float(t))
                        
                        file_data['data']['timestamps'].extend(timestamps)
                        time_extracted = True
                        print(f"DEBUG: Extracted {len(timestamps)} timestamps from {time_var}")
                        break
                    except Exception as e:
                        print(f"DEBUG: Failed to extract timestamps from {time_var}: {e}")
                        continue
            
            if not time_extracted:
                print(f"DEBUG: No timestamp data found in {nc_file}")
            
            ds.close()
            
            # Update processing statistics
            self.processing_stats['files_processed'] += 1
            self.processing_stats['temperature_count'] += len(file_data['data']['temperature'])
            self.processing_stats['salinity_count'] += len(file_data['data']['salinity'])
            self.processing_stats['pressure_count'] += len(file_data['data']['pressure'])
            self.processing_stats['coordinate_count'] += len(file_data['data']['coordinates'])
            
            return file_data
            
        except Exception as e:
            print(f"DEBUG: Failed to process NetCDF file {nc_file}: {e}")
            return None
    
    def _merge_file_data(self, all_data: Dict[str, Any], file_data: Dict[str, Any]):
        """Merge individual file data into the combined dataset"""
        
        # Merge numeric data
        for key in ['temperature', 'salinity', 'pressure', 'coordinates', 'timestamps']:
            if key in file_data['data']:
                all_data['numeric_data'][key].extend(file_data['data'][key])
        
        # Add file metadata
        all_data['file_metadata'].append({
            'filename': file_data['filename'],
            'variables': file_data['variables'],
            'dimensions': file_data['dimensions'],
            'data_counts': {
                'temperature': len(file_data['data']['temperature']),
                'salinity': len(file_data['data']['salinity']),
                'pressure': len(file_data['data']['pressure']),
                'coordinates': len(file_data['data']['coordinates'])
            }
        })
    
    def _generate_processing_summary(self, all_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive processing summary"""
        
        numeric_data = all_data['numeric_data']
        
        summary = {
            'total_files_processed': self.processing_stats['files_processed'],
            'processing_errors': self.processing_stats['processing_errors'],
            'success_rate': (
                self.processing_stats['files_processed'] / 
                max(1, self.processing_stats['files_processed'] + self.processing_stats['processing_errors'])
            ) * 100,
            'data_counts': {
                'temperature_measurements': len(numeric_data['temperature']),
                'salinity_measurements': len(numeric_data['salinity']),
                'pressure_measurements': len(numeric_data['pressure']),
                'coordinate_points': len(numeric_data['coordinates']),
                'timestamps': len(numeric_data['timestamps'])
            },
            'data_ranges': {},
            'processing_timestamp': datetime.now().isoformat()
        }
        
        # Calculate data ranges
        if numeric_data['temperature']:
            temp_array = np.array(numeric_data['temperature'])
            summary['data_ranges']['temperature'] = {
                'min': float(np.min(temp_array)),
                'max': float(np.max(temp_array)),
                'mean': float(np.mean(temp_array)),
                'std': float(np.std(temp_array))
            }
        
        if numeric_data['salinity']:
            sal_array = np.array(numeric_data['salinity'])
            summary['data_ranges']['salinity'] = {
                'min': float(np.min(sal_array)),
                'max': float(np.max(sal_array)),
                'mean': float(np.mean(sal_array)),
                'std': float(np.std(sal_array))
            }
        
        if numeric_data['pressure']:
            pres_array = np.array(numeric_data['pressure'])
            summary['data_ranges']['pressure'] = {
                'min': float(np.min(pres_array)),
                'max': float(np.max(pres_array)),
                'mean': float(np.mean(pres_array)),
                'std': float(np.std(pres_array))
            }
        
        # Calculate total measurements
        summary['total_measurements'] = (
            summary['data_counts']['temperature_measurements'] +
            summary['data_counts']['salinity_measurements'] +
            summary['data_counts']['pressure_measurements']
        )
        
        self.processing_stats['total_measurements'] = summary['total_measurements']
        
        return summary
    
    def _perform_regional_analysis(self, coordinates: List[List[float]]) -> Dict[str, Any]:
        """Perform regional analysis of measurement locations"""
        
        if not coordinates:
            return {'error': 'No coordinate data available for regional analysis'}
        
        regional_counts = {
            'Bay of Bengal': 0,
            'Arabian Sea': 0,
            'Southern Indian Ocean': 0,
            'Northern Indian Ocean': 0,
            'Unknown/Other': 0
        }
        
        regional_coords = {
            'Bay of Bengal': [],
            'Arabian Sea': [],
            'Southern Indian Ocean': [],
            'Northern Indian Ocean': [],
            'Unknown/Other': []
        }
        
        for lat, lon in coordinates:
            region = 'Unknown/Other'
            
            # Bay of Bengal
            if 5.0 <= lat <= 22.0 and 80.0 <= lon <= 100.0:
                region = 'Bay of Bengal'
            # Arabian Sea
            elif 8.0 <= lat <= 30.0 and 50.0 <= lon <= 80.0:
                region = 'Arabian Sea'
            # Southern Indian Ocean
            elif -10.0 <= lat <= 5.0 and 70.0 <= lon <= 90.0:
                region = 'Southern Indian Ocean'
            # Northern Indian Ocean (general)
            elif 0.0 <= lat <= 8.0 and 60.0 <= lon <= 100.0:
                region = 'Northern Indian Ocean'
            
            regional_counts[region] += 1
            regional_coords[region].append([lat, lon])
        
        # Calculate regional statistics
        regional_stats = {}
        for region, coords in regional_coords.items():
            if coords:
                lats = [c[0] for c in coords]
                lons = [c[1] for c in coords]
                
                regional_stats[region] = {
                    'count': len(coords),
                    'lat_range': [min(lats), max(lats)],
                    'lon_range': [min(lons), max(lons)],
                    'center': [sum(lats)/len(lats), sum(lons)/len(lons)]
                }
        
        return {
            'regional_distribution': regional_counts,
            'regional_statistics': regional_stats,
            'total_locations': len(coordinates)
        }
    
    def _perform_quality_control(self, numeric_data: Dict[str, List[float]]) -> Dict[str, Any]:
        """Perform quality control analysis on the data"""
        
        qc_results = {
            'data_quality_scores': {},
            'outlier_detection': {},
            'completeness_analysis': {},
            'overall_quality': 'unknown'
        }
        
        total_score = 0
        parameter_count = 0
        
        # Temperature QC
        if numeric_data['temperature']:
            temp_array = np.array(numeric_data['temperature'])
            
            # Outlier detection using IQR
            q75, q25 = np.percentile(temp_array, [75, 25])
            iqr = q75 - q25
            outliers = temp_array[(temp_array < q25 - 1.5 * iqr) | (temp_array > q75 + 1.5 * iqr)]
            
            temp_quality_score = min(100, max(0, 100 - (len(outliers) / len(temp_array)) * 100))
            
            qc_results['data_quality_scores']['temperature'] = temp_quality_score
            qc_results['outlier_detection']['temperature'] = {
                'outlier_count': len(outliers),
                'outlier_percentage': (len(outliers) / len(temp_array)) * 100,
                'outlier_values': outliers[:10].tolist()  # First 10 outliers
            }
            
            total_score += temp_quality_score
            parameter_count += 1
        
        # Salinity QC
        if numeric_data['salinity']:
            sal_array = np.array(numeric_data['salinity'])
            
            q75, q25 = np.percentile(sal_array, [75, 25])
            iqr = q75 - q25
            outliers = sal_array[(sal_array < q25 - 1.5 * iqr) | (sal_array > q75 + 1.5 * iqr)]
            
            sal_quality_score = min(100, max(0, 100 - (len(outliers) / len(sal_array)) * 100))
            
            qc_results['data_quality_scores']['salinity'] = sal_quality_score
            qc_results['outlier_detection']['salinity'] = {
                'outlier_count': len(outliers),
                'outlier_percentage': (len(outliers) / len(sal_array)) * 100,
                'outlier_values': outliers[:10].tolist()
            }
            
            total_score += sal_quality_score
            parameter_count += 1
        
        # Overall quality assessment
        if parameter_count > 0:
            overall_score = total_score / parameter_count
            
            if overall_score >= 90:
                qc_results['overall_quality'] = 'excellent'
            elif overall_score >= 75:
                qc_results['overall_quality'] = 'good'
            elif overall_score >= 60:
                qc_results['overall_quality'] = 'acceptable'
            else:
                qc_results['overall_quality'] = 'poor'
                
            qc_results['overall_quality_score'] = overall_score
        
        return qc_results
    
    def _save_processed_data(self, all_data: Dict[str, Any]):
        """Save processed data to JSON file"""
        
        output_file = Path("processed_oceanographic_data.json")
        
        try:
            with open(output_file, 'w') as f:
                json.dump(all_data, f, indent=2, default=str)
            
            print(f"DEBUG: Processed data saved to {output_file}")
            
        except Exception as e:
            print(f"DEBUG: Failed to save processed data: {e}")
    
    def _save_to_mongodb(self, all_data: Dict[str, Any]):
        """Save processed data to MongoDB"""
        
        if not self.mongodb_connected:
            print("DEBUG: MongoDB not connected - skipping save")
            return
        
        try:
            collection = self.mongo_db[self.config['mongodb_collection']]
            
            # Prepare document for MongoDB
            document = {
                'data_type': 'processed_oceanographic_data',
                'timestamp': datetime.now(),
                'processing_summary': all_data['processing_summary'],
                'regional_analysis': all_data['regional_analysis'],
                'quality_control': all_data['quality_control'],
                'numeric_data': all_data['numeric_data'],
                'file_count': len(all_data['file_metadata'])
            }
            
            # Replace existing document or insert new one
            result = collection.replace_one(
                {'data_type': 'processed_oceanographic_data'},
                document,
                upsert=True
            )
            
            print(f"DEBUG: Data saved to MongoDB - {'updated' if result.matched_count > 0 else 'inserted'}")
            
        except Exception as e:
            print(f"DEBUG: Failed to save to MongoDB: {e}")
    
    def _save_to_minio(self, all_data: Dict[str, Any]):
        """Save processed data to MinIO"""
        
        if not self.minio_connected:
            print("DEBUG: MinIO not connected - skipping save")
            return
        
        try:
            # Convert data to JSON string
            json_data = json.dumps(all_data, indent=2, default=str)
            json_bytes = json_data.encode('utf-8')
            
            # Generate object name with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            object_name = f"processed_data/oceanographic_data_{timestamp}.json"
            
            # Upload to MinIO
            from io import BytesIO
            data_stream = BytesIO(json_bytes)
            
            self.minio_client.put_object(
                bucket_name='floatchat-data',
                object_name=object_name,
                data=data_stream,
                length=len(json_bytes),
                content_type='application/json'
            )
            
            print(f"DEBUG: Data saved to MinIO as {object_name}")
            
        except Exception as e:
            print(f"DEBUG: Failed to save to MinIO: {e}")
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get current processing statistics"""
        return {
            **self.processing_stats,
            'mongodb_connected': self.mongodb_connected,
            'minio_connected': self.minio_connected,
            'timestamp': datetime.now().isoformat()
        }

def test_enhanced_data_processor():
    """Test the enhanced data processor with real NetCDF files"""
    print("DEBUG: Starting Enhanced Data Processor test...")
    
    processor = EnhancedDataProcessor()
    
    # Test connections
    print(f"DEBUG: MongoDB connected: {processor.mongodb_connected}")
    print(f"DEBUG: MinIO connected: {processor.minio_connected}")
    
    # Process all NetCDF files
    result = processor.process_all_netcdf_files()
    
    if 'error' not in result:
        print("DEBUG: ✓ NetCDF processing completed successfully")
        
        summary = result.get('processing_summary', {})
        print(f"DEBUG: Files processed: {summary.get('total_files_processed', 0)}")
        print(f"DEBUG: Total measurements: {summary.get('total_measurements', 0)}")
        
        data_counts = summary.get('data_counts', {})
        for param, count in data_counts.items():
            print(f"DEBUG: {param}: {count}")
        
        # Show data ranges
        data_ranges = summary.get('data_ranges', {})
        for param, ranges in data_ranges.items():
            print(f"DEBUG: {param} range: {ranges.get('min', 0):.2f} to {ranges.get('max', 0):.2f}, mean: {ranges.get('mean', 0):.2f}")
        
        # Show regional analysis
        regional = result.get('regional_analysis', {})
        if 'regional_distribution' in regional:
            print("DEBUG: Regional distribution:")
            for region, count in regional['regional_distribution'].items():
                if count > 0:
                    print(f"DEBUG: {region}: {count} locations")
        
        # Show quality control
        qc = result.get('quality_control', {})
        if 'overall_quality' in qc:
            print(f"DEBUG: Data quality: {qc['overall_quality']} ({qc.get('overall_quality_score', 0):.1f}%)")
    
    else:
        print(f"DEBUG: ✗ Processing failed: {result['error']}")
    
    # Show final statistics
    stats = processor.get_processing_statistics()
    print("DEBUG: Final processing statistics:")
    for key, value in stats.items():
        print(f"DEBUG: {key}: {value}")
    
    print("DEBUG: Enhanced Data Processor test completed!")
    return result

if __name__ == "__main__":
    test_enhanced_data_processor()
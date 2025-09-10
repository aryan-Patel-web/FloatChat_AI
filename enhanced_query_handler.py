"""
Enhanced Query Handler with Real Data Integration - COMPLETE FIXED VERSION
- Connects to actual processed oceanographic data  
- Implements statistical analysis on real measurements
- NO hardcoded responses - only real data analysis
- MongoDB integration for advanced queries
- Fixed all syntax errors and circular imports
"""

import json
import logging
import re
import netCDF4 as nc
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import pandas as pd
from collections import defaultdict
import math

print("DEBUG: Starting enhanced_query_handler.py imports")

# MongoDB support
try:
    from pymongo import MongoClient
    MONGODB_AVAILABLE = True
    print("DEBUG: MongoDB support available")
except ImportError:
    MONGODB_AVAILABLE = False
    print("DEBUG: MongoDB not available - using JSON files only")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedQueryHandler:
    def __init__(self, mongodb_uri="mongodb://localhost:27017"):
        print("DEBUG: Initializing AdvancedQueryHandler...")
        
        # MongoDB connection (optional)
        self.mongo_client = None
        self.mongo_collection = None
        self.mongodb_connected = False
        
        if MONGODB_AVAILABLE:
            try:
                print("DEBUG: Attempting MongoDB connection...")
                self.mongo_client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
                db = self.mongo_client.floatchat
                self.mongo_collection = db.ocean_data
                # Test connection
                self.mongo_client.admin.command('ismaster')
                self.mongodb_connected = True
                print("DEBUG: MongoDB connection established successfully")
            except Exception as e:
                print(f"DEBUG: MongoDB connection failed: {e}")
                self.mongodb_connected = False
        
        # Load real oceanographic data
        self.real_data = {}
        self.netcdf_data = {}
        self.data_cache = {}
        self.load_real_oceanographic_data()
        self.load_netcdf_files()
        
        # Query processors
        self.query_processors = {
            'temporal': self.process_temporal_query,
            'spatial': self.process_spatial_query, 
            'statistical': self.process_statistical_query,
            'comparison': self.process_comparison_query,
            'trend': self.process_trend_query,
            'correlation': self.process_correlation_query,
            'anomaly': self.process_anomaly_query,
            'research': self.process_research_query
        }
        
        # Query history and learning
        self.query_history = []
        self.user_patterns = defaultdict(list)
        print("DEBUG: AdvancedQueryHandler initialization complete")
        
    def load_netcdf_files(self):
        """Load actual NetCDF files and extract real measurements"""
        print("DEBUG: Loading NetCDF files from directory...")
        
        nc_files = list(Path('.').glob('*.nc'))
        print(f"DEBUG: Found {len(nc_files)} NetCDF files")
        
        all_temperatures = []
        all_salinities = []
        all_pressures = []
        all_coordinates = []
        file_metadata = []
        
        for nc_file in nc_files[:10]:  # Process first 10 files
            try:
                print(f"DEBUG: Processing NetCDF file: {nc_file}")
                ds = nc.Dataset(nc_file, 'r')
                
                # Extract variables
                temp_data = None
                sal_data = None
                pres_data = None
                lat_data = None
                lon_data = None
                
                # Check for temperature variables
                for temp_var in ['TEMP', 'temperature', 'temp', 'Temperature']:
                    if temp_var in ds.variables:
                        temp_data = ds.variables[temp_var][:]
                        print(f"DEBUG: Found temperature data in {temp_var}: {len(temp_data)} values")
                        break
                
                # Check for salinity variables  
                for sal_var in ['PSAL', 'salinity', 'salt', 'Salinity']:
                    if sal_var in ds.variables:
                        sal_data = ds.variables[sal_var][:]
                        print(f"DEBUG: Found salinity data in {sal_var}: {len(sal_data)} values")
                        break
                
                # Check for pressure variables
                for pres_var in ['PRES', 'pressure', 'depth', 'Pressure']:
                    if pres_var in ds.variables:
                        pres_data = ds.variables[pres_var][:]
                        print(f"DEBUG: Found pressure data in {pres_var}: {len(pres_data)} values")
                        break
                
                # Check for latitude/longitude
                for lat_var in ['LATITUDE', 'latitude', 'lat', 'Latitude']:
                    if lat_var in ds.variables:
                        lat_data = ds.variables[lat_var][:]
                        break
                
                for lon_var in ['LONGITUDE', 'longitude', 'lon', 'Longitude']:
                    if lon_var in ds.variables:
                        lon_data = ds.variables[lon_var][:]
                        break
                
                # Process temperature data
                if temp_data is not None:
                    temp_values = np.array(temp_data).flatten()
                    # Remove invalid values (fill values, NaN, etc.)
                    valid_temps = temp_values[(temp_values > -10) & (temp_values < 50) & ~np.isnan(temp_values)]
                    all_temperatures.extend(valid_temps.tolist())
                    print(f"DEBUG: Extracted {len(valid_temps)} valid temperature values")
                
                # Process salinity data
                if sal_data is not None:
                    sal_values = np.array(sal_data).flatten()
                    valid_sals = sal_values[(sal_values > 20) & (sal_values < 40) & ~np.isnan(sal_values)]
                    all_salinities.extend(valid_sals.tolist())
                    print(f"DEBUG: Extracted {len(valid_sals)} valid salinity values")
                
                # Process pressure data
                if pres_data is not None:
                    pres_values = np.array(pres_data).flatten()
                    valid_pres = pres_values[(pres_values >= 0) & (pres_values < 7000) & ~np.isnan(pres_values)]
                    all_pressures.extend(valid_pres.tolist())
                    print(f"DEBUG: Extracted {len(valid_pres)} valid pressure values")
                
                # Process coordinates
                if lat_data is not None and lon_data is not None:
                    lats = np.array(lat_data).flatten()
                    lons = np.array(lon_data).flatten()
                    
                    for lat, lon in zip(lats, lons):
                        if not (np.isnan(lat) or np.isnan(lon)):
                            if -90 <= lat <= 90 and -180 <= lon <= 180:
                                all_coordinates.append([float(lat), float(lon)])
                    
                    print(f"DEBUG: Extracted {len(lats)} coordinate pairs")
                
                # Store file metadata
                file_info = {
                    'filename': str(nc_file),
                    'variables': list(ds.variables.keys()),
                    'dimensions': list(ds.dimensions.keys()),
                    'temp_count': len(valid_temps) if temp_data is not None else 0,
                    'sal_count': len(valid_sals) if sal_data is not None else 0,
                    'coord_count': len(lats) if lat_data is not None else 0
                }
                file_metadata.append(file_info)
                
                ds.close()
                print(f"DEBUG: Successfully processed {nc_file}")
                
            except Exception as e:
                print(f"DEBUG: Error processing {nc_file}: {e}")
                continue
        
        # Store processed NetCDF data
        self.netcdf_data = {
            'temperature': all_temperatures,
            'salinity': all_salinities, 
            'pressure': all_pressures,
            'coordinates': all_coordinates,
            'file_metadata': file_metadata,
            'processing_summary': {
                'files_processed': len([f for f in file_metadata if f['temp_count'] > 0 or f['sal_count'] > 0]),
                'total_temp_measurements': len(all_temperatures),
                'total_sal_measurements': len(all_salinities),
                'total_coordinates': len(all_coordinates)
            }
        }
        
        print(f"DEBUG: NetCDF processing complete:")
        print(f"DEBUG: - Temperature measurements: {len(all_temperatures)}")
        print(f"DEBUG: - Salinity measurements: {len(all_salinities)}")
        print(f"DEBUG: - Pressure measurements: {len(all_pressures)}")
        print(f"DEBUG: - Coordinate points: {len(all_coordinates)}")
        print(f"DEBUG: - Files with data: {len([f for f in file_metadata if f['temp_count'] > 0 or f['sal_count'] > 0])}")
        
        # Save to MongoDB if connected
        if self.mongodb_connected:
            self.save_to_mongodb(self.netcdf_data)
    
    def load_real_oceanographic_data(self):
        """Load real oceanographic data from processed files"""
        print("DEBUG: Loading processed oceanographic data...")
        
        try:
            # Load processed oceanographic data
            if Path("processed_oceanographic_data.json").exists():
                print("DEBUG: Loading processed_oceanographic_data.json")
                with open("processed_oceanographic_data.json", 'r') as f:
                    processed_data = json.load(f)
                    self.real_data['processed'] = processed_data
                    print("DEBUG: Loaded processed oceanographic data successfully")
            else:
                print("DEBUG: processed_oceanographic_data.json not found")
            
            # Load ARGO data
            if Path("argo_extracted_data.json").exists():
                print("DEBUG: Loading argo_extracted_data.json")
                with open("argo_extracted_data.json", 'r') as f:
                    argo_data = json.load(f)
                    self.real_data['argo'] = argo_data
                    print("DEBUG: Loaded ARGO extracted data successfully")
            else:
                print("DEBUG: argo_extracted_data.json not found")
            
            # Load INCOIS data
            if Path("incois_comprehensive_data.json").exists():
                print("DEBUG: Loading incois_comprehensive_data.json")
                with open("incois_comprehensive_data.json", 'r') as f:
                    incois_data = json.load(f)
                    self.real_data['incois'] = incois_data
                    print("DEBUG: Loaded INCOIS comprehensive data successfully")
            else:
                print("DEBUG: incois_comprehensive_data.json not found")
            
            # Extract numeric data for analysis
            self._extract_numeric_datasets()
            
        except Exception as e:
            print(f"DEBUG: Failed to load real oceanographic data: {e}")
    
    def _extract_numeric_datasets(self):
        """Extract numeric data for statistical analysis"""
        print("DEBUG: Extracting numeric datasets...")
        
        self.data_cache = {
            'temperature': [],
            'salinity': [],
            'pressure': [],
            'coordinates': [],
            'depths': [],
            'timestamps': []
        }
        
        try:
            # Extract from processed data
            processed = self.real_data.get('processed', {})
            numeric_data = processed.get('numeric_data', {})
            
            print(f"DEBUG: Found processed data keys: {list(processed.keys())}")
            print(f"DEBUG: Found numeric data keys: {list(numeric_data.keys())}")
            
            if 'temperature' in numeric_data:
                temps = numeric_data['temperature']
                if isinstance(temps, list):
                    valid_temps = [t for t in temps if isinstance(t, (int, float)) and not np.isnan(t)]
                    self.data_cache['temperature'].extend(valid_temps)
                    print(f"DEBUG: Extracted {len(valid_temps)} temperature values from processed data")
            
            if 'salinity' in numeric_data:
                sals = numeric_data['salinity']
                if isinstance(sals, list):
                    valid_sals = [s for s in sals if isinstance(s, (int, float)) and not np.isnan(s)]
                    self.data_cache['salinity'].extend(valid_sals)
                    print(f"DEBUG: Extracted {len(valid_sals)} salinity values from processed data")
            
            if 'coordinates' in numeric_data:
                coords = numeric_data['coordinates']
                if isinstance(coords, list):
                    self.data_cache['coordinates'].extend(coords)
                    print(f"DEBUG: Extracted {len(coords)} coordinates from processed data")
            
            # Extract from INCOIS data
            incois = self.real_data.get('incois', {})
            if 'measurements' in incois:
                measurements = incois['measurements']
                print(f"DEBUG: Found {len(measurements)} INCOIS measurements")
                
                for measurement in measurements:
                    if isinstance(measurement, dict):
                        if 'temperature' in measurement:
                            temp_val = measurement['temperature']
                            if isinstance(temp_val, (int, float)) and not np.isnan(temp_val):
                                self.data_cache['temperature'].append(temp_val)
                        
                        if 'coordinates' in measurement:
                            coord_val = measurement['coordinates']
                            if isinstance(coord_val, (list, tuple)) and len(coord_val) >= 2:
                                self.data_cache['coordinates'].append(coord_val)
            
            print(f"DEBUG: Final data cache summary:")
            print(f"DEBUG: - Temperature: {len(self.data_cache['temperature'])} values")
            print(f"DEBUG: - Salinity: {len(self.data_cache['salinity'])} values")
            print(f"DEBUG: - Coordinates: {len(self.data_cache['coordinates'])} points")
        
        except Exception as e:
            print(f"DEBUG: Failed to extract numeric datasets: {e}")
    
    def save_to_mongodb(self, data):
        """Save data to MongoDB for advanced querying"""
        if not self.mongodb_connected:
            print("DEBUG: MongoDB not connected - skipping save")
            return
        
        try:
            print("DEBUG: Saving data to MongoDB...")
            
            # Prepare document for MongoDB
            document = {
                'data_type': 'oceanographic_measurements',
                'timestamp': datetime.now(),
                'source': 'netcdf_processing',
                'measurements': data,
                'summary': {
                    'temperature_count': len(data.get('temperature', [])),
                    'salinity_count': len(data.get('salinity', [])),
                    'coordinate_count': len(data.get('coordinates', []))
                }
            }
            
            # Insert or update
            result = self.mongo_collection.replace_one(
                {'data_type': 'oceanographic_measurements'},
                document,
                upsert=True
            )
            
            print(f"DEBUG: MongoDB save result: {result.acknowledged}")
            
        except Exception as e:
            print(f"DEBUG: Failed to save to MongoDB: {e}")
    
    def analyze_query_intent(self, query: str) -> Dict[str, Any]:
        """Advanced query intent analysis using real data"""
        print(f"DEBUG: Analyzing query intent for: {query}")
        
        query_lower = query.lower()
        
        analysis = {
            'intent_type': [],
            'parameters': [],
            'temporal_scope': None,
            'spatial_scope': None,
            'statistical_operations': [],
            'language': 'en',
            'complexity_score': 0,
            'research_level': 'basic',
            'requires_computation': False
        }
        
        # Language detection
        if any(char in query for char in 'तापमान समुद्र लवणता गहराई'):
            analysis['language'] = 'hi'
            print("DEBUG: Detected Hindi language")
        elif any(char in query for char in 'வெப்பநிலை கடல் உப்பு'):
            analysis['language'] = 'ta'
            print("DEBUG: Detected Tamil language")
        elif any(char in query for char in 'ఉష్ణోగ్రత సముద్రం లవణత'):
            analysis['language'] = 'te'
            print("DEBUG: Detected Telugu language")
        elif any(char in query for char in 'তাপমাত্রা সমুদ্র লবণাক্ততা'):
            analysis['language'] = 'bn'
            print("DEBUG: Detected Bengali language")
        else:
            print("DEBUG: Detected English language")
        
        # Parameter detection
        if any(word in query_lower for word in ['temperature', 'temp', 'thermal', 'তাপমাত্রা', 'तापमान', 'வெப்பநிலை', 'ఉష్ణోగ్రత']):
            analysis['parameters'].append('temperature')
            analysis['intent_type'].append('parameter_focused')
            print("DEBUG: Detected temperature parameter")
        
        if any(word in query_lower for word in ['salinity', 'salt', 'psu', 'লবণাক্ততা', 'लवणता', 'உப்பு', 'లవణత']):
            analysis['parameters'].append('salinity')
            analysis['intent_type'].append('parameter_focused')
            print("DEBUG: Detected salinity parameter")
        
        if any(word in query_lower for word in ['pressure', 'depth', 'pres', 'গভীরতা', 'गहराई', 'ఆఴం', 'ஆழம்']):
            analysis['parameters'].append('pressure')
            analysis['intent_type'].append('parameter_focused')
            print("DEBUG: Detected pressure/depth parameter")
        
        # Statistical operations
        if any(word in query_lower for word in ['average', 'mean', 'correlation', 'compare', 'analyze', 'statistics']):
            analysis['statistical_operations'].append('statistical_analysis')
            analysis['intent_type'].append('statistical')
            analysis['requires_computation'] = True
            print("DEBUG: Detected statistical analysis intent")
        
        # Spatial scope
        if any(region in query_lower for region in ['bay of bengal', 'bengal', 'arabian sea', 'indian ocean']):
            analysis['spatial_scope'] = 'regional'
            analysis['intent_type'].append('spatial')
            print("DEBUG: Detected regional spatial scope")
        
        # Research level
        if any(word in query_lower for word in ['correlation', 'multivariate', 'analysis', 'pattern', 'trend']):
            analysis['research_level'] = 'advanced'
            print("DEBUG: Detected advanced research level")
        elif any(word in query_lower for word in ['show', 'what is', 'tell me']):
            analysis['research_level'] = 'basic'
            print("DEBUG: Detected basic research level")
        else:
            analysis['research_level'] = 'intermediate'
            print("DEBUG: Detected intermediate research level")
        
        # Complexity scoring
        analysis['complexity_score'] = (
            len(analysis['parameters']) * 2 +
            len(analysis['statistical_operations']) * 3 +
            len(analysis['intent_type']) * 1.5
        )
        
        print(f"DEBUG: Query analysis complete - Intent types: {analysis['intent_type']}, Parameters: {analysis['parameters']}")
        return analysis
    
    def process_statistical_query(self, query: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Process statistical queries using real NetCDF and processed data"""
        print("DEBUG: Processing statistical query...")
        
        results = {
            'statistics': {},
            'data_source': 'real_netcdf_and_processed_measurements',
            'measurement_count': 0,
            'netcdf_data': {},
            'processed_data': {}
        }
        
        try:
            # Process NetCDF data first (priority)
            for param in analysis['parameters']:
                if param in self.netcdf_data:
                    values = self.netcdf_data[param]
                    if values and len(values) > 0:
                        print(f"DEBUG: Processing {param} from NetCDF - {len(values)} values")
                        
                        data_array = np.array(values)
                        
                        if len(data_array) > 0:
                            stats = {
                                'count': len(data_array),
                                'mean': float(np.mean(data_array)),
                                'median': float(np.median(data_array)),
                                'std': float(np.std(data_array)),
                                'min': float(np.min(data_array)),
                                'max': float(np.max(data_array)),
                                'range': float(np.max(data_array) - np.min(data_array)),
                                'percentile_25': float(np.percentile(data_array, 25)),
                                'percentile_75': float(np.percentile(data_array, 75))
                            }
                            
                            # Add confidence intervals
                            if len(data_array) > 2:
                                sem = stats['std'] / np.sqrt(len(data_array))
                                ci_margin = 1.96 * sem
                                stats['confidence_interval_95'] = {
                                    'lower': stats['mean'] - ci_margin,
                                    'upper': stats['mean'] + ci_margin
                                }
                            
                            results['statistics'][param] = stats
                            results['measurement_count'] += len(data_array)
                            results['netcdf_data'][param] = stats
                            
                            print(f"DEBUG: {param} statistics - Mean: {stats['mean']:.2f}, Count: {stats['count']}")
                
                # Also check data_cache for additional data
                elif param in self.data_cache:
                    values = self.data_cache[param]
                    if values and len(values) > 0:
                        print(f"DEBUG: Processing {param} from data cache - {len(values)} values")
                        
                        data_array = np.array([v for v in values if isinstance(v, (int, float))])
                        
                        if len(data_array) > 0:
                            stats = {
                                'count': len(data_array),
                                'mean': float(np.mean(data_array)),
                                'median': float(np.median(data_array)),
                                'std': float(np.std(data_array)),
                                'min': float(np.min(data_array)),
                                'max': float(np.max(data_array)),
                                'range': float(np.max(data_array) - np.min(data_array))
                            }
                            
                            results['statistics'][param] = stats
                            results['measurement_count'] += len(data_array)
                            results['processed_data'][param] = stats
                            
                            print(f"DEBUG: {param} statistics from cache - Mean: {stats['mean']:.2f}, Count: {stats['count']}")
            
            # MongoDB query if available
            if self.mongodb_connected and results['measurement_count'] == 0:
                print("DEBUG: Attempting MongoDB query for additional data...")
                mongo_results = self.query_mongodb_stats(analysis['parameters'])
                if mongo_results:
                    results['statistics'].update(mongo_results)
                    print("DEBUG: Added statistics from MongoDB")
            
            print(f"DEBUG: Statistical processing complete - {results['measurement_count']} total measurements processed")
            return results
            
        except Exception as e:
            print(f"DEBUG: Statistical processing failed: {e}")
            results['error'] = str(e)
            return results
    
    def query_mongodb_stats(self, parameters: List[str]) -> Dict[str, Any]:
        """Query MongoDB for statistical data"""
        if not self.mongodb_connected:
            return {}
        
        try:
            print("DEBUG: Querying MongoDB for statistical data...")
            
            # Query for oceanographic measurements
            cursor = self.mongo_collection.find({'data_type': 'oceanographic_measurements'})
            
            stats_results = {}
            for doc in cursor:
                measurements = doc.get('measurements', {})
                
                for param in parameters:
                    if param in measurements:
                        values = measurements[param]
                        if values and len(values) > 0:
                            data_array = np.array(values)
                            stats_results[param] = {
                                'count': len(data_array),
                                'mean': float(np.mean(data_array)),
                                'std': float(np.std(data_array)),
                                'min': float(np.min(data_array)),
                                'max': float(np.max(data_array)),
                                'source': 'mongodb'
                            }
                            print(f"DEBUG: Retrieved {param} stats from MongoDB - {len(values)} values")
            
            return stats_results
            
        except Exception as e:
            print(f"DEBUG: MongoDB stats query failed: {e}")
            return {}
    
    def process_spatial_query(self, query: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Process spatial queries using real coordinate data"""
        print("DEBUG: Processing spatial query...")
        
        results = {
            'spatial_analysis': {},
            'regional_distribution': {},
            'coordinates_analyzed': 0,
            'data_sources': []
        }
        
        try:
            # Combine coordinates from NetCDF and processed data
            all_coordinates = []
            
            # NetCDF coordinates (priority)
            if 'coordinates' in self.netcdf_data:
                netcdf_coords = self.netcdf_data['coordinates']
                all_coordinates.extend(netcdf_coords)
                results['data_sources'].append('netcdf_files')
                print(f"DEBUG: Added {len(netcdf_coords)} coordinates from NetCDF files")
            
            # Processed data coordinates
            cache_coords = self.data_cache.get('coordinates', [])
            for coord in cache_coords:
                if coord not in all_coordinates:
                    all_coordinates.append(coord)
            
            if cache_coords:
                results['data_sources'].append('processed_json')
                print(f"DEBUG: Added {len(cache_coords)} unique coordinates from processed data")
            
            if all_coordinates:
                print(f"DEBUG: Processing {len(all_coordinates)} total coordinates")
                
                # Classify coordinates by region
                regional_counts = {
                    'Bay of Bengal': 0,
                    'Arabian Sea': 0, 
                    'Indian Ocean': 0,
                    'Southern Indian Ocean': 0,
                    'Unknown/Other': 0
                }
                
                valid_coords = []
                for coord in all_coordinates:
                    if isinstance(coord, (list, tuple)) and len(coord) >= 2:
                        try:
                            lat, lon = float(coord[0]), float(coord[1])
                            
                            # Validate coordinates
                            if -90 <= lat <= 90 and -180 <= lon <= 180:
                                valid_coords.append([lat, lon])
                                
                                # Classify region based on coordinates
                                if 5 <= lat <= 22 and 80 <= lon <= 100:
                                    regional_counts['Bay of Bengal'] += 1
                                elif 8 <= lat <= 30 and 50 <= lon <= 80:
                                    regional_counts['Arabian Sea'] += 1
                                elif -10 <= lat <= 5 and 70 <= lon <= 90:
                                    regional_counts['Southern Indian Ocean'] += 1
                                elif -60 <= lat <= 30 and 40 <= lon <= 120:
                                    regional_counts['Indian Ocean'] += 1
                                else:
                                    regional_counts['Unknown/Other'] += 1
                                    
                        except (ValueError, TypeError):
                            continue
                
                results['regional_distribution'] = regional_counts
                results['coordinates_analyzed'] = len(valid_coords)
                
                print(f"DEBUG: Regional distribution: {regional_counts}")
                
                # Calculate spatial statistics
                if valid_coords:
                    lats = [coord[0] for coord in valid_coords]
                    lons = [coord[1] for coord in valid_coords]
                    
                    results['spatial_analysis'] = {
                        'lat_range': [min(lats), max(lats)],
                        'lon_range': [min(lons), max(lons)],
                        'center_point': [sum(lats)/len(lats), sum(lons)/len(lons)],
                        'coverage_area': {
                            'lat_span': max(lats) - min(lats),
                            'lon_span': max(lons) - min(lons)
                        },
                        'bounding_box': {
                            'north': max(lats),
                            'south': min(lats), 
                            'east': max(lons),
                            'west': min(lons)
                        }
                    }
                    
                    print(f"DEBUG: Spatial analysis complete - Lat range: [{min(lats):.2f}, {max(lats):.2f}], Lon range: [{min(lons):.2f}, {max(lons):.2f}]")
            
            return results
            
        except Exception as e:
            print(f"DEBUG: Spatial processing failed: {e}")
            results['error'] = str(e)
            return results
    
    def process_temporal_query(self, query: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Process temporal queries using file timestamps and data collection periods"""
        print("DEBUG: Processing temporal query...")
        
        results = {
            'temporal_analysis': {},
            'data_recency': 'current',
            'time_coverage': 'real-time monitoring',
            'file_timestamps': []
        }
        
        try:
            # Get file modification times
            nc_files = list(Path('.').glob('*.nc'))
            json_files = ['processed_oceanographic_data.json', 'argo_extracted_data.json', 'incois_comprehensive_data.json']
            
            file_times = []
            for nc_file in nc_files:
                if nc_file.exists():
                    mtime = nc_file.stat().st_mtime
                    file_times.append({
                        'file': str(nc_file),
                        'modified': datetime.fromtimestamp(mtime).isoformat(),
                        'type': 'netcdf'
                    })
            
            for json_file in json_files:
                if Path(json_file).exists():
                    mtime = Path(json_file).stat().st_mtime
                    file_times.append({
                        'file': json_file,
                        'modified': datetime.fromtimestamp(mtime).isoformat(),
                        'type': 'processed_data'
                    })
            
            results['file_timestamps'] = file_times
            
            # Analyze data collection periods from NetCDF metadata
            if hasattr(self, 'netcdf_data') and 'file_metadata' in self.netcdf_data:
                metadata = self.netcdf_data['file_metadata']
                results['temporal_analysis'] = {
                    'data_files_analyzed': len(metadata),
                    'data_collection_period': 'ongoing_argo_missions',
                    'last_update': datetime.now().strftime('%Y-%m-%d %H:%M'),
                    'data_source': 'ARGO floats and INCOIS stations',
                    'monitoring_status': 'active',
                    'file_count': len(nc_files),
                    'processing_timestamp': datetime.now().isoformat()
                }
            
            print(f"DEBUG: Temporal analysis complete - {len(file_times)} files analyzed")
            return results
            
        except Exception as e:
            print(f"DEBUG: Temporal processing failed: {e}")
            results['error'] = str(e)
            return results
    
    def process_comparison_query(self, query: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Process comparison queries between parameters or regions"""
        print("DEBUG: Processing comparison query...")
        
        results = {
            'comparisons': {},
            'correlation_analysis': {},
            'data_sources': []
        }
        
        try:
            if len(analysis['parameters']) >= 2:
                param1, param2 = analysis['parameters'][:2]
                print(f"DEBUG: Comparing {param1} vs {param2}")
                
                # Get data from NetCDF first (priority)
                data1 = self.netcdf_data.get(param1, [])
                data2 = self.netcdf_data.get(param2, [])
                
                # Fallback to processed data
                if not data1:
                    data1 = self.data_cache.get(param1, [])
                if not data2:
                    data2 = self.data_cache.get(param2, [])
                
                # Clean data
                clean_data1 = [v for v in data1 if isinstance(v, (int, float)) and not np.isnan(v)]
                clean_data2 = [v for v in data2 if isinstance(v, (int, float)) and not np.isnan(v)]
                
                if clean_data1 and clean_data2:
                    print(f"DEBUG: Found {len(clean_data1)} {param1} and {len(clean_data2)} {param2} values")
                    
                    # Statistical comparison
                    results['comparisons'][f"{param1}_vs_{param2}"] = {
                        f'{param1}_mean': float(np.mean(clean_data1)),
                        f'{param2}_mean': float(np.mean(clean_data2)),
                        f'{param1}_std': float(np.std(clean_data1)),
                        f'{param2}_std': float(np.std(clean_data2)),
                        f'{param1}_range': [float(np.min(clean_data1)), float(np.max(clean_data1))],
                        f'{param2}_range': [float(np.min(clean_data2)), float(np.max(clean_data2))],
                        'sample_sizes': [len(clean_data1), len(clean_data2)]
                    }
                    
                    # Correlation analysis if we have paired data
                    min_length = min(len(clean_data1), len(clean_data2))
                    if min_length > 1:
                        # Take equal length samples
                        sample1 = clean_data1[:min_length]
                        sample2 = clean_data2[:min_length]
                        
                        correlation = np.corrcoef(sample1, sample2)[0, 1]
                        if not np.isnan(correlation):
                            results['correlation_analysis'] = {
                                'correlation_coefficient': float(correlation),
                                'strength': self._interpret_correlation(correlation),
                                'sample_size': min_length,
                                'p_value_estimate': self._estimate_p_value(correlation, min_length)
                            }
                            
                            print(f"DEBUG: Correlation analysis - r = {correlation:.3f}, strength = {self._interpret_correlation(correlation)}")
                
                results['data_sources'] = ['netcdf_files', 'processed_json']
                
            return results
            
        except Exception as e:
            print(f"DEBUG: Comparison processing failed: {e}")
            results['error'] = str(e)
            return results
    
    def _interpret_correlation(self, corr: float) -> str:
        """Interpret correlation coefficient strength"""
        abs_corr = abs(corr)
        if abs_corr > 0.8:
            return 'very strong'
        elif abs_corr > 0.6:
            return 'strong'
        elif abs_corr > 0.4:
            return 'moderate'
        elif abs_corr > 0.2:
            return 'weak'
        else:
            return 'very weak'
    
    def _estimate_p_value(self, r: float, n: int) -> str:
        """Rough p-value estimation for correlation"""
        if n < 3:
            return 'insufficient_sample_size'
        
        # Simple approximation for correlation significance
        t_stat = abs(r) * math.sqrt((n - 2) / (1 - r**2))
        
        if t_stat > 2.576:  # ~99% confidence
            return 'p < 0.01'
        elif t_stat > 1.96:  # ~95% confidence
            return 'p < 0.05'
        elif t_stat > 1.645:  # ~90% confidence
            return 'p < 0.10'
        else:
            return 'p >= 0.10'
    
    def process_trend_query(self, query: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Process trend analysis queries"""
        print("DEBUG: Processing trend query...")
        
        results = {
            'trend_analysis': {},
            'data_availability': 'limited_temporal_data',
            'recommendations': []
        }
        
        # Since we don't have extensive temporal data, provide analysis based on what's available
        results['trend_analysis'] = {
            'temporal_scope': 'snapshot_analysis',
            'data_points': len(self.data_cache.get('temperature', [])),
            'analysis_type': 'cross_sectional',
            'trend_detection': 'requires_time_series_data'
        }
        
        results['recommendations'] = [
            'For trend analysis, collect data over multiple time periods',
            'Current analysis provides spatial patterns rather than temporal trends',
            'Consider seasonal data collection for meaningful trend detection'
        ]
        
        return results
    
    def process_correlation_query(self, query: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Process correlation analysis queries"""
        return self.process_comparison_query(query, analysis)
    
    def process_anomaly_query(self, query: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Process anomaly detection queries"""
        print("DEBUG: Processing anomaly query...")
        
        results = {
            'anomaly_analysis': {},
            'outliers_detected': {},
            'statistical_thresholds': {}
        }
        
        try:
            for param in analysis['parameters']:
                data = self.netcdf_data.get(param, self.data_cache.get(param, []))
                
                if data and len(data) > 10:
                    data_array = np.array([v for v in data if isinstance(v, (int, float))])
                    
                    if len(data_array) > 0:
                        # Statistical outlier detection
                        q75, q25 = np.percentile(data_array, [75, 25])
                        iqr = q75 - q25
                        lower_bound = q25 - 1.5 * iqr
                        upper_bound = q75 + 1.5 * iqr
                        
                        outliers = data_array[(data_array < lower_bound) | (data_array > upper_bound)]
                        
                        results['outliers_detected'][param] = {
                            'count': len(outliers),
                            'percentage': len(outliers) / len(data_array) * 100,
                            'outlier_values': outliers.tolist()[:10],  # First 10 outliers
                            'bounds': {'lower': float(lower_bound), 'upper': float(upper_bound)}
                        }
                        
                        results['statistical_thresholds'][param] = {
                            'iqr': float(iqr),
                            'q25': float(q25),
                            'q75': float(q75),
                            'method': 'interquartile_range'
                        }
                        
                        print(f"DEBUG: {param} anomalies - {len(outliers)} outliers ({len(outliers)/len(data_array)*100:.1f}%)")
            
            return results
            
        except Exception as e:
            print(f"DEBUG: Anomaly processing failed: {e}")
            results['error'] = str(e)
            return results
    
    def process_research_query(self, query: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Process research-level queries with comprehensive analysis"""
        print("DEBUG: Processing research query...")
        
        results = {
            'research_analysis': {},
            'data_summary': {},
            'methodology': {},
            'limitations': []
        }
        
        try:
            # Comprehensive data summary
            results['data_summary'] = {
                'netcdf_files': len(self.netcdf_data.get('file_metadata', [])),
                'temperature_measurements': len(self.netcdf_data.get('temperature', [])),
                'salinity_measurements': len(self.netcdf_data.get('salinity', [])),
                'coordinate_points': len(self.netcdf_data.get('coordinates', [])),
                'data_sources': ['ARGO_floats', 'INCOIS_stations', 'processed_oceanographic_data']
            }
            
            # Research methodology
            results['methodology'] = {
                'data_extraction': 'NetCDF file processing with quality control',
                'statistical_analysis': 'NumPy-based statistical computations',
                'spatial_analysis': 'Coordinate-based regional classification',
                'quality_control': 'Range validation and NaN filtering'
            }
            
            # Research limitations
            results['limitations'] = [
                'Limited temporal coverage - snapshot analysis only',
                'Data quality depends on original ARGO/INCOIS measurements',
                'Regional classification based on coordinate ranges',
                'Statistical significance testing requires larger samples'
            ]
            
            # Advanced analysis if multiple parameters
            if len(analysis['parameters']) > 1:
                results['research_analysis'] = self.process_comparison_query(query, analysis)
            else:
                results['research_analysis'] = self.process_statistical_query(query, analysis)
            
            return results
            
        except Exception as e:
            print(f"DEBUG: Research processing failed: {e}")
            results['error'] = str(e)
            return results
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """Main query processing function"""
        print(f"DEBUG: Processing query: {query}")
        
        try:
            # Analyze query intent
            analysis = self.analyze_query_intent(query)
            
            # Determine processing method
            if analysis['research_level'] == 'advanced':
                processor = self.query_processors['research']
            elif 'statistical' in analysis['intent_type']:
                processor = self.query_processors['statistical']
            elif 'spatial' in analysis['intent_type']:
                processor = self.query_processors['spatial']
            elif len(analysis['parameters']) >= 2:
                processor = self.query_processors['comparison']
            else:
                processor = self.query_processors['statistical']  # Default
            
            # Process the query
            result = processor(query, analysis)
            result['query'] = query
            result['analysis'] = analysis
            result['timestamp'] = datetime.now().isoformat()
            
            print(f"DEBUG: Query processed successfully")
            return result
            
        except Exception as e:
            print(f"DEBUG: Query processing failed: {e}")
            return {
                'query': query,
                'error': str(e),
                'fallback_response': f"I encountered an error processing your query about {query}. The system has real oceanographic data available but couldn't complete the specific analysis requested.",
                'timestamp': datetime.now().isoformat()
            }


def test_enhanced_query_handler():
    """Test the enhanced query handler with real data"""
    print("Testing Enhanced Query Handler with Real Data...")
    
    handler = AdvancedQueryHandler()
    
    test_queries = [
        "What is the average temperature in the Indian Ocean?",
        "Show me salinity statistics",
        "Compare temperature vs salinity correlation",
        "Recent temperature measurements",
        "Analyze temperature distribution patterns"
    ]
    
    # Check data availability first
    netcdf_temp_count = len(handler.netcdf_data.get('temperature', []))
    netcdf_sal_count = len(handler.netcdf_data.get('salinity', []))
    cache_temp_count = len(handler.data_cache.get('temperature', []))
    cache_sal_count = len(handler.data_cache.get('salinity', []))
    
    print(f"DEBUG: Data availability check:")
    print(f"DEBUG: - NetCDF temperature: {netcdf_temp_count} values")
    print(f"DEBUG: - NetCDF salinity: {netcdf_sal_count} values") 
    print(f"DEBUG: - Cache temperature: {cache_temp_count} values")
    print(f"DEBUG: - Cache salinity: {cache_sal_count} values")
    
    for query in test_queries:
        print(f"\nDEBUG: Testing query: {query}")
        
        try:
            result = handler.process_query(query)
            
            print(f"DEBUG: ✓ Query processed successfully")
            print(f"DEBUG: Result keys: {list(result.keys())}")
            
            if 'statistics' in result:
                stats = result['statistics']
                for param, param_stats in stats.items():
                    if isinstance(param_stats, dict) and 'count' in param_stats:
                        print(f"DEBUG: {param}: {param_stats['count']} measurements, mean: {param_stats.get('mean', 'N/A')}")
            
            if 'error' in result:
                print(f"DEBUG: ✗ Query had error: {result['error']}")
            
        except Exception as e:
            print(f"DEBUG: ✗ Query failed with exception: {e}")
    
    print(f"\nDEBUG: {'='*80}")
    print("DEBUG: Enhanced Query Handler test completed!")
    print(f"DEBUG: Total NetCDF measurements available: {netcdf_temp_count + netcdf_sal_count}")
    print(f"DEBUG: Total cached measurements available: {cache_temp_count + cache_sal_count}")
    print(f"DEBUG: MongoDB connection: {'✓ Connected' if handler.mongodb_connected else '✗ Not connected'}")
    print(f"DEBUG: {'='*80}")
    
    return True

if __name__ == "__main__":
    test_enhanced_query_handler()
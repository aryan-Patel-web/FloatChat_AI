"""
Advanced LLM Handler for FloatChat - Production-Ready Chat Intelligence
- Multi-model LLM integration with fallbacks
- Real oceanographic data integration
- Advanced conversation management
- NO hardcoded responses - only real data analysis
"""

import json
import logging
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import numpy as np
import re
import hashlib
import time
from collections import deque, defaultdict

print("DEBUG: Starting advanced_llm_handler.py imports")

# Import system components
try:
    from mcp_integration import MCPContextManager
    print("DEBUG: MCP integration imported successfully")
except ImportError as e:
    print(f"DEBUG: MCP integration import failed: {e}")
    MCPContextManager = None

try:
    from enhanced_query_handler import AdvancedQueryHandler
    print("DEBUG: Enhanced query handler imported successfully")
except ImportError as e:
    print(f"DEBUG: Enhanced query handler import failed: {e}")
    AdvancedQueryHandler = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedLLMHandler:
    """Production-ready LLM handler with real data integration"""
    
    def __init__(self, config_path: Optional[str] = None):
        print("DEBUG: Initializing Advanced LLM Handler...")
        
        self.config = self._load_config(config_path)
        self.conversation_history = deque(maxlen=50)
        self.user_sessions = defaultdict(dict)
        self.response_cache = {}
        self.performance_metrics = {
            'total_queries': 0,
            'successful_responses': 0,
            'average_response_time': 0.0,
            'model_usage': defaultdict(int)
        }
        
        # Initialize components
        self.mcp_manager = None
        self.query_handler = None
        
        try:
            if MCPContextManager:
                self.mcp_manager = MCPContextManager()
                print("DEBUG: MCP manager initialized")
        except Exception as e:
            print(f"DEBUG: MCP manager initialization failed: {e}")
        
        try:
            if AdvancedQueryHandler:
                self.query_handler = AdvancedQueryHandler()
                print("DEBUG: Query handler initialized")
        except Exception as e:
            print(f"DEBUG: Query handler initialization failed: {e}")
        
        # Load real oceanographic data
        self.oceanographic_data = {}
        self.load_real_oceanographic_data()
        
        # Conversation context management
        self.context_window_size = 10
        self.max_context_tokens = 8000
        
        print("DEBUG: Advanced LLM Handler initialization complete")
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load LLM handler configuration"""
        print("DEBUG: Loading LLM handler configuration...")
        
        default_config = {
            'response_timeout': 30,
            'max_retries': 3,
            'cache_responses': True,
            'enable_conversation_context': True,
            'fallback_to_data_analysis': True,
            'supported_languages': ['en', 'hi', 'ta', 'te', 'bn', 'ml'],
            'response_quality_threshold': 0.7,
            'max_response_length': 2000
        }
        
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
                    print("DEBUG: Configuration loaded from file")
            except Exception as e:
                print(f"DEBUG: Failed to load config: {e}")
        
        return default_config
    
    def load_real_oceanographic_data(self):
        """Load real oceanographic data for intelligent responses"""
        print("DEBUG: Loading real oceanographic data...")
        
        try:
            # Load NetCDF data summary
            import netCDF4 as nc
            
            nc_files = list(Path('.').glob('*.nc'))
            print(f"DEBUG: Found {len(nc_files)} NetCDF files")
            
            netcdf_summary = {
                'file_count': len(nc_files),
                'temperature_measurements': [],
                'salinity_measurements': [],
                'pressure_measurements': [],
                'coordinates': [],
                'variables_available': set()
            }
            
            # Process NetCDF files for real data
            for nc_file in nc_files[:10]:  # Process first 10 files
                try:
                    ds = nc.Dataset(nc_file, 'r')
                    
                    # Track available variables
                    netcdf_summary['variables_available'].update(ds.variables.keys())
                    
                    # Extract temperature data
                    for temp_var in ['TEMP', 'temperature', 'temp']:
                        if temp_var in ds.variables:
                            temp_data = ds.variables[temp_var][:]
                            valid_temps = [float(t) for t in np.array(temp_data).flatten() 
                                         if isinstance(t, (int, float)) and not np.isnan(t) and -5 <= t <= 40]
                            netcdf_summary['temperature_measurements'].extend(valid_temps)
                            break
                    
                    # Extract salinity data
                    for sal_var in ['PSAL', 'salinity', 'salt']:
                        if sal_var in ds.variables:
                            sal_data = ds.variables[sal_var][:]
                            valid_sals = [float(s) for s in np.array(sal_data).flatten()
                                        if isinstance(s, (int, float)) and not np.isnan(s) and 25 <= s <= 40]
                            netcdf_summary['salinity_measurements'].extend(valid_sals)
                            break
                    
                    # Extract coordinates
                    lat_data = None
                    lon_data = None
                    
                    for lat_var in ['LATITUDE', 'latitude', 'lat']:
                        if lat_var in ds.variables:
                            lat_data = ds.variables[lat_var][:]
                            break
                    
                    for lon_var in ['LONGITUDE', 'longitude', 'lon']:
                        if lon_var in ds.variables:
                            lon_data = ds.variables[lon_var][:]
                            break
                    
                    if lat_data is not None and lon_data is not None:
                        lats = np.array(lat_data).flatten()
                        lons = np.array(lon_data).flatten()
                        
                        for lat, lon in zip(lats, lons):
                            if not (np.isnan(lat) or np.isnan(lon)) and -90 <= lat <= 90 and -180 <= lon <= 180:
                                netcdf_summary['coordinates'].append([float(lat), float(lon)])
                    
                    ds.close()
                    print(f"DEBUG: Processed NetCDF file: {nc_file}")
                    
                except Exception as e:
                    print(f"DEBUG: Failed to process {nc_file}: {e}")
                    continue
            
            netcdf_summary['variables_available'] = list(netcdf_summary['variables_available'])
            self.oceanographic_data['netcdf'] = netcdf_summary
            
            print(f"DEBUG: NetCDF data loaded - {len(netcdf_summary['temperature_measurements'])} temp, "
                  f"{len(netcdf_summary['salinity_measurements'])} sal, {len(netcdf_summary['coordinates'])} coords")
            
            # Load processed JSON data
            json_files = [
                'processed_oceanographic_data.json',
                'argo_extracted_data.json', 
                'incois_comprehensive_data.json'
            ]
            
            for json_file in json_files:
                if Path(json_file).exists():
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                        
                    file_key = json_file.replace('.json', '').replace('_', '')
                    self.oceanographic_data[file_key] = data
                    print(f"DEBUG: Loaded {json_file}")
            
            print("DEBUG: Real oceanographic data loading complete")
            
        except Exception as e:
            print(f"DEBUG: Failed to load oceanographic data: {e}")
    
    async def process_intelligent_query(self, query: str, user_id: str = "default", 
                                      conversation_context: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Process query with intelligent LLM response using real data"""
        print(f"DEBUG: Processing intelligent query: '{query[:50]}...' for user: {user_id}")
        
        start_time = time.time()
        self.performance_metrics['total_queries'] += 1
        
        try:
            # Analyze query and extract real data context
            analysis_result = await self._analyze_query_with_real_data(query, user_id)
            
            # Generate intelligent response
            if self.mcp_manager:
                print("DEBUG: Using MCP manager for response generation")
                
                # Optimize context with real data
                optimized_context = self.mcp_manager.optimize_context_for_query(
                    query, analysis_result.get('real_data', {})
                )
                
                # Generate MCP response
                mcp_response = await self.mcp_manager.generate_mcp_response(
                    query, optimized_context
                )
                
                intelligent_response = mcp_response.get('response', '')
                model_used = mcp_response.get('model_used', 'unknown')
                
            else:
                print("DEBUG: Using fallback intelligent response generation")
                intelligent_response = await self._generate_fallback_intelligent_response(
                    query, analysis_result
                )
                model_used = 'fallback_intelligent'
            
            # Enhance response with real data insights
            enhanced_response = await self._enhance_response_with_real_data(
                intelligent_response, analysis_result, query
            )
            
            processing_time = time.time() - start_time
            
            # Build comprehensive result
            result = {
                'original_query': query,
                'intelligent_response': enhanced_response,
                'model_used': model_used,
                'processing_time': processing_time,
                'data_analysis': analysis_result,
                'conversation_context_used': len(conversation_context) if conversation_context else 0,
                'timestamp': datetime.now().isoformat(),
                'user_id': user_id,
                'quality_score': self._calculate_response_quality(enhanced_response, analysis_result),
                'real_data_integrated': True
            }
            
            # Update conversation history
            self.conversation_history.append({
                'query': query,
                'response': enhanced_response,
                'timestamp': datetime.now().isoformat(),
                'user_id': user_id,
                'processing_time': processing_time
            })
            
            # Update performance metrics
            self.performance_metrics['successful_responses'] += 1
            self.performance_metrics['model_usage'][model_used] += 1
            self._update_average_response_time(processing_time)
            
            print(f"DEBUG: Intelligent query processing complete in {processing_time:.2f}s, quality: {result['quality_score']:.2f}")
            
            return result
            
        except Exception as e:
            print(f"DEBUG: Intelligent query processing failed: {e}")
            
            # Fallback to data-only analysis
            fallback_result = await self._generate_data_only_response(query, user_id)
            
            processing_time = time.time() - start_time
            
            return {
                'original_query': query,
                'intelligent_response': fallback_result,
                'model_used': 'data_analysis_fallback',
                'processing_time': processing_time,
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'user_id': user_id,
                'real_data_integrated': True
            }
    
    async def _analyze_query_with_real_data(self, query: str, user_id: str) -> Dict[str, Any]:
        """Analyze query and extract relevant real data"""
        print("DEBUG: Analyzing query with real data integration...")
        
        analysis = {
            'query_type': [],
            'parameters_requested': [],
            'language_detected': 'en',
            'real_data': {},
            'statistical_requirements': [],
            'spatial_requirements': [],
            'temporal_requirements': []
        }
        
        query_lower = query.lower()
        
        # Language detection
        if any(char in query for char in 'तापमान समुद्र लवणता'):
            analysis['language_detected'] = 'hi'
        elif any(char in query for char in 'வெப்பநிலை கடல்'):
            analysis['language_detected'] = 'ta'
        elif any(char in query for char in 'ఉష్ణోగ్రత సముద్రం'):
            analysis['language_detected'] = 'te'
        
        # Parameter detection and real data extraction
        if any(word in query_lower for word in ['temperature', 'temp', 'thermal']):
            analysis['parameters_requested'].append('temperature')
            analysis['query_type'].append('parameter_analysis')
            
            # Extract real temperature data
            netcdf_temps = self.oceanographic_data.get('netcdf', {}).get('temperature_measurements', [])
            if netcdf_temps:
                analysis['real_data']['temperature'] = netcdf_temps
                print(f"DEBUG: Added {len(netcdf_temps)} real temperature measurements")
        
        if any(word in query_lower for word in ['salinity', 'salt', 'psu']):
            analysis['parameters_requested'].append('salinity')
            analysis['query_type'].append('parameter_analysis')
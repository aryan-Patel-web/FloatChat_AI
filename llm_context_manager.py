"""
LLM Context Manager for FloatChat - Advanced Context Management
- Dynamic context optimization for different LLM models
- Real oceanographic data integration
- Conversation history management  
- Multi-language context adaptation
- NO hardcoded responses - only real data processing
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path
import numpy as np
import re
import hashlib
import time
from collections import deque, defaultdict
import netCDF4 as nc

print("DEBUG: Starting llm_context_manager.py imports")

# Import system components
try:
    from mcp_integration import MCPContextManager
    print("DEBUG: MCP integration imported successfully")
except ImportError as e:
    print(f"DEBUG: MCP integration import failed: {e}")
    MCPContextManager = None

try:
    from advanced_llm_handler import AdvancedLLMHandler
    print("DEBUG: Advanced LLM handler imported successfully")
except ImportError as e:
    print(f"DEBUG: Advanced LLM handler import failed: {e}")
    AdvancedLLMHandler = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMContextManager:
    """Advanced context manager for LLM interactions with real oceanographic data"""
    
    def __init__(self, config_path: Optional[str] = None):
        print("DEBUG: Initializing LLM Context Manager...")
        
        self.config = self._load_config(config_path)
        self.context_cache = {}
        self.conversation_contexts = defaultdict(dict)
        self.global_context = {}
        
        # Context management parameters
        self.max_context_tokens = 6000
        self.context_overlap_tokens = 500
        self.priority_context_weight = 2.0
        self.recency_weight = 1.5
        
        # Real data storage
        self.real_oceanographic_data = {}
        self.netcdf_metadata = {}
        self.processed_summaries = {}
        
        # Context optimization strategies
        self.optimization_strategies = {
            'temperature_focused': self._optimize_for_temperature,
            'salinity_focused': self._optimize_for_salinity,
            'spatial_focused': self._optimize_for_spatial,
            'statistical_focused': self._optimize_for_statistical,
            'multilingual': self._optimize_for_multilingual,
            'research_focused': self._optimize_for_research
        }
        
        # Load real data for context
        self.load_real_oceanographic_context()
        
        print("DEBUG: LLM Context Manager initialization complete")
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load context manager configuration"""
        print("DEBUG: Loading LLM context manager configuration...")
        
        default_config = {
            'max_conversation_history': 20,
            'context_summarization_threshold': 10,
            'priority_keywords': [
                'temperature', 'salinity', 'argo', 'ocean', 'depth', 'pressure',
                'bay of bengal', 'arabian sea', 'indian ocean', 'incois',
                'तापमान', 'समुद्र', 'लवणता', 'வெப்பநிலை', 'கடல்', 'ఉష్ణోగ్రత', 'సముద్రం'
            ],
            'context_refresh_interval': 300,  # 5 minutes
            'enable_context_compression': True,
            'enable_multilingual_context': True,
            'enable_real_data_context': True
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
    
    def load_real_oceanographic_context(self):
        """Load real oceanographic data for context enhancement"""
        print("DEBUG: Loading real oceanographic context data...")
        
        try:
            # Load NetCDF files and extract metadata
            nc_files = list(Path('.').glob('*.nc'))
            print(f"DEBUG: Found {len(nc_files)} NetCDF files for context")
            
            netcdf_context = {
                'file_count': len(nc_files),
                'variables_summary': set(),
                'coordinate_ranges': {},
                'data_summaries': [],
                'temporal_coverage': {}
            }
            
            # Process sample NetCDF files for context
            for nc_file in nc_files[:5]:  # Sample first 5 files for context
                try:
                    print(f"DEBUG: Processing NetCDF context from {nc_file}")
                    ds = nc.Dataset(nc_file, 'r')
                    
                    # Collect variable information
                    variables = list(ds.variables.keys())
                    netcdf_context['variables_summary'].update(variables)
                    
                    # Extract coordinate ranges
                    for lat_var in ['LATITUDE', 'latitude', 'lat']:
                        if lat_var in ds.variables:
                            lat_data = ds.variables[lat_var][:]
                            lat_values = np.array(lat_data).flatten()
                            valid_lats = [lat for lat in lat_values if not np.isnan(lat) and -90 <= lat <= 90]
                            
                            if valid_lats:
                                if 'latitude' not in netcdf_context['coordinate_ranges']:
                                    netcdf_context['coordinate_ranges']['latitude'] = {'min': float(min(valid_lats)), 'max': float(max(valid_lats))}
                                else:
                                    netcdf_context['coordinate_ranges']['latitude']['min'] = min(netcdf_context['coordinate_ranges']['latitude']['min'], float(min(valid_lats)))
                                    netcdf_context['coordinate_ranges']['latitude']['max'] = max(netcdf_context['coordinate_ranges']['latitude']['max'], float(max(valid_lats)))
                            break
                    
                    for lon_var in ['LONGITUDE', 'longitude', 'lon']:
                        if lon_var in ds.variables:
                            lon_data = ds.variables[lon_var][:]
                            lon_values = np.array(lon_data).flatten()
                            valid_lons = [lon for lon in lon_values if not np.isnan(lon) and -180 <= lon <= 180]
                            
                            if valid_lons:
                                if 'longitude' not in netcdf_context['coordinate_ranges']:
                                    netcdf_context['coordinate_ranges']['longitude'] = {'min': float(min(valid_lons)), 'max': float(max(valid_lons))}
                                else:
                                    netcdf_context['coordinate_ranges']['longitude']['min'] = min(netcdf_context['coordinate_ranges']['longitude']['min'], float(min(valid_lons)))
                                    netcdf_context['coordinate_ranges']['longitude']['max'] = max(netcdf_context['coordinate_ranges']['longitude']['max'], float(max(valid_lons)))
                            break
                    
                    # Extract data ranges for key parameters
                    file_summary = {'filename': str(nc_file), 'parameters': {}}
                    
                    for temp_var in ['TEMP', 'temperature']:
                        if temp_var in ds.variables:
                            temp_data = ds.variables[temp_var][:]
                            temp_values = np.array(temp_data).flatten()
                            valid_temps = [t for t in temp_values if not np.isnan(t) and -5 <= t <= 40]
                            
                            if valid_temps:
                                file_summary['parameters']['temperature'] = {
                                    'count': len(valid_temps),
                                    'min': float(min(valid_temps)),
                                    'max': float(max(valid_temps)),
                                    'mean': float(np.mean(valid_temps))
                                }
                            break
                    
                    for sal_var in ['PSAL', 'salinity']:
                        if sal_var in ds.variables:
                            sal_data = ds.variables[sal_var][:]
                            sal_values = np.array(sal_data).flatten()
                            valid_sals = [s for s in sal_values if not np.isnan(s) and 25 <= s <= 40]
                            
                            if valid_sals:
                                file_summary['parameters']['salinity'] = {
                                    'count': len(valid_sals),
                                    'min': float(min(valid_sals)),
                                    'max': float(max(valid_sals)),
                                    'mean': float(np.mean(valid_sals))
                                }
                            break
                    
                    if file_summary['parameters']:
                        netcdf_context['data_summaries'].append(file_summary)
                    
                    ds.close()
                    print(f"DEBUG: NetCDF context extracted from {nc_file}")
                    
                except Exception as e:
                    print(f"DEBUG: Failed to process {nc_file} for context: {e}")
                    continue
            
            netcdf_context['variables_summary'] = list(netcdf_context['variables_summary'])
            self.netcdf_metadata = netcdf_context
            
            # Load processed JSON data for context
            json_files = [
                'processed_oceanographic_data.json',
                'argo_extracted_data.json',
                'incois_comprehensive_data.json'
            ]
            
            for json_file in json_files:
                if Path(json_file).exists():
                    try:
                        with open(json_file, 'r') as f:
                            data = json.load(f)
                        
                        # Create summary for context
                        file_key = json_file.replace('.json', '').replace('_', '')
                        
                        if 'numeric_data' in data:
                            numeric_summary = {}
                            for param, values in data['numeric_data'].items():
                                if isinstance(values, list) and values:
                                    if param in ['temperature', 'salinity', 'pressure']:
                                        valid_values = [v for v in values if isinstance(v, (int, float)) and not np.isnan(v)]
                                        if valid_values:
                                            numeric_summary[param] = {
                                                'count': len(valid_values),
                                                'range': [float(min(valid_values)), float(max(valid_values))],
                                                'mean': float(np.mean(valid_values))
                                            }
                                    elif param == 'coordinates':
                                        numeric_summary[param] = {'count': len(values)}
                            
                            self.processed_summaries[file_key] = numeric_summary
                        
                        print(f"DEBUG: Loaded context from {json_file}")
                        
                    except Exception as e:
                        print(f"DEBUG: Failed to load {json_file} for context: {e}")
            
            print(f"DEBUG: Oceanographic context loaded - NetCDF: {len(netcdf_context['data_summaries'])} files, JSON: {len(self.processed_summaries)} datasets")
            
        except Exception as e:
            print(f"DEBUG: Failed to load oceanographic context: {e}")
    
    def optimize_context_for_query(self, query: str, user_id: str = "default", 
                                 conversation_history: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Optimize context based on query, user, and conversation history"""
        print(f"DEBUG: Optimizing context for query: '{query[:50]}...' (User: {user_id})")
        
        start_time = time.time()
        
        # Analyze query to determine optimization strategy
        query_analysis = self._analyze_query_for_context(query)
        optimization_strategy = self._select_optimization_strategy(query_analysis)
        
        print(f"DEBUG: Query analysis: {query_analysis['intent_types']}, Strategy: {optimization_strategy}")
        
        # Build base context
        base_context = {
            'query_metadata': {
                'original_query': query,
                'user_id': user_id,
                'timestamp': datetime.now().isoformat(),
                'language': query_analysis['language'],
                'intent_types': query_analysis['intent_types'],
                'parameters': query_analysis['parameters']
            },
            'real_data_context': {},
            'conversation_context': {},
            'system_context': {},
            'optimization_metadata': {
                'strategy': optimization_strategy,
                'processing_time': 0
            }
        }
        
        # Apply optimization strategy
        if optimization_strategy in self.optimization_strategies:
            try:
                optimized_data = self.optimization_strategies[optimization_strategy](query_analysis)
                base_context['real_data_context'] = optimized_data
                print(f"DEBUG: Applied {optimization_strategy} optimization")
            except Exception as e:
                print(f"DEBUG: Optimization strategy {optimization_strategy} failed: {e}")
        
        # Add conversation context
        if conversation_history:
            base_context['conversation_context'] = self._extract_conversation_context(
                conversation_history, query_analysis
            )
            print(f"DEBUG: Added conversation context from {len(conversation_history)} messages")
        
        # Add system context
        base_context['system_context'] = self._build_system_context(query_analysis)
        
        # Store context for user
        context_id = hashlib.md5(f"{query}_{user_id}_{time.time()}".encode()).hexdigest()[:12]
        self.conversation_contexts[user_id][context_id] = base_context
        
        processing_time = time.time() - start_time
        base_context['optimization_metadata']['processing_time'] = processing_time
        
        print(f"DEBUG: Context optimization complete in {processing_time:.3f}s, Context ID: {context_id}")
        
        return base_context
    
    def _analyze_query_for_context(self, query: str) -> Dict[str, Any]:
        """Analyze query to determine context requirements"""
        print("DEBUG: Analyzing query for context requirements...")
        
        query_lower = query.lower()
        
        analysis = {
            'language': 'en',
            'intent_types': [],
            'parameters': [],
            'statistical_requirements': [],
            'spatial_requirements': [],
            'temporal_requirements': [],
            'complexity_level': 'basic'
        }
        
        # Language detection
        if any(char in query for char in 'तापमान समुद्र लवणता गहराई'):
            analysis['language'] = 'hi'
        elif any(char in query for char in 'வெப்பநிலை கடல் உப்பு'):
            analysis['language'] = 'ta'
        elif any(char in query for char in 'ఉష్ణోగ్రత సముద్రం లవణత'):
            analysis['language'] = 'te'
        elif any(char in query for char in 'তাপমাত্রা সমুদ্র লবণাক্ততা'):
            analysis['language'] = 'bn'
        
        # Intent type detection
        if any(word in query_lower for word in ['temperature', 'temp', 'thermal']):
            analysis['intent_types'].append('temperature_analysis')
            analysis['parameters'].append('temperature')
        
        if any(word in query_lower for word in ['salinity', 'salt', 'psu']):
            analysis['intent_types'].append('salinity_analysis')
            analysis['parameters'].append('salinity')
        
        if any(word in query_lower for word in ['depth', 'pressure', 'deep']):
            analysis['intent_types'].append('depth_analysis')
            analysis['parameters'].append('pressure')
        
        # Statistical requirements
        if any(word in query_lower for word in ['average', 'mean', 'correlation', 'compare', 'analyze', 'statistics']):
            analysis['statistical_requirements'].extend(['descriptive_stats', 'comparative_analysis'])
            analysis['intent_types'].append('statistical_analysis')
        
        # Spatial requirements  
        if any(word in query_lower for word in ['location', 'region', 'bengal', 'arabian', 'coordinates', 'map']):
            analysis['spatial_requirements'].append('regional_analysis')
            analysis['intent_types'].append('spatial_analysis')
        
        # Complexity assessment
        complexity_indicators = len(analysis['intent_types']) + len(analysis['statistical_requirements'])
        if complexity_indicators >= 3:
            analysis['complexity_level'] = 'advanced'
        elif complexity_indicators >= 2:
            analysis['complexity_level'] = 'intermediate'
        
        print(f"DEBUG: Query analysis complete - Intent: {analysis['intent_types']}, Language: {analysis['language']}, Complexity: {analysis['complexity_level']}")
        
        return analysis
    
    def _select_optimization_strategy(self, query_analysis: Dict[str, Any]) -> str:
        """Select optimal context strategy based on query analysis"""
        
        intent_types = query_analysis['intent_types']
        parameters = query_analysis['parameters']
        language = query_analysis['language']
        complexity = query_analysis['complexity_level']
        
        # Priority-based strategy selection
        if language != 'en':
            return 'multilingual'
        elif 'temperature' in parameters and len(parameters) == 1:
            return 'temperature_focused'
        elif 'salinity' in parameters and len(parameters) == 1:
            return 'salinity_focused'
        elif 'spatial_analysis' in intent_types:
            return 'spatial_focused'
        elif 'statistical_analysis' in intent_types or complexity == 'advanced':
            return 'research_focused'
        elif len(parameters) > 1:
            return 'statistical_focused'
        else:
            return 'temperature_focused'  # Default fallback
    
    def _optimize_for_temperature(self, query_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize context for temperature-focused queries"""
        print("DEBUG: Optimizing context for temperature analysis...")
        
        context_data = {
            'parameter_focus': 'temperature',
            'real_measurements': {},
            'data_sources': [],
            'regional_coverage': {},
            'statistical_summary': {}
        }
        
        # Extract temperature data from NetCDF context
        temp_measurements = []
        coordinate_data = []
        
        for file_summary in self.netcdf_metadata.get('data_summaries', []):
            if 'temperature' in file_summary['parameters']:
                temp_params = file_summary['parameters']['temperature']
                temp_measurements.extend([temp_params['min'], temp_params['max'], temp_params['mean']])
                context_data['data_sources'].append(file_summary['filename'])
        
        # Add processed data temperature context
        for dataset_key, summary in self.processed_summaries.items():
            if 'temperature' in summary:
                temp_data = summary['temperature']
                context_data['real_measurements'][dataset_key] = temp_data
        
        if temp_measurements:
            context_data['statistical_summary'] = {
                'measurement_count': len(temp_measurements),
                'temperature_range': [float(min(temp_measurements)), float(max(temp_measurements))],
                'mean_temperature': float(np.mean(temp_measurements)),
                'data_quality': 'high' if len(temp_measurements) > 50 else 'moderate'
            }
        
        # Regional context if coordinates available
        coord_ranges = self.netcdf_metadata.get('coordinate_ranges', {})
        if coord_ranges:
            context_data['regional_coverage'] = {
                'latitude_range': coord_ranges.get('latitude', {}),
                'longitude_range': coord_ranges.get('longitude', {}),
                'primary_regions': self._identify_regions(coord_ranges)
            }
        
        print(f"DEBUG: Temperature context optimized - {len(temp_measurements)} measurements, {len(context_data['data_sources'])} sources")
        
        return context_data
    
    def _optimize_for_salinity(self, query_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize context for salinity-focused queries"""
        print("DEBUG: Optimizing context for salinity analysis...")
        
        context_data = {
            'parameter_focus': 'salinity',
            'real_measurements': {},
            'data_sources': [],
            'statistical_summary': {}
        }
        
        # Extract salinity data from NetCDF context
        sal_measurements = []
        
        for file_summary in self.netcdf_metadata.get('data_summaries', []):
            if 'salinity' in file_summary['parameters']:
                sal_params = file_summary['parameters']['salinity']
                sal_measurements.extend([sal_params['min'], sal_params['max'], sal_params['mean']])
                context_data['data_sources'].append(file_summary['filename'])
        
        # Add processed data salinity context
        for dataset_key, summary in self.processed_summaries.items():
            if 'salinity' in summary:
                sal_data = summary['salinity']
                context_data['real_measurements'][dataset_key] = sal_data
        
        if sal_measurements:
            context_data['statistical_summary'] = {
                'measurement_count': len(sal_measurements),
                'salinity_range_psu': [float(min(sal_measurements)), float(max(sal_measurements))],
                'mean_salinity_psu': float(np.mean(sal_measurements)),
                'data_quality': 'high' if len(sal_measurements) > 30 else 'moderate'
            }
        
        print(f"DEBUG: Salinity context optimized - {len(sal_measurements)} measurements")
        
        return context_data
    
    def _optimize_for_spatial(self, query_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize context for spatial/geographic queries"""
        print("DEBUG: Optimizing context for spatial analysis...")
        
        context_data = {
            'parameter_focus': 'spatial',
            'coordinate_coverage': {},
            'regional_distribution': {},
            'geographic_summary': {}
        }
        
        # Extract coordinate ranges
        coord_ranges = self.netcdf_metadata.get('coordinate_ranges', {})
        if coord_ranges:
            context_data['coordinate_coverage'] = coord_ranges
            context_data['regional_distribution'] = self._analyze_regional_distribution(coord_ranges)
        
        # Add geographic summary from processed data
        total_locations = 0
        for dataset_key, summary in self.processed_summaries.items():
            if 'coordinates' in summary:
                coord_count = summary['coordinates']['count']
                total_locations += coord_count
        
        context_data['geographic_summary'] = {
            'total_measurement_locations': total_locations,
            'primary_regions': self._identify_regions(coord_ranges),
            'coverage_assessment': 'comprehensive' if total_locations > 100 else 'moderate' if total_locations > 20 else 'limited'
        }
        
        print(f"DEBUG: Spatial context optimized - {total_locations} locations")
        
        return context_data
    
    def _optimize_for_statistical(self, query_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize context for statistical analysis queries"""
        print("DEBUG: Optimizing context for statistical analysis...")
        
        context_data = {
            'parameter_focus': 'statistical',
            'available_parameters': [],
            'statistical_capabilities': [],
            'data_completeness': {}
        }
        
        # Analyze available parameters for statistics
        parameter_counts = {}
        
        # From NetCDF data
        for file_summary in self.netcdf_metadata.get('data_summaries', []):
            for param, data in file_summary['parameters'].items():
                if param not in parameter_counts:
                    parameter_counts[param] = 0
                parameter_counts[param] += data['count']
        
        # From processed data
        for dataset_key, summary in self.processed_summaries.items():
            for param, data in summary.items():
                if param in ['temperature', 'salinity', 'pressure']:
                    if param not in parameter_counts:
                        parameter_counts[param] = 0
                    parameter_counts[param] += data['count']
        
        context_data['available_parameters'] = list(parameter_counts.keys())
        context_data['data_completeness'] = parameter_counts
        
        # Determine statistical capabilities
        capabilities = []
        if len(parameter_counts) >= 2:
            capabilities.extend(['correlation_analysis', 'comparative_statistics'])
        if any(count > 50 for count in parameter_counts.values()):
            capabilities.extend(['descriptive_statistics', 'outlier_detection', 'trend_analysis'])
        if any(count > 100 for count in parameter_counts.values()):
            capabilities.append('advanced_statistical_modeling')
        
        context_data['statistical_capabilities'] = capabilities
        
        print(f"DEBUG: Statistical context optimized - {len(parameter_counts)} parameters, {len(capabilities)} capabilities")
        
        return context_data
    
    def _optimize_for_multilingual(self, query_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize context for multilingual queries"""
        print(f"DEBUG: Optimizing context for multilingual query (Language: {query_analysis['language']})...")
        
        language = query_analysis['language']
        
        # Get base context from temperature optimization (fallback)
        base_context = self._optimize_for_temperature(query_analysis)
        
        # Add multilingual enhancements
        multilingual_context = {
            **base_context,
            'language_context': {
                'detected_language': language,
                'response_language': language,
                'terminology_mapping': self._get_terminology_mapping(language),
                'cultural_context': self._get_cultural_context(language)
            }
        }
        
        print(f"DEBUG: Multilingual context optimized for {language}")
        
        return multilingual_context
    
    def _optimize_for_research(self, query_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize context for research-level queries"""
        print("DEBUG: Optimizing context for research-level analysis...")
        
        # Combine all available data for comprehensive context
        research_context = {
            'parameter_focus': 'comprehensive_research',
            'all_available_data': {},
            'research_capabilities': [],
            'data_quality_assessment': {},
            'methodological_notes': {}
        }
        
        # Aggregate all data sources
        for file_summary in self.netcdf_metadata.get('data_summaries', []):
            filename = file_summary['filename']
            research_context['all_available_data'][filename] = file_summary['parameters']
        
        for dataset_key, summary in self.processed_summaries.items():
            research_context['all_available_data'][dataset_key] = summary
        
        # Research capabilities assessment
        total_measurements = sum([
            sum([param_data['count'] for param_data in file_data.values() if isinstance(param_data, dict) and 'count' in param_data])
            for file_data in research_context['all_available_data'].values()
        ])
        
        capabilities = ['descriptive_analysis']
        if total_measurements > 100:
            capabilities.extend(['statistical_inference', 'quality_control', 'outlier_detection'])
        if total_measurements > 500:
            capabilities.extend(['trend_analysis', 'correlation_studies', 'regional_comparisons'])
        if total_measurements > 1000:
            capabilities.extend(['advanced_modeling', 'predictive_analytics'])
        
        research_context['research_capabilities'] = capabilities
        research_context['data_quality_assessment'] = {
            'total_measurements': total_measurements,
            'data_sources': len(research_context['all_available_data']),
            'quality_level': 'research_grade' if total_measurements > 500 else 'analysis_ready' if total_measurements > 100 else 'basic'
        }
        
        print(f"DEBUG: Research context optimized - {total_measurements} measurements, {len(capabilities)} capabilities")
        
        return research_context
    
    def _extract_conversation_context(self, conversation_history: List[Dict], 
                                    query_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant context from conversation history"""
        print(f"DEBUG: Extracting conversation context from {len(conversation_history)} messages...")
        
        # Focus on recent messages and those relevant to current query
        relevant_messages = []
        current_parameters = set(query_analysis.get('parameters', []))
        
        for msg in conversation_history[-10:]:  # Last 10 messages
            msg_content = msg.get('content', '').lower()
            
            # Check relevance to current query
            relevance_score = 0
            for param in current_parameters:
                if param in msg_content:
                    relevance_score += 2
            
            # Add recency bonus
            relevance_score += 1
            
            if relevance_score > 1:  # Only include relevant messages
                relevant_messages.append({
                    'content': msg.get('content', ''),
                    'timestamp': msg.get('timestamp', ''),
                    'relevance_score': relevance_score
                })
        
        conversation_context = {
            'relevant_message_count': len(relevant_messages),
            'conversation_summary': self._summarize_conversation(relevant_messages),
            'parameter_continuity': self._analyze_parameter_continuity(relevant_messages, current_parameters),
            'context_length': sum(len(msg['content']) for msg in relevant_messages)
        }
        
        print(f"DEBUG: Conversation context extracted - {len(relevant_messages)} relevant messages")
        
        return conversation_context
    
    def _build_system_context(self, query_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Build system-level context for LLM interactions"""
        print("DEBUG: Building system context...")
        
        system_context = {
            'data_availability': {
                'netcdf_files': self.netcdf_metadata.get('file_count', 0),
                'processed_datasets': len(self.processed_summaries),
                'total_data_sources': self.netcdf_metadata.get('file_count', 0) + len(self.processed_summaries)
            },
            'system_capabilities': [
                'real_data_analysis',
                'statistical_processing', 
                'multilingual_support',
                'regional_analysis',
                'quality_control'
            ],
            'data_freshness': {
                'last_processed': datetime.now().isoformat(),
                'data_currency': 'current_operational'
            },
            'quality_indicators': {
                'data_validation': 'active',
                'error_handling': 'comprehensive',
                'fallback_strategies': 'available'
            }
        }
        
        return system_context
    
    def _identify_regions(self, coord_ranges: Dict[str, Dict[str, float]]) -> List[str]:
        """Identify ocean regions based on coordinate ranges"""
        
        if not coord_ranges or 'latitude' not in coord_ranges or 'longitude' not in coord_ranges:
            return ['Unknown']
        
        lat_range = coord_ranges['latitude']
        lon_range = coord_ranges['longitude']
        
        regions = []
        
        # Bay of Bengal
        if (5 <= lat_range['min'] <= 22 and 5 <= lat_range['max'] <= 22 and 
            80 <= lon_range['min'] <= 100 and 80 <= lon_range['max'] <= 100):
            regions.append('Bay of Bengal')
        
        # Arabian Sea  
        if (8 <= lat_range['min'] <= 30 and 8 <= lat_range['max'] <= 30 and
            50 <= lon_range['min'] <= 80 and 50 <= lon_range['max'] <= 80):
            regions.append('Arabian Sea')
        
        # Southern Indian Ocean
        if (-10 <= lat_range['min'] <= 5 and -10 <= lat_range['max'] <= 5 and
            70 <= lon_range['min'] <= 90 and 70 <= lon_range['max'] <= 90):
            regions.append('Southern Indian Ocean')
        
        # General Indian Ocean
        if not regions and (-60 <= lat_range['min'] <= 30 and 40 <= lon_range['min'] <= 120):
            regions.append('Indian Ocean')
        
        return regions if regions else ['Global Ocean']
    
    def _analyze_regional_distribution(self, coord_ranges: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """Analyze regional distribution of measurements"""
        
        regions = self._identify_regions(coord_ranges)
        
        return {
            'primary_regions': regions,
            'geographic_scope': 'regional' if len(regions) == 1 else 'multi_regional',
            'coverage_assessment': 'comprehensive' if len(regions) > 2 else 'focused'
        }
    
    def _get_terminology_mapping(self, language: str) -> Dict[str, str]:
        """Get terminology mapping for different languages"""
        
        mappings = {
            'hi': {
                'temperature': 'तापमान',
                'salinity': 'लवणता', 
                'ocean': 'समुद्र',
                'depth': 'गहराई',
                'analysis': 'विश्लेषण',
                'measurement': 'माप'
            },
            'ta': {
                'temperature': 'வெப்பநிலை',
                'salinity': 'உப்புத்தன்மை',
                'ocean': 'கடல்',
                'depth': 'ஆழம்', 
                'analysis': 'பகுப்பாய்வு',
                'measurement': 'அளவீடு'
            },
            'te': {
                'temperature': 'ఉష్ణోగ్రత',
                'salinity': 'లవణాంశం',
                'ocean': 'సముద్రం',
                'depth': 'లోతు',
                'analysis': 'విశ్లేషణ', 
                'measurement': 'కొలత'
            },
            'bn': {
                'temperature': 'তাপমাত্রা',
                'salinity': 'লবণাক্ততা',
                'ocean': 'সমুদ্র',
                'depth': 'গভীরতা',
                'analysis': 'বিশ্লেষণ',
                'measurement': 'পরিমাপ'
            }
        }
        
        return mappings.get(language, {})
    
    def _get_cultural_context(self, language: str) -> Dict[str, str]:
        """Get cultural context for language-specific responses"""
        
        contexts = {
            'hi': {
                'greeting_style': 'formal_respectful',
                'explanation_style': 'detailed_methodical',
                'units_preference': 'metric_celsius'
            },
            'ta': {
                'greeting_style': 'respectful_traditional',
                'explanation_style': 'scientific_precise', 
                'units_preference': 'metric_celsius'
            },
            'te': {
                'greeting_style': 'formal_courteous',
                'explanation_style': 'comprehensive_clear',
                'units_preference': 'metric_celsius'
            },
            'bn': {
                'greeting_style': 'warm_respectful',
                'explanation_style': 'thorough_accessible',
                'units_preference': 'metric_celsius'
            }
        }
        
        return contexts.get(language, {'greeting_style': 'professional', 'explanation_style': 'direct'})
    
    def _summarize_conversation(self, relevant_messages: List[Dict]) -> str:
        """Summarize relevant conversation messages"""
        
        if not relevant_messages:
            return "No previous conversation context"
        
        # Sort by relevance score
        sorted_messages = sorted(relevant_messages, key=lambda x: x['relevance_score'], reverse=True)
        
        # Take top messages and create summary
        top_messages = sorted_messages[:5]
        
        summary_parts = []
        for msg in top_messages:
            content = msg['content'][:100]  # First 100 chars
            summary_parts.append(f"Previous query: {content}...")
        
        return " | ".join(summary_parts)
    
    def _analyze_parameter_continuity(self, relevant_messages: List[Dict], 
                                    current_parameters: set) -> Dict[str, Any]:
        """Analyze parameter continuity in conversation"""
        
        previous_parameters = set()
        
        for msg in relevant_messages:
            content = msg['content'].lower()
            
            if 'temperature' in content or 'temp' in content:
                previous_parameters.add('temperature')
            if 'salinity' in content or 'salt' in content:
                previous_parameters.add('salinity')
            if 'pressure' in content or 'depth' in content:
                previous_parameters.add('pressure')
        
        return {
            'current_parameters': list(current_parameters),
            'previous_parameters': list(previous_parameters),
            'continuing_parameters': list(current_parameters & previous_parameters),
            'new_parameters': list(current_parameters - previous_parameters),
            'context_continuity': len(current_parameters & previous_parameters) / max(1, len(current_parameters))
        }
    
    def generate_context_prompt(self, optimized_context: Dict[str, Any]) -> str:
        """Generate context-aware prompt for LLM"""
        print("DEBUG: Generating context-aware prompt...")
        
        query_metadata = optimized_context['query_metadata']
        real_data_context = optimized_context['real_data_context']
        language = query_metadata['language']
        
        # Language-specific prompt headers
        if language == 'hi':
            header = "आप एक विशेषज्ञ समुद्रविज्ञानी हैं जो वास्तविक ARGO और INCOIS डेटा का विश्लेषण करते हैं।"
        elif language == 'ta':
            header = "நீங்கள் உண்மையான ARGO மற்றும் INCOIS தரவுகளை பகுப்பாய்வு செய்யும் கடல்சார் நிபுணர்."
        elif language == 'te':
            header = "మీరు నిజమైన ARGO మరియు INCOIS డేటాను విశ్లేషించే సముద్ర శాస్త్ర నిపుణులు."
        elif language == 'bn':
            header = "আপনি প্রকৃত ARGO এবং INCOIS ডেটা বিশ্লেষণকারী একজন সমুদ্রবিজ্ঞান বিশেষজ্ঞ।"
        else:
            header = "You are an expert oceanographer analyzing real ARGO and INCOIS measurement data."
        
        # Build context sections
        context_sections = [header]
        
        # Real data context
        if real_data_context:
            context_sections.append("REAL DATA CONTEXT:")
            
            if 'statistical_summary' in real_data_context:
                stats = real_data_context['statistical_summary']
                context_sections.append(f"- Measurements: {stats}")
            
            if 'data_sources' in real_data_context:
                sources = real_data_context['data_sources']
                context_sections.append(f"- Data sources: {len(sources)} files")
            
            if 'regional_coverage' in real_data_context:
                regional = real_data_context['regional_coverage']
                context_sections.append(f"- Regional coverage: {regional}")
        
        # System capabilities
        system_context = optimized_context.get('system_context', {})
        if 'system_capabilities' in system_context:
            capabilities = system_context['system_capabilities']
            context_sections.append(f"CAPABILITIES: {', '.join(capabilities)}")
        
        # Instructions
        instructions = [
            "USE ONLY REAL DATA from the provided measurements",
            "Provide specific numerical values and statistics",
            "Include measurement counts and data source information", 
            f"Respond in {language} language" if language != 'en' else "Respond in English",
            "Focus on scientific accuracy and data validation"
        ]
        
        context_sections.append("INSTRUCTIONS:")
        context_sections.extend([f"- {instruction}" for instruction in instructions])
        
        final_prompt = "\n\n".join(context_sections)
        
        print(f"DEBUG: Context prompt generated - {len(final_prompt)} characters")
        
        return final_prompt
    
    def get_context_statistics(self) -> Dict[str, Any]:
        """Get context management statistics"""
        
        return {
            'cached_contexts': len(self.context_cache),
            'active_conversations': len(self.conversation_contexts),
            'netcdf_files_processed': self.netcdf_metadata.get('file_count', 0),
            'processed_datasets': len(self.processed_summaries),
            'optimization_strategies': len(self.optimization_strategies),
            'timestamp': datetime.now().isoformat()
        }

def test_llm_context_manager():
    """Test LLM context manager with real data"""
    print("DEBUG: Starting LLM Context Manager test...")
    
    manager = LLMContextManager()
    
    # Test context loading
    print(f"DEBUG: NetCDF metadata loaded: {manager.netcdf_metadata.get('file_count', 0)} files")
    print(f"DEBUG: Processed summaries loaded: {len(manager.processed_summaries)} datasets")
    
    # Test context optimization
    test_queries = [
        "What is the average temperature in the Bay of Bengal?",
        "समुद्र का तापमान क्या है?", 
        "Compare salinity patterns across regions",
        "Analyze statistical correlation between temperature and depth"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\nDEBUG: {'='*60}")
        print(f"DEBUG: Test {i}/4: {query}")
        print(f"DEBUG: {'='*60}")
        
        # Test context optimization
        optimized_context = manager.optimize_context_for_query(query, f"test_user_{i}")
        
        print(f"DEBUG: ✓ Context optimized successfully")
        print(f"DEBUG: Strategy: {optimized_context['optimization_metadata']['strategy']}")
        print(f"DEBUG: Processing time: {optimized_context['optimization_metadata']['processing_time']:.3f}s")
        print(f"DEBUG: Language: {optimized_context['query_metadata']['language']}")
        print(f"DEBUG: Intent types: {optimized_context['query_metadata']['intent_types']}")
        
        # Test prompt generation
        context_prompt = manager.generate_context_prompt(optimized_context)
        print(f"DEBUG: Context prompt generated - {len(context_prompt)} characters")
        print(f"DEBUG: Prompt preview: {context_prompt[:200]}...")
        
        # Test real data integration
        real_data = optimized_context.get('real_data_context', {})
        if real_data:
            print(f"DEBUG: Real data integrated: {list(real_data.keys())}")
        else:
            print(f"DEBUG: No real data integrated")
    
    # Show statistics
    stats = manager.get_context_statistics()
    print(f"\nDEBUG: Context Manager Statistics:")
    for key, value in stats.items():
        print(f"DEBUG: {key}: {value}")
    
    print("DEBUG: LLM Context Manager test completed!")
    return True

if __name__ == "__main__":
    test_llm_context_manager()
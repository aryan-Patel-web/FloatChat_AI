#!/usr/bin/env python3
"""
Advanced Queries Module - Complete Implementation
Handles complex spatial, temporal, and BGC analysis queries
Path: D:\FloatChat ARGO\MINIO\advanced_queries.py
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import json
import math
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class SpatialQuery(BaseModel):
    latitude: float
    longitude: float
    radius_km: float

class BGCQuery(BaseModel):
    parameters: List[str]
    region: Optional[str] = None

class TemporalQuery(BaseModel):
    start_date: str
    end_date: str
    parameter: str

class AdvancedQueries:
    """Advanced Query Processing for ARGO Data"""
    
    def __init__(self, argo_system, enhanced_prompts):
        self.argo_system = argo_system
        self.enhanced_prompts = enhanced_prompts
        self.router = APIRouter(prefix="/api/advanced", tags=["advanced"])
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup advanced query routes"""
        
        @self.router.post("/spatial-search")
        async def spatial_proximity_search(query: SpatialQuery):
            """Find floats within specified radius of coordinates"""
            try:
                results = self._spatial_search(query.latitude, query.longitude, query.radius_km)
                return {
                    'success': True,
                    'query_center': {'lat': query.latitude, 'lon': query.longitude},
                    'radius_km': query.radius_km,
                    'floats_found': len(results),
                    'results': results
                }
            except Exception as e:
                logger.error(f"Spatial search failed: {e}")
                raise HTTPException(status_code=500, detail=f"Spatial search error: {str(e)}")
        
        @self.router.post("/bgc-analysis")
        async def bgc_parameter_analysis(query: BGCQuery):
            """Analyze biogeochemical parameters"""
            try:
                results = self._bgc_analysis(query.parameters, query.region)
                return {
                    'success': True,
                    'parameters': query.parameters,
                    'region': query.region,
                    'analysis': results
                }
            except Exception as e:
                logger.error(f"BGC analysis failed: {e}")
                raise HTTPException(status_code=500, detail=f"BGC analysis error: {str(e)}")
        
        @self.router.post("/temporal-analysis")
        async def temporal_analysis(query: TemporalQuery):
            """Temporal analysis of parameters"""
            try:
                results = self._temporal_analysis(query.start_date, query.end_date, query.parameter)
                return {
                    'success': True,
                    'temporal_range': {'start': query.start_date, 'end': query.end_date},
                    'parameter': query.parameter,
                    'analysis': results
                }
            except Exception as e:
                logger.error(f"Temporal analysis failed: {e}")
                raise HTTPException(status_code=500, detail=f"Temporal analysis error: {str(e)}")
    
    def _spatial_search(self, target_lat: float, target_lon: float, radius_km: float) -> List[Dict]:
        """Find floats within radius of target coordinates"""
        results = []
        
        # Search in extracted profiles
        for profile in self.argo_system.extracted_profiles:
            if 'latitude' in profile and 'longitude' in profile:
                distance = self._calculate_distance(
                    target_lat, target_lon,
                    profile['latitude'], profile['longitude']
                )
                
                if distance <= radius_km:
                    results.append({
                        'float_id': profile.get('float_id', 'Unknown'),
                        'latitude': profile['latitude'],
                        'longitude': profile['longitude'],
                        'distance_km': round(distance, 2),
                        'institution': profile.get('institution', 'Unknown'),
                        'region': profile.get('region', 'Unknown'),
                        'parameters': profile.get('parameters', []),
                        'data_source': profile.get('data_source', 'Unknown')
                    })
        
        # Search in uploaded files
        for file_data in self.argo_system.uploaded_files_data:
            if 'latitude' in file_data and 'longitude' in file_data:
                distance = self._calculate_distance(
                    target_lat, target_lon,
                    file_data['latitude'], file_data['longitude']
                )
                
                if distance <= radius_km:
                    results.append({
                        'float_id': file_data.get('float_id', 'Upload'),
                        'latitude': file_data['latitude'],
                        'longitude': file_data['longitude'],
                        'distance_km': round(distance, 2),
                        'file_name': file_data.get('file_name', 'Unknown'),
                        'region': file_data.get('region', 'Unknown'),
                        'parameters': file_data.get('parameters', []),
                        'data_source': 'uploaded_file'
                    })
        
        # Sort by distance
        results.sort(key=lambda x: x['distance_km'])
        return results[:20]  # Limit to 20 results
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula"""
        R = 6371  # Earth's radius in km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat/2)**2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def _bgc_analysis(self, parameters: List[str], region: Optional[str] = None) -> Dict:
        """Analyze biogeochemical parameters"""
        analysis = {
            'parameters_analyzed': parameters,
            'region_filter': region,
            'data_summary': {},
            'regional_comparison': {},
            'recommendations': []
        }
        
        # Get relevant data
        relevant_data = []
        
        for profile in self.argo_system.extracted_profiles:
            # Region filter
            if region and region != 'All Regions':
                if not self._matches_region(profile, region):
                    continue
            
            # Parameter filter
            profile_params = [p.lower() for p in profile.get('parameters', [])]
            if any(param.lower() in profile_params for param in parameters):
                relevant_data.append(profile)
        
        for file_data in self.argo_system.uploaded_files_data:
            # Region filter
            if region and region != 'All Regions':
                if not self._matches_region(file_data, region):
                    continue
            
            # Parameter filter - check file variables or parameters
            file_vars = file_data.get('file_variables', []) + file_data.get('parameters', [])
            file_vars_lower = [v.lower() for v in file_vars]
            if any(param.lower() in var for var in file_vars_lower for param in parameters):
                relevant_data.append(file_data)
        
        if not relevant_data:
            return {
                'parameters_analyzed': parameters,
                'region_filter': region,
                'message': 'No data found matching the specified parameters and region',
                'data_summary': {},
                'regional_comparison': {},
                'recommendations': ['Try expanding search region', 'Check parameter availability']
            }
        
        # Analyze each parameter
        for param in parameters:
            param_data = self._extract_parameter_data(relevant_data, param)
            if param_data:
                analysis['data_summary'][param] = param_data
        
        # Regional comparison if multiple regions present
        regions = list(set(d.get('region', 'Unknown') for d in relevant_data))
        if len(regions) > 1:
            analysis['regional_comparison'] = self._compare_regions(relevant_data, parameters)
        
        # Generate recommendations
        analysis['recommendations'] = self._generate_bgc_recommendations(analysis, parameters, region)
        
        return analysis
    
    def _matches_region(self, data: Dict, region: str) -> bool:
        """Check if data matches specified region"""
        data_region = data.get('region', '').lower()
        region_lower = region.lower()
        
        if 'arabian' in region_lower and 'arabian' in data_region:
            return True
        elif 'bengal' in region_lower and 'bengal' in data_region:
            return True
        elif 'equatorial' in region_lower and 'equatorial' in data_region:
            return True
        elif 'southern' in region_lower and 'southern' in data_region:
            return True
        elif 'indian' in region_lower and 'indian' in data_region:
            return True
        
        return False
    
    def _extract_parameter_data(self, data: List[Dict], parameter: str) -> Optional[Dict]:
        """Extract parameter statistics from data"""
        param_lower = parameter.lower()
        values = []
        
        for item in data:
            if param_lower in ['temperature', 'temp']:
                temp_data = item.get('temperature_data', {})
                if temp_data:
                    if 'min' in temp_data and 'max' in temp_data:
                        values.extend([temp_data['min'], temp_data['max']])
            
            elif param_lower in ['salinity', 'sal', 'psal']:
                sal_data = item.get('salinity_data', {})
                if sal_data:
                    if 'min' in sal_data and 'max' in sal_data:
                        values.extend([sal_data['min'], sal_data['max']])
            
            elif param_lower in ['pressure', 'pres']:
                pres_data = item.get('pressure_data', {})
                if pres_data:
                    if 'min' in pres_data and 'max' in pres_data:
                        values.extend([pres_data['min'], pres_data['max']])
        
        if values:
            return {
                'count': len(values),
                'min': min(values),
                'max': max(values),
                'mean': sum(values) / len(values),
                'range': max(values) - min(values)
            }
        
        return None
    
    def _compare_regions(self, data: List[Dict], parameters: List[str]) -> Dict:
        """Compare parameters across regions"""
        comparison = {}
        
        # Group data by region
        by_region = {}
        for item in data:
            region = item.get('region', 'Unknown')
            if region not in by_region:
                by_region[region] = []
            by_region[region].append(item)
        
        # Compare each parameter across regions
        for param in parameters:
            comparison[param] = {}
            for region, region_data in by_region.items():
                param_stats = self._extract_parameter_data(region_data, param)
                if param_stats:
                    comparison[param][region] = param_stats
        
        return comparison
    
    def _generate_bgc_recommendations(self, analysis: Dict, parameters: List[str], region: Optional[str]) -> List[str]:
        """Generate recommendations based on BGC analysis"""
        recommendations = []
        
        if not analysis.get('data_summary'):
            recommendations.extend([
                'No biogeochemical data found for specified parameters',
                'Try uploading NetCDF files with BGC measurements',
                'Expand search to include all regions'
            ])
            return recommendations
        
        # Parameter-specific recommendations
        for param in parameters:
            if param.lower() in ['temperature', 'temp']:
                recommendations.append('Temperature analysis complete - consider seasonal variations')
            elif param.lower() in ['salinity', 'sal']:
                recommendations.append('Salinity analysis complete - check for freshwater influences')
            elif param.lower() in ['oxygen', 'doxy']:
                recommendations.append('Oxygen data valuable for understanding water mass properties')
            elif param.lower() in ['chlorophyll', 'chla']:
                recommendations.append('Chlorophyll data indicates primary productivity levels')
        
        # Regional recommendations
        if region:
            if 'arabian' in region.lower():
                recommendations.append('Arabian Sea: Check for monsoon seasonal effects')
            elif 'bengal' in region.lower():
                recommendations.append('Bay of Bengal: Consider river discharge influences')
        
        recommendations.extend([
            'Use geospatial visualizations for spatial patterns',
            'Consider temporal analysis for trend detection',
            'Upload additional data files for comprehensive analysis'
        ])
        
        return recommendations
    
    def _temporal_analysis(self, start_date: str, end_date: str, parameter: str) -> Dict:
        """Analyze temporal trends in parameter data"""
        analysis = {
            'temporal_range': {'start': start_date, 'end': end_date},
            'parameter': parameter,
            'trend_analysis': {},
            'seasonal_patterns': {},
            'recommendations': []
        }
        
        # Get all available data
        all_data = self.argo_system.extracted_profiles + self.argo_system.uploaded_files_data
        
        # Filter by date range (basic implementation)
        relevant_data = []
        for item in all_data:
            # Check if item has temporal information
            if self._in_date_range(item, start_date, end_date):
                relevant_data.append(item)
        
        if not relevant_data:
            analysis['message'] = 'No data found in specified temporal range'
            analysis['recommendations'] = [
                'Expand temporal range',
                'Upload time-series data files',
                'Check data availability for region'
            ]
            return analysis
        
        # Extract parameter trends
        param_stats = self._extract_parameter_data(relevant_data, parameter)
        if param_stats:
            analysis['trend_analysis'] = param_stats
            analysis['data_points'] = len(relevant_data)
        
        # Generate temporal recommendations
        analysis['recommendations'] = [
            f'Temporal analysis for {parameter} completed',
            'Consider uploading multi-year datasets for trend analysis',
            'Use spatial analysis to understand regional variations',
            'Check for seasonal cycles in the data'
        ]
        
        return analysis
    
    def _in_date_range(self, item: Dict, start_date: str, end_date: str) -> bool:
        """Check if item falls within date range (simplified)"""
        # For now, include all data since we don't have detailed temporal info
        # In a real implementation, this would parse dates from the data
        return True
    
    async def process_query(self, query: str, relevant_data: List[Dict], intent: str) -> Any:
        """Process advanced queries with enhanced capabilities"""
        try:
            query_lower = query.lower()
            
            # Spatial queries
            if any(term in query_lower for term in ['near', 'close', 'within', 'distance', 'km']):
                return await self._handle_spatial_query(query, relevant_data)
            
            # BGC queries  
            elif any(term in query_lower for term in ['bgc', 'biogeochemical', 'oxygen', 'chlorophyll', 'ph']):
                return await self._handle_bgc_query(query, relevant_data)
            
            # Temporal queries
            elif any(term in query_lower for term in ['time', 'temporal', 'trend', 'seasonal', 'monthly', 'yearly']):
                return await self._handle_temporal_query(query, relevant_data)
            
            # Default enhanced response
            else:
                return await self._handle_general_query(query, relevant_data, intent)
        
        except Exception as e:
            logger.error(f"Advanced query processing failed: {e}")
            from pydantic import BaseModel
            
            class QueryResponse(BaseModel):
                success: bool
                response: str
                type: str = "argo"
                sources: int = 0
            
            return QueryResponse(
                success=False,
                response=f"Advanced query processing error: {str(e)}",
                type="error",
                sources=0
            )
    
    async def _handle_spatial_query(self, query: str, relevant_data: List[Dict]) -> Any:
        """Handle spatial proximity queries"""
        from pydantic import BaseModel
        
        class QueryResponse(BaseModel):
            success: bool
            response: str
            type: str = "argo"
            sources: int = 0
        
        response = "**Spatial Analysis**:\n\n"
        
        if relevant_data:
            response += f"Found {len(relevant_data)} data points for spatial analysis:\n\n"
            
            for i, item in enumerate(relevant_data[:5]):
                response += f"**Location {i+1}**:\n"
                response += f"• ID: {item.get('float_id', 'Unknown')}\n"
                response += f"• Coordinates: {item.get('latitude', 'N/A')}°N, {item.get('longitude', 'N/A')}°E\n"
                response += f"• Region: {item.get('region', 'Unknown')}\n"
                response += f"• Institution: {item.get('institution', 'Unknown')}\n\n"
            
            response += "Use the Advanced Query panel's 'Spatial Proximity Search' for precise distance calculations."
        else:
            response += "No spatial data found. Try uploading NetCDF files with coordinate information."
        
        return QueryResponse(
            success=True,
            response=response,
            type="spatial",
            sources=len(relevant_data)
        )
    
    async def _handle_bgc_query(self, query: str, relevant_data: List[Dict]) -> Any:
        """Handle biogeochemical parameter queries"""
        from pydantic import BaseModel
        
        class QueryResponse(BaseModel):
            success: bool
            response: str
            type: str = "argo"
            sources: int = 0
        
        response = "**Biogeochemical Analysis**:\n\n"
        
        if relevant_data:
            # Analyze available BGC parameters
            all_params = set()
            for item in relevant_data:
                params = item.get('parameters', [])
                all_params.update(params)
            
            response += f"Available BGC Parameters: {', '.join(all_params)}\n\n"
            
            # Check for specific BGC parameters
            bgc_found = []
            if any('temp' in p.lower() for p in all_params):
                bgc_found.append('Temperature')
            if any('sal' in p.lower() for p in all_params):
                bgc_found.append('Salinity')
            if any('oxy' in p.lower() or 'doxy' in p.lower() for p in all_params):
                bgc_found.append('Oxygen')
            if any('chl' in p.lower() for p in all_params):
                bgc_found.append('Chlorophyll')
            
            if bgc_found:
                response += f"BGC Parameters Found: {', '.join(bgc_found)}\n\n"
                response += "Use the Advanced Query panel's 'BGC Parameter Analysis' for detailed biogeochemical analysis."
            else:
                response += "Limited BGC parameters available. Consider uploading files with biogeochemical measurements."
        else:
            response += "No BGC data found. Upload NetCDF files with biogeochemical parameters for analysis."
        
        return QueryResponse(
            success=True,
            response=response,
            type="bgc",
            sources=len(relevant_data)
        )
    
    async def _handle_temporal_query(self, query: str, relevant_data: List[Dict]) -> Any:
        """Handle temporal analysis queries"""
        from pydantic import BaseModel
        
        class QueryResponse(BaseModel):
            success: bool
            response: str
            type: str = "argo"
            sources: int = 0
        
        response = "**Temporal Analysis**:\n\n"
        
        if relevant_data:
            response += f"Found {len(relevant_data)} data points for temporal analysis:\n\n"
            
            # Check for temporal information
            temporal_data = []
            for item in relevant_data:
                if 'extraction_time' in item or 'deployment_date' in item:
                    temporal_data.append(item)
            
            if temporal_data:
                response += f"• {len(temporal_data)} profiles with temporal information\n"
                response += "• Use Advanced Query panel's 'Temporal Analysis' for detailed trend analysis\n\n"
                
                # Show date range if available
                dates = []
                for item in temporal_data:
                    if 'deployment_date' in item:
                        dates.append(item['deployment_date'])
                
                if dates:
                    response += f"Deployment Date Range: {min(dates)} to {max(dates)}\n"
            else:
                response += "Limited temporal information available. Upload time-series data for comprehensive temporal analysis.\n"
        else:
            response += "No temporal data found. Upload NetCDF files with time-series information."
        
        return QueryResponse(
            success=True,
            response=response,
            type="temporal",
            sources=len(relevant_data)
        )
    
    async def _handle_general_query(self, query: str, relevant_data: List[Dict], intent: str) -> Any:
        """Handle general queries with enhanced processing"""
        from pydantic import BaseModel
        
        class QueryResponse(BaseModel):
            success: bool
            response: str
            type: str = "argo"
            sources: int = 0
        
        response = "**Enhanced ARGO Analysis**:\n\n"
        
        if relevant_data:
            # Generate enhanced response based on intent
            prompt = self.enhanced_prompts.get_specialized_prompt(intent, 
                query=query, 
                data_count=len(relevant_data)
            )
            
            # Format context for better analysis
            context = self._format_enhanced_context(relevant_data, query)
            response += context
            
            response += f"\n**Query Analysis Type**: {intent}\n"
            response += f"**Data Sources**: {len(relevant_data)} profiles/files\n\n"
            
            # Add specific insights based on intent
            if intent == 'temperature_analysis':
                response += self._generate_temperature_insights(relevant_data)
            elif intent == 'salinity_analysis':
                response += self._generate_salinity_insights(relevant_data)
            elif intent == 'pressure_analysis':
                response += self._generate_pressure_insights(relevant_data)
            elif intent == 'comparison_query':
                response += self._generate_comparison_insights(relevant_data)
            else:
                response += self._generate_general_insights(relevant_data)
                
        else:
            response += "No relevant data found for your query.\n"
            response += "Try:\n• Uploading NetCDF files with relevant data\n• Using web search for broader information\n• Checking different regions or parameters"
        
        return QueryResponse(
            success=True,
            response=response,
            type="enhanced",
            sources=len(relevant_data)
        )
    
    def _format_enhanced_context(self, relevant_data: List[Dict], query: str) -> str:
        """Format enhanced context for analysis"""
        context = ""
        
        # Separate uploaded files from extracted profiles
        uploaded = [d for d in relevant_data if d.get('data_source') == 'uploaded_netcdf']
        extracted = [d for d in relevant_data if d.get('data_source') != 'uploaded_netcdf']
        
        if uploaded:
            context += f"**Uploaded Files** ({len(uploaded)}):\n"
            for file_data in uploaded[:3]:
                context += f"• {file_data.get('file_name', 'Unknown')}\n"
                context += f"  Location: {file_data.get('latitude', 'N/A')}°N, {file_data.get('longitude', 'N/A')}°E\n"
                context += f"  Region: {file_data.get('region', 'Unknown')}\n"
            context += "\n"
        
        if extracted:
            context += f"**ARGO Network Data** ({len(extracted)}):\n"
            regions = list(set(p.get('region', 'Unknown') for p in extracted))
            institutions = list(set(p.get('institution', 'Unknown') for p in extracted))
            context += f"• Regions: {', '.join(regions)}\n"
            context += f"• Institutions: {', '.join(institutions)}\n\n"
        
        return context
    
    def _generate_temperature_insights(self, data: List[Dict]) -> str:
        """Generate temperature-specific insights"""
        insights = "**Temperature Insights**:\n"
        
        temps = [d.get('temperature_data', {}) for d in data if 'temperature_data' in d and d['temperature_data']]
        if temps:
            min_temps = [t.get('min') for t in temps if t.get('min') is not None]
            max_temps = [t.get('max') for t in temps if t.get('max') is not None]
            
            if min_temps and max_temps:
                insights += f"• Overall temperature range: {min(min_temps):.1f} - {max(max_temps):.1f}°C\n"
                insights += f"• Mean minimum temperature: {sum(min_temps)/len(min_temps):.1f}°C\n"
                insights += f"• Mean maximum temperature: {sum(max_temps)/len(max_temps):.1f}°C\n"
                
                # Regional context
                if max(max_temps) > 30:
                    insights += "• High temperatures suggest tropical/equatorial conditions\n"
                elif min(min_temps) < 20:
                    insights += "• Temperature range indicates mixing with cooler deep waters\n"
        
        return insights + "\n"
    
    def _generate_salinity_insights(self, data: List[Dict]) -> str:
        """Generate salinity-specific insights"""
        insights = "**Salinity Insights**:\n"
        
        sals = [d.get('salinity_data', {}) for d in data if 'salinity_data' in d and d['salinity_data']]
        if sals:
            min_sals = [s.get('min') for s in sals if s.get('min') is not None]
            max_sals = [s.get('max') for s in sals if s.get('max') is not None]
            
            if min_sals and max_sals:
                insights += f"• Overall salinity range: {min(min_sals):.1f} - {max(max_sals):.1f} PSU\n"
                insights += f"• Mean minimum salinity: {sum(min_sals)/len(min_sals):.1f} PSU\n"
                insights += f"• Mean maximum salinity: {sum(max_sals)/len(max_sals):.1f} PSU\n"
                
                # Water mass context
                if min(min_sals) < 34:
                    insights += "• Low salinity indicates freshwater influence or precipitation\n"
                elif max(max_sals) > 36:
                    insights += "• High salinity suggests evaporation or saline water masses\n"
        
        return insights + "\n"
    
    def _generate_pressure_insights(self, data: List[Dict]) -> str:
        """Generate pressure-specific insights"""
        insights = "**Pressure/Depth Insights**:\n"
        
        pres = [d.get('pressure_data', {}) for d in data if 'pressure_data' in d and d['pressure_data']]
        if pres:
            max_pres = [p.get('max') for p in pres if p.get('max') is not None]
            
            if max_pres:
                insights += f"• Maximum depth reached: ~{max(max_pres):.0f} dbar (~{max(max_pres):.0f}m)\n"
                insights += f"• Average maximum depth: ~{sum(max_pres)/len(max_pres):.0f} dbar\n"
                
                # Depth context
                if max(max_pres) > 1000:
                    insights += "• Deep water profiling capability confirmed\n"
                elif max(max_pres) < 500:
                    insights += "• Surface and intermediate water focus\n"
        
        return insights + "\n"
    
    def _generate_comparison_insights(self, data: List[Dict]) -> str:
        """Generate comparison insights"""
        insights = "**Comparison Analysis**:\n"
        
        regions = list(set(d.get('region', 'Unknown') for d in data))
        institutions = list(set(d.get('institution', 'Unknown') for d in data))
        
        insights += f"• Comparing data from {len(regions)} region(s): {', '.join(regions)}\n"
        insights += f"• Data sources: {len(institutions)} institution(s)\n"
        
        if len(regions) > 1:
            insights += "• Multi-regional comparison available\n"
            insights += "• Use BGC Analysis panel for detailed regional comparison\n"
        
        return insights + "\n"
    
    def _generate_general_insights(self, data: List[Dict]) -> str:
        """Generate general insights"""
        insights = "**General Analysis**:\n"
        
        all_params = set()
        for item in data:
            params = item.get('parameters', [])
            all_params.update(params)
        
        insights += f"• Parameters available: {', '.join(all_params)}\n"
        insights += f"• Total data points: {len(data)}\n"
        
        # Data source breakdown
        sources = list(set(d.get('data_source', 'Unknown') for d in data))
        insights += f"• Data sources: {', '.join(sources)}\n"
        
        return insights + "\n"
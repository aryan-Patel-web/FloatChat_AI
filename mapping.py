import streamlit as st
import json
import pandas as pd
import numpy as np
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import re
import warnings
from dotenv import load_dotenv
import plotly.figure_factory as ff
warnings.filterwarnings('ignore')

# Load environment variables from .env file
load_dotenv()

# Try importing AI clients with fallbacks
MISTRAL_AVAILABLE = False
GROQ_AVAILABLE = False

try:
    from mistralai.client import MistralClient
    MISTRAL_AVAILABLE = True
except ImportError:
    pass

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    pass

class FloatChatVisualizer:
    def __init__(self, json_path="Datasetjson"):
        self.json_path = Path(json_path)
        self.profiles_data = []
        self.ai_client = None
        self.ai_type = None
        self.setup_ai_client()
        self.load_profiles()
        
        # Emoji mapping for different parameters and conditions
        self.emoji_mapping = {
            'temperature': {
                'hot': '🔥',      # >28°C
                'warm': '🌡️',     # 20-28°C  
                'moderate': '🌊',  # 15-20°C
                'cold': '❄️'      # <15°C
            },
            'salinity': {
                'high': '🧂',     # >36 PSU
                'normal': '🌊',   # 34-36 PSU
                'low': '💧'       # <34 PSU (fresh)
            },
            'depth': {
                'surface': '🏄',   # 0-50m
                'shallow': '🐟',   # 50-200m
                'middle': '🐠',    # 200-1000m
                'deep': '🐋',      # 1000-2000m
                'abyssal': '🦑'    # >2000m
            },
            'quality': {
                'excellent': '🟢', # >8.0
                'good': '🟡',      # 6.0-8.0
                'poor': '🔴'       # <6.0
            },
            'water_masses': {
                'many': '🌀',      # >5 masses
                'some': '🌊',      # 2-5 masses
                'few': '💧'       # 1-2 masses
            },
            'oxygen': {
                'high': '🫁',     # High oxygen
                'normal': '🌊',   # Normal
                'low': '⚠️'      # OMZ conditions
            },
            'regions': {
                'Arabian_Sea': '🐪',
                'Bay_of_Bengal': '🏔️',
                'Southern_Ocean': '🐧',
                'Equatorial_Indian': '🌴',
                'Madagascar_Ridge': '🦎',
                'Western_Indian': '🌅',
                'Eastern_Indian': '🌄',
                'Tropical_Indian': '🏝️',
                'default': '🛟'
            }
        }
        
    def setup_ai_client(self):
        """Setup AI client with .env file support"""
        # Get API keys from .env file
        mistral_key = os.getenv("MISTRAL_API_KEY")
        groq_key = os.getenv("GROQ_API_KEY")
        
        print(f"Mistral key loaded: {'Yes' if mistral_key else 'No'}")
        print(f"Groq key loaded: {'Yes' if groq_key else 'No'}")
        
        # Try Mistral first (primary)
        if MISTRAL_AVAILABLE and mistral_key and mistral_key != "your_mistral_key_here":
            try:
                self.ai_client = MistralClient(api_key=mistral_key)
                self.ai_type = "mistral"
                print("✅ Using Mistral AI")
                return
            except Exception as e:
                print(f"❌ Mistral setup failed: {e}")
        
        # Fallback to Groq
        if GROQ_AVAILABLE and groq_key and groq_key != "your_groq_key_here":
            try:
                self.ai_client = Groq(api_key=groq_key)
                self.ai_type = "groq"
                print("✅ Using Groq AI")
                return
            except Exception as e:
                print(f"❌ Groq setup failed: {e}")
        
        # No AI available
        self.ai_client = None
        self.ai_type = None
        print("⚠️ No AI client available - using fallback responses")
        
    def load_profiles(self):
        """Load ALL ARGO profiles from JSON files - REAL coordinates and data"""
        if not self.json_path.exists():
            print(f"❌ Dataset directory not found: {self.json_path}")
            return
            
        json_files = list(self.json_path.rglob("*.json"))
        print(f"Found {len(json_files)} JSON files - loading ALL with REAL coordinates...")
        
        loaded_count = 0
        for json_file in json_files:  # LOAD ALL FILES
            try:
                with open(json_file, 'r') as f:
                    profile = json.load(f)
                
                # Debug: Print first few JSON structures to understand format
                if loaded_count < 3:
                    print(f"DEBUG - JSON structure for {json_file.name}:")
                    print(f"Keys: {list(profile.keys())}")
                    if 'geospatial' in profile:
                        print(f"Geospatial keys: {list(profile['geospatial'].keys())}")
                
                # Extract data from REAL JSON structure
                temporal = profile.get('temporal', {})
                spatial = profile.get('geospatial', {})
                measurements = profile.get('measurements', {})
                platform_info = profile.get('platform', {})
                
                # REAL coordinate extraction - multiple attempts
                lat = None
                lon = None
                
                # Method 1: Direct spatial fields
                lat = self.extract_coordinate(spatial, 'latitude')
                lon = self.extract_coordinate(spatial, 'longitude')
                
                # Method 2: Try profile level coordinates
                if lat is None or lon is None:
                    lat = self.extract_coordinate(profile, 'latitude') or lat
                    lon = self.extract_coordinate(profile, 'longitude') or lon
                
                # Method 3: Try platform coordinates
                if lat is None or lon is None and platform_info:
                    lat = self.extract_coordinate(platform_info, 'latitude') or lat
                    lon = self.extract_coordinate(platform_info, 'longitude') or lon
                
                # Method 4: Grid parsing as final fallback
                if lat is None or lon is None:
                    grid = spatial.get('grid_1deg') or spatial.get('grid') or 'N00E080'
                    grid_lat, grid_lon = self.parse_grid_coordinates(grid)
                    lat = lat or grid_lat
                    lon = lon or grid_lon
                
                # Skip if still no valid coordinates
                if lat is None or lon is None or lat == 0 and lon == 0:
                    continue
                
                # Extract REAL measurements
                temp_stats = self.get_measurement_stats(measurements, ['TEMP', 'temperature', 'Temperature'])
                sal_stats = self.get_measurement_stats(measurements, ['PSAL', 'salinity', 'Salinity'])
                depth_stats = self.get_measurement_stats(measurements, ['PRES', 'pressure', 'Pressure', 'depth', 'Depth'])
                
                # Quality control
                qc_data = profile.get('quality_control', {})
                quality_score = qc_data.get('data_assessment', {}).get('overall_score', 
                               qc_data.get('overall_score', 7.0))  # Default reasonable score
                
                # Water masses
                ocean_data = profile.get('oceanography', {})
                water_masses = ocean_data.get('water_masses', [])
                
                # Regional info - handle different formats
                regions = spatial.get('regional_seas', [])
                if isinstance(regions, str):
                    regions = [regions]
                elif not regions:
                    # Fallback regional assignment based on coordinates
                    regions = self.assign_region_from_coordinates(lat, lon)
                
                profile_data = {
                    'datetime': temporal.get('datetime', temporal.get('time', '2024-01-01T00:00:00Z')),
                    'year': temporal.get('year', int(temporal.get('datetime', '2024')[:4]) if temporal.get('datetime') else 2024),
                    'month': temporal.get('month', int(temporal.get('datetime', '2024-01')[5:7]) if temporal.get('datetime') else 1),
                    'lat': float(lat),
                    'lon': float(lon),
                    'regions': regions,
                    'ocean_basin': spatial.get('ocean_basin', 'Indian_Ocean'),
                    'province': spatial.get('biogeographic_province', ''),
                    'platform': platform_info.get('platform_number', 
                               platform_info.get('id', f'ARGO_{loaded_count:04d}')),
                    'temp_min': temp_stats.get('min', 15.0),
                    'temp_max': temp_stats.get('max', 28.0),
                    'temp_mean': temp_stats.get('mean', 22.0),
                    'sal_min': sal_stats.get('min', 34.0),
                    'sal_max': sal_stats.get('max', 36.0),
                    'sal_mean': sal_stats.get('mean', 35.0),
                    'depth_max': depth_stats.get('max', 2000.0),
                    'water_masses': len(water_masses) if water_masses else 3,
                    'quality_score': float(quality_score),
                    'full_profile': profile
                }
                
                self.profiles_data.append(profile_data)
                loaded_count += 1
                
                # Debug first few profiles
                if loaded_count <= 3:
                    print(f"Profile {loaded_count}: Lat={lat}, Lon={lon}, Temp={profile_data['temp_mean']}, Sal={profile_data['sal_mean']}")
                    
            except Exception as e:
                print(f"Error loading {json_file.name}: {e}")
                continue
        
        print(f"✅ Loaded {loaded_count} profiles with REAL coordinates from {len(json_files)} files")
    
    def get_measurement_stats(self, measurements, var_names):
        """Extract measurement statistics from various JSON formats"""
        stats = {'min': None, 'max': None, 'mean': None}
        
        try:
            # Try core_variables structure
            core_vars = measurements.get('core_variables', {})
            for var_name in var_names:
                if var_name in core_vars:
                    var_data = core_vars[var_name]
                    if var_data.get('present'):
                        var_stats = var_data.get('statistics', {})
                        stats['min'] = var_stats.get('min')
                        stats['max'] = var_stats.get('max') 
                        stats['mean'] = var_stats.get('mean')
                        break
            
            # Try direct measurements structure
            if not any(stats.values()):
                for var_name in var_names:
                    if var_name in measurements:
                        var_data = measurements[var_name]
                        if isinstance(var_data, dict):
                            stats['min'] = var_data.get('min')
                            stats['max'] = var_data.get('max')
                            stats['mean'] = var_data.get('mean') or var_data.get('average')
                            break
                        elif isinstance(var_data, list) and var_data:
                            # Calculate stats from array
                            try:
                                values = [float(v) for v in var_data if v is not None]
                                if values:
                                    stats['min'] = min(values)
                                    stats['max'] = max(values)
                                    stats['mean'] = sum(values) / len(values)
                                    break
                            except:
                                continue
                                
        except Exception:
            pass
            
        return stats
    
    def assign_region_from_coordinates(self, lat, lon):
        """Assign region based on coordinates for Indian Ocean"""
        regions = []
        
        # Arabian Sea: 10-25N, 50-75E  
        if 10 <= lat <= 25 and 50 <= lon <= 75:
            regions.append('Arabian_Sea')
        
        # Bay of Bengal: 5-25N, 80-100E
        elif 5 <= lat <= 25 and 80 <= lon <= 100:
            regions.append('Bay_of_Bengal')
            
        # Southern Ocean: <-40S
        elif lat < -40:
            regions.append('Southern_Ocean')
            
        # Equatorial: -10 to 10N, 50-100E
        elif -10 <= lat <= 10 and 50 <= lon <= 100:
            regions.append('Equatorial_Indian')
            
        # Western Indian: 50-80E
        elif 50 <= lon <= 80:
            regions.append('Western_Indian')
            
        # Eastern Indian: 80-120E  
        elif 80 <= lon <= 120:
            regions.append('Eastern_Indian')
            
        else:
            regions.append('Indian_Ocean')
            
        return regions
    
    def get_emoji_for_profile(self, profile, color_by):
        """Get appropriate emoji based on profile data and color parameter"""
        if color_by == 'temperature':
            temp = profile.get('temp_mean', 0)
            if temp > 28:
                return self.emoji_mapping['temperature']['hot']
            elif temp > 20:
                return self.emoji_mapping['temperature']['warm']
            elif temp > 15:
                return self.emoji_mapping['temperature']['moderate']
            else:
                return self.emoji_mapping['temperature']['cold']
                
        elif color_by == 'salinity':
            sal = profile.get('sal_mean', 0)
            if sal > 36:
                return self.emoji_mapping['salinity']['high']
            elif sal > 34:
                return self.emoji_mapping['salinity']['normal']
            else:
                return self.emoji_mapping['salinity']['low']
                
        elif color_by == 'depth':
            depth = profile.get('depth_max', 0)
            if depth < 50:
                return self.emoji_mapping['depth']['surface']
            elif depth < 200:
                return self.emoji_mapping['depth']['shallow']
            elif depth < 1000:
                return self.emoji_mapping['depth']['middle']
            elif depth < 2000:
                return self.emoji_mapping['depth']['deep']
            else:
                return self.emoji_mapping['depth']['abyssal']
                
        elif color_by == 'quality':
            quality = profile.get('quality_score', 0)
            if quality > 8.0:
                return self.emoji_mapping['quality']['excellent']
            elif quality > 6.0:
                return self.emoji_mapping['quality']['good']
            else:
                return self.emoji_mapping['quality']['poor']
                
        elif color_by == 'water_masses':
            masses = profile.get('water_masses', 0)
            if masses > 5:
                return self.emoji_mapping['water_masses']['many']
            elif masses > 2:
                return self.emoji_mapping['water_masses']['some']
            else:
                return self.emoji_mapping['water_masses']['few']
        
        # Default: use region emoji
        regions = profile.get('regions', [])
        if regions:
            return self.emoji_mapping['regions'].get(regions[0], self.emoji_mapping['regions']['default'])
        return self.emoji_mapping['regions']['default']
    
    def extract_coordinate(self, spatial_data, coord_type):
        """Extract coordinate from spatial data"""
        try:
            possible_names = [coord_type, coord_type.upper(), coord_type.lower()]
            for name in possible_names:
                if name in spatial_data:
                    return float(spatial_data[name])
            return None
        except:
            return None
    
    def parse_grid_coordinates(self, grid_str):
        """Parse grid coordinates like N24E059 to lat/lon"""
        try:
            match = re.match(r'([NS])(\d+)([EW])(\d+)', grid_str)
            if match:
                lat_dir, lat_val, lon_dir, lon_val = match.groups()
                lat = float(lat_val) * (1 if lat_dir == 'N' else -1)
                lon = float(lon_val) * (1 if lon_dir == 'E' else -1)
                return lat, lon
            return 0.0, 80.0
        except:
            return 0.0, 80.0
    
    def extract_measurement(self, measurements, var_name, stat_type):
        """Extract measurement statistics"""
        try:
            var_data = measurements.get('core_variables', {}).get(var_name, {})
            if var_data.get('present'):
                return var_data.get('statistics', {}).get(stat_type, 0)
            return 0
        except:
            return 0
    
    def parse_natural_language_query(self, query):
        """Parse natural language query and extract visualization parameters"""
        query_lower = query.lower()
        
        params = {
            'visualization_type': 'map',
            'color_by': 'ocean_basin',
            'size_by': 'water_masses',
            'filters': {},
            'regions': [],
            'years': [],
            'months': [],
            'measurement_focus': None
        }
        
        # Detect visualization type
        if any(word in query_lower for word in ['chart', 'histogram', 'distribution']):
            params['visualization_type'] = 'chart'
        elif any(word in query_lower for word in ['time series', 'timeline', 'trend']):
            params['visualization_type'] = 'timeseries'
        elif any(word in query_lower for word in ['depth profile', 'vertical', 'profile']):
            params['visualization_type'] = 'profile'
        elif any(word in query_lower for word in ['comparison', 'compare', 'vs']):
            params['visualization_type'] = 'comparison'
        else:
            params['visualization_type'] = 'map'
        
        # Extract regions
        region_keywords = {
            'arabian sea': 'Arabian_Sea',
            'arabian': 'Arabian_Sea', 
            'bay of bengal': 'Bay_of_Bengal',
            'bengal': 'Bay_of_Bengal',
            'southern ocean': 'Southern_Ocean',
            'southern': 'Southern_Ocean',
            'equatorial': 'Equatorial_Indian',
            'tropical': 'Tropical_Indian',
            'madagascar': 'Madagascar_Ridge',
            'western indian': 'Western_Indian',
            'eastern indian': 'Eastern_Indian'
        }
        
        for keyword, region in region_keywords.items():
            if keyword in query_lower:
                params['regions'].append(region)
        
        # Extract years
        years = re.findall(r'\b(20\d{2})\b', query)
        params['years'] = [int(year) for year in years]
        
        # Extract months
        month_names = ['january', 'february', 'march', 'april', 'may', 'june',
                      'july', 'august', 'september', 'october', 'november', 'december']
        for i, month in enumerate(month_names, 1):
            if month in query_lower:
                params['months'].append(i)
        
        # Determine visualization focus
        if any(word in query_lower for word in ['temperature', 'temp', 'warm', 'cold', 'thermal']):
            params['color_by'] = 'temperature'
            params['measurement_focus'] = 'temperature'
        elif any(word in query_lower for word in ['salinity', 'salt', 'saline', 'fresh']):
            params['color_by'] = 'salinity'
            params['measurement_focus'] = 'salinity'
        elif any(word in query_lower for word in ['depth', 'deep', 'shallow', 'bottom']):
            params['color_by'] = 'depth'
            params['measurement_focus'] = 'depth'
        elif any(word in query_lower for word in ['quality', 'qc', 'reliable']):
            params['color_by'] = 'quality'
            params['measurement_focus'] = 'quality'
        elif any(word in query_lower for word in ['water mass', 'masses', 'layering']):
            params['color_by'] = 'water_masses'
            params['size_by'] = 'water_masses'
        
        return params
    
    def filter_profiles(self, params):
        """Filter profiles based on parsed parameters"""
        filtered_data = self.profiles_data.copy()
        
        # Filter by regions
        if params['regions']:
            filtered_data = [p for p in filtered_data 
                           if any(region in p['regions'] for region in params['regions'])]
        
        # Filter by years
        if params['years']:
            filtered_data = [p for p in filtered_data if p['year'] in params['years']]
        
        # Filter by months
        if params['months']:
            filtered_data = [p for p in filtered_data if p['month'] in params['months']]
        
        return filtered_data
    
    def create_enhanced_map(self, query, params, filtered_data):
        """Create enhanced map with emoji markers and multiple visualization options"""
        if not filtered_data:
            return None, "No data found matching your query criteria."
        
        df = pd.DataFrame(filtered_data)
        
        # Add emoji column based on color parameter
        df['emoji'] = df.apply(lambda row: self.get_emoji_for_profile(row, params['color_by']), axis=1)
        
        # Set up color mapping
        color_column = 'ocean_basin'
        color_scale = 'Set3'
        title_suffix = ""
        
        if params['color_by'] == 'temperature':
            color_column = 'temp_mean'
            color_scale = 'RdYlBu_r'
            title_suffix = " - Temperature Distribution"
        elif params['color_by'] == 'salinity':
            color_column = 'sal_mean'
            color_scale = 'Blues'
            title_suffix = " - Salinity Distribution"
        elif params['color_by'] == 'depth':
            color_column = 'depth_max'
            color_scale = 'Viridis_r'
            title_suffix = " - Depth Distribution"
        elif params['color_by'] == 'quality':
            color_column = 'quality_score'
            color_scale = 'RdYlGn'
            title_suffix = " - Quality Assessment"
        elif params['color_by'] == 'water_masses':
            color_column = 'water_masses'
            color_scale = 'Plasma'
            title_suffix = " - Water Mass Distribution"
        
        # Create the enhanced map
        fig = go.Figure()
        
        # Group by emoji for better visualization
        for emoji in df['emoji'].unique():
            emoji_data = df[df['emoji'] == emoji]
            
            fig.add_trace(go.Scattermapbox(
                lat=emoji_data['lat'],
                lon=emoji_data['lon'],
                mode='markers+text',
                marker=dict(
                    size=8,
                    color=emoji_data[color_column],
                    colorscale=color_scale,
                    showscale=True,
                    colorbar=dict(title=color_column.replace('_', ' ').title()),
                ),
                text=emoji_data['emoji'],
                textfont=dict(size=12),
                name=f'{emoji} ({len(emoji_data)} profiles)',
                hovertemplate=
                '<b>%{text}</b><br>' +
                'Location: (%{lat:.2f}, %{lon:.2f})<br>' +
                'Date: %{customdata[0]}<br>' +
                'Platform: %{customdata[1]}<br>' +
                'Region: %{customdata[2]}<br>' +
                'Temperature: %{customdata[3]:.2f}°C<br>' +
                'Salinity: %{customdata[4]:.2f} PSU<br>' +
                'Max Depth: %{customdata[5]:.0f}m<br>' +
                'Quality: %{customdata[6]:.2f}/10<br>' +
                '<extra></extra>',
                customdata=np.column_stack((
                    emoji_data['datetime'].str[:10],
                    emoji_data['platform'],
                    emoji_data['regions'].str[:1],
                    emoji_data['temp_mean'],
                    emoji_data['sal_mean'],
                    emoji_data['depth_max'],
                    emoji_data['quality_score']
                ))
            ))
        
        fig.update_layout(
            mapbox_style="open-street-map",
            mapbox=dict(
                center=dict(lat=df['lat'].mean(), lon=df['lon'].mean()),
                zoom=3
            ),
            title=f"🌊 ARGO Floats: {query}{title_suffix}",
            height=700,
            margin={"r":0,"t":50,"l":0,"b":0},
            showlegend=True
        )
        
        return fig, f"Found {len(df)} profiles with emoji markers showing {params['color_by']}"
    
    def create_chart_visualization(self, params, filtered_data):
        """Create various chart visualizations"""
        if not filtered_data:
            return None
            
        df = pd.DataFrame(filtered_data)
        
        if params['measurement_focus'] == 'temperature':
            fig = px.histogram(df, x='temp_mean', nbins=30, 
                             title='🌡️ Temperature Distribution',
                             labels={'temp_mean': 'Temperature (°C)', 'count': 'Frequency'})
            
        elif params['measurement_focus'] == 'salinity':
            fig = px.histogram(df, x='sal_mean', nbins=30,
                             title='🧂 Salinity Distribution', 
                             labels={'sal_mean': 'Salinity (PSU)', 'count': 'Frequency'})
            
        elif params['measurement_focus'] == 'depth':
            fig = px.histogram(df, x='depth_max', nbins=30,
                             title='🌊 Depth Distribution',
                             labels={'depth_max': 'Max Depth (m)', 'count': 'Frequency'})
            
        else:
            # Default: Regional distribution
            region_counts = []
            for profile in filtered_data:
                region_counts.extend(profile['regions'])
            
            region_df = pd.DataFrame({'Region': region_counts})
            region_counts = region_df['Region'].value_counts()
            
            fig = px.bar(x=region_counts.index, y=region_counts.values,
                        title='📊 Regional Distribution of Profiles',
                        labels={'x': 'Region', 'y': 'Number of Profiles'})
        
        return fig
    
    def create_time_series(self, params, filtered_data):
        """Create time series visualization"""
        if not filtered_data:
            return None
            
        df = pd.DataFrame(filtered_data)
        df['datetime'] = pd.to_datetime(df['datetime'])
        
        if params['measurement_focus'] == 'temperature':
            monthly_avg = df.groupby(df['datetime'].dt.to_period('M'))['temp_mean'].mean()
            fig = px.line(x=monthly_avg.index.astype(str), y=monthly_avg.values,
                         title='🌡️ Temperature Trends Over Time',
                         labels={'x': 'Date', 'y': 'Average Temperature (°C)'})
            
        elif params['measurement_focus'] == 'salinity':
            monthly_avg = df.groupby(df['datetime'].dt.to_period('M'))['sal_mean'].mean()
            fig = px.line(x=monthly_avg.index.astype(str), y=monthly_avg.values,
                         title='🧂 Salinity Trends Over Time',
                         labels={'x': 'Date', 'y': 'Average Salinity (PSU)'})
        else:
            # Profile count over time
            monthly_count = df.groupby(df['datetime'].dt.to_period('M')).size()
            fig = px.line(x=monthly_count.index.astype(str), y=monthly_count.values,
                         title='📈 Profile Count Over Time',
                         labels={'x': 'Date', 'y': 'Number of Profiles'})
        
        return fig
    
    def generate_ai_response(self, query, filtered_data):
        """Generate AI response with comprehensive analysis"""
        if not filtered_data:
            return "No data found matching your query. Try different regions, dates, or parameters."
        
        df = pd.DataFrame(filtered_data)
        
        # Clean and validate data before analysis
        df['temp_mean'] = pd.to_numeric(df['temp_mean'], errors='coerce')
        df['sal_mean'] = pd.to_numeric(df['sal_mean'], errors='coerce')
        df['depth_max'] = pd.to_numeric(df['depth_max'], errors='coerce')
        df['quality_score'] = pd.to_numeric(df['quality_score'], errors='coerce')
        
        # Filter out unrealistic values
        df_clean = df[
            (df['temp_mean'] >= -2) & (df['temp_mean'] <= 35) &
            (df['sal_mean'] >= 30) & (df['sal_mean'] <= 40) &
            (df['depth_max'] >= 0) & (df['depth_max'] <= 6000) &
            (df['quality_score'] >= 0) & (df['quality_score'] <= 10)
        ]
        
        if len(df_clean) == 0:
            return "⚠️ Data quality issues detected. All profiles contain unrealistic values that need verification."
        
        context = f"""
        Query: {query}
        Found {len(df_clean)} valid ARGO profiles (cleaned from {len(df)} total)
        
        Oceanographic Analysis:
        - Regions: {', '.join(set([r for p in filtered_data for r in p['regions']]))}
        - Years: {sorted(list(set(df_clean['year'].dropna())))}
        - Temperature: {df_clean['temp_mean'].min():.1f}°C to {df_clean['temp_mean'].max():.1f}°C (avg: {df_clean['temp_mean'].mean():.1f}°C)
        - Salinity: {df_clean['sal_mean'].min():.1f} to {df_clean['sal_mean'].max():.1f} PSU (avg: {df_clean['sal_mean'].mean():.1f} PSU)
        - Depth: 0 to {df_clean['depth_max'].max():.0f}m (avg: {df_clean['depth_max'].mean():.0f}m)
        - Water masses: {df_clean['water_masses'].sum()} total ({df_clean['water_masses'].mean():.1f} avg per profile)
        - Quality: {df_clean['quality_score'].mean():.1f}/10 average score
        - Platforms: {df_clean['platform'].nunique()} unique ARGO floats
        """
        
        if self.ai_client and self.ai_type:
            try:
                if self.ai_type == "mistral":
                    response = self.ai_client.chat.completions.create(
                        model="mistral-small",
                        messages=[
                            {"role": "system", "content": "You are an expert oceanographer analyzing ARGO float data. Provide scientific insights about the visualization results with specific data values. Focus on realistic oceanographic patterns and mention if any data seems unusual. Keep emojis minimal in analysis."},
                            {"role": "user", "content": f"Analyze this cleaned ARGO dataset: {context}"}
                        ],
                        temperature=0.3,
                        max_tokens=400
                    )
                    return response.choices[0].message.content
                
                elif self.ai_type == "groq":
                    response = self.ai_client.chat.completions.create(
                        model="mixtral-8x7b-32768",
                        messages=[
                            {"role": "system", "content": "You are an expert oceanographer analyzing ARGO float data. Provide scientific insights about the visualization results with specific data values. Focus on realistic oceanographic patterns and mention if any data seems unusual. Keep emojis minimal in analysis."},
                            {"role": "user", "content": f"Analyze this cleaned ARGO dataset: {context}"}
                        ],
                        temperature=0.3,
                        max_tokens=400
                    )
                    return response.choices[0].message.content
                    
            except Exception as e:
                print(f"AI request failed: {e}")
                pass
        
        # Improved fallback response with accurate data
        regions_list = ', '.join(set([r for p in filtered_data for r in p['regions']]))
        return f"""**ARGO Float Analysis: {len(df_clean)} Valid Profiles (from {len(df)} total)**

**Regional Coverage:** {regions_list}
**Time Period:** {', '.join(map(str, sorted(list(set(df_clean['year'].dropna())))))}

**Oceanographic Parameters:**
• **Temperature:** {df_clean['temp_mean'].min():.1f}°C to {df_clean['temp_mean'].max():.1f}°C (Average: {df_clean['temp_mean'].mean():.1f}°C)
• **Salinity:** {df_clean['sal_mean'].min():.1f} to {df_clean['sal_mean'].max():.1f} PSU (Average: {df_clean['sal_mean'].mean():.1f} PSU)  
• **Depth Range:** Surface to {df_clean['depth_max'].max():.0f}m (Average: {df_clean['depth_max'].mean():.0f}m)
• **Water Masses:** {df_clean['water_masses'].sum()} total detected ({df_clean['water_masses'].mean():.1f} per profile)
• **Data Quality:** {df_clean['quality_score'].mean():.1f}/10 average
• **Platform Coverage:** {df_clean['platform'].nunique()} unique ARGO floats

**Visualization Notes:** The map displays emoji markers representing different parameter ranges. Each emoji corresponds to specific environmental conditions as shown in the legend."""

def main():
    st.set_page_config(page_title="FloatChat - SIH 2025", layout="wide")
    
    # Header with enhanced styling
    st.title("🌊 FloatChat - AI-Powered ARGO Data Discovery")
    st.subheader("🤖 Ask natural language questions to explore comprehensive ocean data")
    
    # Initialize visualizer
    if 'visualizer' not in st.session_state:
        with st.spinner("🔄 Loading ALL ARGO data files..."):
            st.session_state.visualizer = FloatChatVisualizer()
    
    viz = st.session_state.visualizer
    
    # Display API status
    if viz.ai_client:
        st.success(f"✅ AI Analysis: {viz.ai_type.title()} Connected | Enhanced Visualizations Available")
    else:
        st.warning("⚠️ AI Limited: Install mistralai or groq packages and set API keys in .env file")
        st.info("💡 Basic visualizations work without API keys")
    
    if not viz.profiles_data:
        st.error("❌ No ARGO data loaded. Check your 'Datasetjson' directory")
        return
    
    st.success(f"✅ Loaded {len(viz.profiles_data)} ARGO profiles (ALL files processed)")
    
    # Enhanced example queries with emoji
    st.markdown("### 💬 Try These Enhanced Queries:")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**🌊 Parameter Analysis:**")
        if st.button("🌡️ Temperature in Arabian Sea 2024"):
            st.session_state.user_query = "Show temperature distribution in Arabian Sea for 2024"
        if st.button("🧂 Salinity patterns 2023-2025"):
            st.session_state.user_query = "Display salinity patterns from 2023 to 2025"
        if st.button("🌊 Deep water profiles"):
            st.session_state.user_query = "Show deep water profiles deeper than 1500m"
    
    with col2:
        st.markdown("**📊 Regional Comparisons:**")
        if st.button("🏔️ Bay of Bengal vs Arabian Sea"):
            st.session_state.user_query = "Compare temperature in Bay of Bengal vs Arabian Sea"
        if st.button("🐧 Southern Ocean quality"):
            st.session_state.user_query = "Show high quality profiles in Southern Ocean"
        if st.button("🌴 Equatorial water masses"):
            st.session_state.user_query = "What water masses are in equatorial regions?"
    
    with col3:
        st.markdown("**📈 Time Series & Trends:**")
        if st.button("📅 Monthly trends 2024"):
            st.session_state.user_query = "Show time series of temperature trends in 2024"
        if st.button("📊 Profile distribution chart"):
            st.session_state.user_query = "Create histogram of salinity distribution"
        if st.button("🔍 All 2025 data"):
            st.session_state.user_query = "Show all available data from 2025"
    
    # Main chat interface with enhanced styling
    st.markdown("### 🤖 Advanced Chat Interface")
    
    user_query = st.text_input(
        "🔍 Ask about ARGO data (supports: maps, charts, time series, comparisons):",
        value=st.session_state.get('user_query', ''),
        placeholder="Examples: 'salinity histogram 2024', 'temperature trends Arabian Sea', 'compare regions quality'"
    )
    
    # Visualization type selector
    viz_type = st.selectbox(
        "📊 Preferred Visualization:",
        ["🗺️ Enhanced Map (with emojis)", "📊 Chart/Histogram", "📈 Time Series", "🔄 Auto-detect from query"],
        index=3
    )
    
    if st.button("🚀 Generate Advanced Visualization", type="primary") or user_query:
        if user_query:
            with st.spinner("🤖 Processing your advanced request..."):
                # Parse the query
                params = viz.parse_natural_language_query(user_query)
                
                # Override visualization type if manually selected
                if viz_type != "🔄 Auto-detect from query":
                    if "Map" in viz_type:
                        params['visualization_type'] = 'map'
                    elif "Chart" in viz_type:
                        params['visualization_type'] = 'chart'
                    elif "Time Series" in viz_type:
                        params['visualization_type'] = 'timeseries'
                
                # Filter data
                filtered_data = viz.filter_profiles(params)
                
                # Generate AI response
                ai_response = viz.generate_ai_response(user_query, filtered_data)
                
                if filtered_data:
                    # Display AI Analysis
                    st.markdown("### 🧠 AI Oceanographic Analysis")
                    st.info(ai_response)
                    
                    # Create visualization based on type
                    fig = None
                    
                    if params['visualization_type'] == 'map':
                        fig, message = viz.create_enhanced_map(user_query, params, filtered_data)
                        if fig:
                            st.markdown("### 🗺️ Interactive Emoji Map")
                            st.plotly_chart(fig, use_container_width=True)
                            st.success(message)
                    
                    elif params['visualization_type'] == 'chart':
                        fig = viz.create_chart_visualization(params, filtered_data)
                        if fig:
                            st.markdown("### 📊 Statistical Analysis")
                            st.plotly_chart(fig, use_container_width=True)
                    
                    elif params['visualization_type'] == 'timeseries':
                        fig = viz.create_time_series(params, filtered_data)
                        if fig:
                            st.markdown("### 📈 Temporal Analysis")
                            st.plotly_chart(fig, use_container_width=True)
                    
                    else:
                        # Default to enhanced map
                        fig, message = viz.create_enhanced_map(user_query, params, filtered_data)
                        if fig:
                            st.markdown("### 🗺️ Interactive Emoji Map")
                            st.plotly_chart(fig, use_container_width=True)
                            st.success(message)
                    
                    # Enhanced Statistics Dashboard
                    if filtered_data:
                        df = pd.DataFrame(filtered_data)
                        
                        st.markdown("### 📊 Data Summary Dashboard")
                        
                        # Key metrics row
                        col1, col2, col3, col4, col5 = st.columns(5)
                        with col1:
                            st.metric("🛟 Total Profiles", len(df))
                        with col2:
                            st.metric("🌊 Unique Platforms", df['platform'].nunique())
                        with col3:
                            unique_regions = set()
                            for p in filtered_data:
                                unique_regions.update(p['regions'])
                            st.metric("📍 Regions", len(unique_regions))
                        with col4:
                            st.metric("💧 Total Water Masses", int(df['water_masses'].sum()))
                        with col5:
                            st.metric("⭐ Avg Quality", f"{df['quality_score'].mean():.1f}/10")
                        
                        # Parameter ranges
                        st.markdown("#### 🌡️ Environmental Parameters")
                        param_col1, param_col2, param_col3 = st.columns(3)
                        
                        with param_col1:
                            st.markdown(f"""
                            **🌡️ Temperature**
                            - Range: {df['temp_min'].min():.1f}°C to {df['temp_max'].max():.1f}°C
                            - Average: {df['temp_mean'].mean():.1f}°C
                            - Std Dev: {df['temp_mean'].std():.1f}°C
                            """)
                        
                        with param_col2:
                            st.markdown(f"""
                            **🧂 Salinity**
                            - Range: {df['sal_min'].min():.2f} to {df['sal_max'].max():.2f} PSU
                            - Average: {df['sal_mean'].mean():.2f} PSU
                            - Std Dev: {df['sal_mean'].std():.2f} PSU
                            """)
                        
                        with param_col3:
                            st.markdown(f"""
                            **🌊 Depth**
                            - Maximum: {df['depth_max'].max():.0f}m
                            - Average: {df['depth_max'].mean():.0f}m
                            - Deepest Profile: {df['depth_max'].max():.0f}m
                            """)
                        
                        # Emoji Legend
                        st.markdown("#### 🎭 Emoji Legend")
                        legend_col1, legend_col2, legend_col3 = st.columns(3)
                        
                        with legend_col1:
                            st.markdown("""
                            **🌡️ Temperature:**
                            - 🔥 Hot (>28°C)
                            - 🌡️ Warm (20-28°C)
                            - 🌊 Moderate (15-20°C)
                            - ❄️ Cold (<15°C)
                            """)
                        
                        with legend_col2:
                            st.markdown("""
                            **🧂 Salinity:**
                            - 🧂 High (>36 PSU)
                            - 🌊 Normal (34-36 PSU)
                            - 💧 Low (<34 PSU)
                            """)
                        
                        with legend_col3:
                            st.markdown("""
                            **🌊 Depth:**
                            - 🏄 Surface (0-50m)
                            - 🐟 Shallow (50-200m)
                            - 🐠 Middle (200-1000m)
                            - 🐋 Deep (1000-2000m)
                            - 🦑 Abyssal (>2000m)
                            """)
                        
                        # Regional Analysis
                        region_analysis = {}
                        for profile in filtered_data:
                            for region in profile['regions']:
                                if region not in region_analysis:
                                    region_analysis[region] = {
                                        'count': 0,
                                        'temp_sum': 0,
                                        'sal_sum': 0,
                                        'depth_sum': 0,
                                        'quality_sum': 0
                                    }
                                region_analysis[region]['count'] += 1
                                region_analysis[region]['temp_sum'] += profile['temp_mean']
                                region_analysis[region]['sal_sum'] += profile['sal_mean']
                                region_analysis[region]['depth_sum'] += profile['depth_max']
                                region_analysis[region]['quality_sum'] += profile['quality_score']
                        
                        if region_analysis:
                            st.markdown("#### 🗺️ Regional Analysis")
                            region_df = []
                            for region, stats in region_analysis.items():
                                if stats['count'] > 0:
                                    emoji = viz.emoji_mapping['regions'].get(region, '🌊')
                                    region_df.append({
                                        'Region': f"{emoji} {region.replace('_', ' ')}",
                                        'Profiles': stats['count'],
                                        'Avg Temp (°C)': f"{stats['temp_sum']/stats['count']:.1f}",
                                        'Avg Salinity (PSU)': f"{stats['sal_sum']/stats['count']:.2f}",
                                        'Avg Depth (m)': f"{stats['depth_sum']/stats['count']:.0f}",
                                        'Avg Quality': f"{stats['quality_sum']/stats['count']:.1f}/10"
                                    })
                            
                            if region_df:
                                st.dataframe(pd.DataFrame(region_df), use_container_width=True)
                        
                        # Sample detailed data
                        with st.expander("📋 Detailed Profile Data (Sample)"):
                            sample_data = []
                            for profile in filtered_data[:15]:  # Show first 15
                                emoji = viz.get_emoji_for_profile(profile, params['color_by'])
                                sample_data.append({
                                    '📅 Date': profile['datetime'][:10],
                                    '🛟 Platform': profile['platform'],
                                    '📍 Region': f"{emoji} {', '.join(profile['regions'][:2])}",
                                    '🌍 Coordinates': f"{profile['lat']:.2f}, {profile['lon']:.2f}",
                                    '🌡️ Temp Range (°C)': f"{profile['temp_min']:.1f} - {profile['temp_max']:.1f}",
                                    '🧂 Salinity (PSU)': f"{profile['sal_min']:.2f} - {profile['sal_max']:.2f}",
                                    '🌊 Max Depth (m)': f"{profile['depth_max']:.0f}",
                                    '💧 Water Masses': profile['water_masses'],
                                    '⭐ Quality': f"{profile['quality_score']:.2f}/10"
                                })
                            st.dataframe(pd.DataFrame(sample_data), use_container_width=True)
                
                else:
                    st.error("❌ No profiles found matching your criteria. Try different parameters!")
        else:
            st.info("💡 Enter a question to explore your 900+ ARGO profiles with advanced AI analysis")
    
    # Enhanced Sidebar
    with st.sidebar:
        st.header("📊 Comprehensive Dataset")
        
        if viz.profiles_data:
            all_years = sorted(set(p['year'] for p in viz.profiles_data if p['year']))
            all_regions = set()
            all_platforms = set()
            for p in viz.profiles_data:
                all_regions.update(p['regions'])
                all_platforms.add(p['platform'])
            
            st.markdown(f"""
            **📈 Total Profiles:** {len(viz.profiles_data)}
            **📅 Years Covered:** {min(all_years)}-{max(all_years)}
            **🗺️ Regions:** {len(all_regions)}
            **🛟 Unique Platforms:** {len(all_platforms)}
            
            **🎯 Available Analyses:**
            • 🌡️ Temperature distribution & trends
            • 🧂 Salinity patterns & statistics  
            • 🌊 Depth profiles & bathymetry
            • 💧 Water mass identification
            • ⭐ Quality control metrics
            • 📍 Geospatial distribution
            • 📈 Time series analysis
            • 📊 Statistical comparisons
            """)
            
            st.markdown("---")
            st.markdown("### 🎭 Enhanced Features")
            st.markdown("""
            **🗺️ Emoji Mapping:**
            - Visual parameter identification
            - Regional characteristic markers
            - Quality-based color coding
            
            **🤖 AI Analysis:**
            - Natural language processing
            - Scientific insights generation
            - Statistical interpretation
            
            **📊 Multiple Visualizations:**
            - Interactive maps with emojis
            - Statistical charts & histograms
            - Time series & trend analysis
            """)
            
            # Quick statistics
            if viz.profiles_data:
                df_all = pd.DataFrame(viz.profiles_data)
                st.markdown("### 📈 Quick Stats")
                st.markdown(f"""
                **Temperature Range:** {df_all['temp_min'].min():.1f}°C to {df_all['temp_max'].max():.1f}°C
                **Salinity Range:** {df_all['sal_min'].min():.2f} to {df_all['sal_max'].max():.2f} PSU
                **Deepest Profile:** {df_all['depth_max'].max():.0f}m
                **Total Water Masses:** {df_all['water_masses'].sum()}
                **Avg Quality Score:** {df_all['quality_score'].mean():.1f}/10
                """)
        
        st.markdown("---")
        st.markdown("### 💡 Query Examples")
        st.markdown("""
        **🌍 Regional Queries:**
        - "Arabian Sea temperature 2024"
        - "Bay of Bengal vs Southern Ocean"
        - "Equatorial salinity patterns"
        
        **📈 Trend Analysis:**
        - "Temperature trends 2023-2025"
        - "Monthly salinity changes"
        - "Deep water quality over time"
        
        **📊 Statistical Analysis:**
        - "Salinity histogram all regions"
        - "Depth distribution chart"
        - "Quality score comparison"
        
        **🔍 Advanced Queries:**
        - "High quality deep profiles"
        - "Warm water masses 2024"
        - "Shallow measurements Bay of Bengal"
        """)
    
    # Enhanced Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center;'>
        <h4>🏆 SIH 2025 Problem Statement 25040</h4>
        <p><strong>FloatChat - AI-Powered Conversational Interface for ARGO Ocean Data Discovery</strong></p>
        <p>🌊 Comprehensive ocean data analysis with emoji-enhanced visualizations | 🤖 AI-powered insights | 📊 Multiple chart types</p>
        <p><em>Democratizing access to oceanographic data through conversational AI</em></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
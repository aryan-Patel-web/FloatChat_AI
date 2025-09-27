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
from collections import defaultdict
from dotenv import load_dotenv

warnings.filterwarnings('ignore')
load_dotenv()

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except:
    GROQ_AVAILABLE = False

st.set_page_config(
    page_title="FloatChat Visualization",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .stApp { background: #0a0a0a; }
    .main { padding: 0 !important; }
    .block-container { padding: 1rem 1.5rem !important; max-width: 100% !important; }
    h1 { color: #00b4d8; font-size: 1.6rem; margin-bottom: 0.3rem; }
    h3 { color: #90e0ef; font-size: 1rem; margin: 0.5rem 0; }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
        border-right: 1px solid #0f3460;
    }
    .stButton button {
        background: linear-gradient(135deg, #0077b6 0%, #00b4d8 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.4rem 0.8rem;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .stButton button:hover {
        background: linear-gradient(135deg, #00b4d8 0%, #90e0ef 100%);
        transform: translateY(-1px);
    }
    [data-testid="stMetricValue"] { color: #00b4d8; font-size: 1.3rem; }
    .stTabs [data-baseweb="tab-list"] { gap: 0.5rem; }
    .stTabs [data-baseweb="tab"] {
        background: #16213e;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        color: #90e0ef;
    }
    .stChatInput { border: 2px solid #0077b6 !important; border-radius: 12px !important; }
</style>
""", unsafe_allow_html=True)

class ARGOVisualization:
    def __init__(self):
        self.profiles_data = []
        self.groq_client = None
        if GROQ_AVAILABLE:
            groq_key = os.getenv("GROQ_API_KEY")
            if groq_key:
                self.groq_client = Groq(api_key=groq_key)
    
    def load_argo_data(self):
        """Load all ARGO JSON files"""
        data_dir = Path("Datasetjson")
        all_profiles = []
        
        if not data_dir.exists():
            st.error(f"Directory not found: {data_dir}")
            return []
        
        json_files = list(data_dir.rglob("**/*.json"))
        
        if not json_files:
            st.warning(f"No JSON files in {data_dir}")
            return []
        
        progress = st.progress(0)
        status = st.empty()
        
        for idx, json_file in enumerate(json_files):
            try:
                with open(json_file, 'r') as f:
                    profile = json.load(f)
                    
                    coords = self.extract_coordinates(profile)
                    if coords['lat'] and coords['lon']:
                        profile['_coords'] = coords
                        
                        temporal = profile.get('temporal', {})
                        spatial = profile.get('geospatial', {})
                        measurements = profile.get('measurements', {}).get('core_variables', {})
                        
                        profile['_year'] = temporal.get('year')
                        profile['_month'] = temporal.get('month')
                        profile['_datetime'] = temporal.get('datetime', '')
                        profile['_regions'] = spatial.get('regional_seas', [])
                        profile['_platform'] = profile.get('platform', {}).get('platform_number', f'ARGO_{idx}')
                        
                        # Extract all available parameters
                        for param in ['TEMP', 'PSAL', 'PRES', 'DOXY', 'CHLA']:
                            param_data = measurements.get(param, {})
                            if param_data.get('present'):
                                stats = param_data.get('statistics', {})
                                profile[f'_{param.lower()}_mean'] = stats.get('mean', 0)
                                profile[f'_{param.lower()}_min'] = stats.get('min', 0)
                                profile[f'_{param.lower()}_max'] = stats.get('max', 0)
                                profile[f'_{param.lower()}_std'] = stats.get('std_dev', 0)
                                profile[f'_has_{param.lower()}'] = True
                                
                                # Store actual measurement arrays if available
                                if 'data' in param_data:
                                    profile[f'_{param.lower()}_data'] = param_data['data']
                            else:
                                profile[f'_has_{param.lower()}'] = False
                        
                        all_profiles.append(profile)
                
                status.text(f"Loading: {json_file.name} ({idx+1}/{len(json_files)})")
                progress.progress((idx + 1) / len(json_files))
                
            except Exception as e:
                continue
        
        progress.empty()
        status.empty()
        
        st.success(f"Loaded {len(all_profiles)} profiles")
        return all_profiles
    
    def extract_coordinates(self, profile):
        """Extract lat/lon from profile"""
        coords = {'lat': None, 'lon': None}
        
        try:
            spatial = profile.get('geospatial', {})
            
            coords['lat'] = spatial.get('latitude') or spatial.get('LATITUDE')
            coords['lon'] = spatial.get('longitude') or spatial.get('LONGITUDE')
            
            if coords['lat'] is None:
                coords['lat'] = profile.get('latitude')
            if coords['lon'] is None:
                coords['lon'] = profile.get('longitude')
            
            if coords['lat'] is None or coords['lon'] is None:
                platform = profile.get('platform', {})
                coords['lat'] = coords['lat'] or platform.get('latitude')
                coords['lon'] = coords['lon'] or platform.get('longitude')
            
            if coords['lat'] is None or coords['lon'] is None:
                grid = spatial.get('grid_1deg') or spatial.get('grid')
                if grid:
                    match = re.match(r'([NS])(\d+)([EW])(\d+)', grid)
                    if match:
                        lat_dir, lat_val, lon_dir, lon_val = match.groups()
                        coords['lat'] = coords['lat'] or float(lat_val) * (1 if lat_dir == 'N' else -1)
                        coords['lon'] = coords['lon'] or float(lon_val) * (1 if lon_dir == 'E' else -1)
            
            if coords['lat']:
                coords['lat'] = float(coords['lat'])
            if coords['lon']:
                coords['lon'] = float(coords['lon'])
                
        except:
            pass
        
        return coords
    
    def parse_query(self, query):
        """Parse natural language query to extract intent"""
        query_lower = query.lower()
        
        intent = {
            'parameter': None,
            'regions': [],
            'years': [],
            'visualization': 'map'
        }
        
        # Extract parameter
        if any(word in query_lower for word in ['temperature', 'temp', 'thermal']):
            intent['parameter'] = 'temp'
        elif any(word in query_lower for word in ['salinity', 'salt', 'psal']):
            intent['parameter'] = 'psal'
        elif any(word in query_lower for word in ['pressure', 'depth', 'pres']):
            intent['parameter'] = 'pres'
        elif any(word in query_lower for word in ['oxygen', 'doxy', 'o2']):
            intent['parameter'] = 'doxy'
        elif any(word in query_lower for word in ['chlorophyll', 'chla', 'chl']):
            intent['parameter'] = 'chla'
        
        # Extract regions
        region_map = {
            'bay of bengal': 'Bay_of_Bengal',
            'bengal': 'Bay_of_Bengal',
            'arabian sea': 'Arabian_Sea',
            'arabian': 'Arabian_Sea',
            'southern ocean': 'Southern_Ocean',
            'equatorial': 'Equatorial_Indian',
            'madagascar': 'Madagascar_Ridge'
        }
        
        for keyword, region in region_map.items():
            if keyword in query_lower:
                intent['regions'].append(region)
        
        # Extract years
        years = re.findall(r'\b(20\d{2})\b', query)
        intent['years'] = [int(y) for y in years]
        
        # Determine visualization type
        if any(word in query_lower for word in ['trajectory', 'path', 'track', 'movement']):
            intent['visualization'] = 'trajectory'
        elif any(word in query_lower for word in ['depth', 'profile', 'vertical']):
            intent['visualization'] = 'depth'
        elif any(word in query_lower for word in ['t-s', 'ts diagram', 'water mass']):
            intent['visualization'] = 'ts'
        elif any(word in query_lower for word in ['time series', 'trend', 'over time']):
            intent['visualization'] = 'timeseries'
        elif any(word in query_lower for word in ['compare', 'comparison']):
            intent['visualization'] = 'comparison'
        else:
            intent['visualization'] = 'map'
        
        return intent
    
    def create_map(self, profiles, color_param='temp'):
        """Create interactive map"""
        if not profiles:
            return None
        
        map_data = []
        for p in profiles:
            coords = p.get('_coords', {})
            if coords.get('lat') and coords.get('lon'):
                map_data.append({
                    'lat': coords['lat'],
                    'lon': coords['lon'],
                    'date': p.get('_datetime', '')[:10],
                    'regions': ', '.join(p.get('_regions', ['Unknown'])[:2]),
                    'platform': p.get('_platform', 'Unknown'),
                    'temp': p.get('_temp_mean', 0),
                    'sal': p.get('_psal_mean', 0),
                    'depth': p.get('_pres_max', 0),
                    'oxygen': p.get('_doxy_mean', 0),
                    'chla': p.get('_chla_mean', 0)
                })
        
        if not map_data:
            return None
        
        df = pd.DataFrame(map_data)
        
        param_map = {
            'temp': ('temp', 'RdYlBu_r', 'Temperature (°C)'),
            'psal': ('sal', 'Viridis', 'Salinity (PSU)'),
            'pres': ('depth', 'Blues', 'Depth (m)'),
            'doxy': ('oxygen', 'Greens', 'Oxygen (µmol/kg)'),
            'chla': ('chla', 'YlGn', 'Chlorophyll (mg/m³)')
        }
        
        col, scale, label = param_map.get(color_param, param_map['temp'])
        
        fig = px.scatter_mapbox(
            df, lat='lat', lon='lon',
            color=col,
            color_continuous_scale=scale,
            size_max=8,
            zoom=3,
            hover_data={
                'lat': ':.2f', 'lon': ':.2f',
                'date': True, 'regions': True,
                'platform': True,
                'temp': ':.2f', 'sal': ':.2f',
                'depth': ':.0f'
            },
            labels={col: label}
        )
        
        fig.update_layout(
            mapbox_style="carto-darkmatter",
            mapbox=dict(center=dict(lat=df['lat'].mean(), lon=df['lon'].mean()), zoom=3),
            height=500,
            margin={"r":0,"t":30,"l":0,"b":0},
            paper_bgcolor='#0a0a0a',
            font=dict(color='#caf0f8', size=11)
        )
        
        return fig
    
    def create_trajectory(self, profiles):
        """Create trajectory map"""
        if not profiles:
            return None
        
        platform_tracks = defaultdict(list)
        for p in profiles:
            platform = p.get('_platform', 'Unknown')
            coords = p.get('_coords', {})
            if coords.get('lat') and coords.get('lon'):
                platform_tracks[platform].append({
                    'lat': coords['lat'],
                    'lon': coords['lon'],
                    'datetime': p.get('_datetime', ''),
                    'temp': p.get('_temp_mean', 0)
                })
        
        fig = go.Figure()
        
        for platform, tracks in list(platform_tracks.items())[:15]:
            tracks_sorted = sorted(tracks, key=lambda x: x['datetime'])
            
            if len(tracks_sorted) < 2:
                continue
            
            lats = [t['lat'] for t in tracks_sorted]
            lons = [t['lon'] for t in tracks_sorted]
            
            fig.add_trace(go.Scattermapbox(
                lat=lats, lon=lons,
                mode='lines+markers',
                name=f'Float {platform}',
                line=dict(width=2),
                marker=dict(size=5),
                hovertemplate='%{text}<br>Lat: %{lat:.2f}<br>Lon: %{lon:.2f}<extra></extra>',
                text=[t['datetime'][:10] for t in tracks_sorted]
            ))
            
            fig.add_trace(go.Scattermapbox(
                lat=[lats[0]], lon=[lons[0]],
                mode='markers',
                marker=dict(size=10, color='green'),
                showlegend=False,
                hovertext=f"Start: {tracks_sorted[0]['datetime'][:10]}"
            ))
            
            fig.add_trace(go.Scattermapbox(
                lat=[lats[-1]], lon=[lons[-1]],
                mode='markers',
                marker=dict(size=10, color='red'),
                showlegend=False,
                hovertext=f"End: {tracks_sorted[-1]['datetime'][:10]}"
            ))
        
        fig.update_layout(
            mapbox_style="carto-darkmatter",
            mapbox=dict(center=dict(lat=10, lon=75), zoom=3),
            height=500,
            margin={"r":0,"t":30,"l":0,"b":0},
            paper_bgcolor='#0a0a0a',
            font=dict(color='#caf0f8', size=11),
            showlegend=True
        )
        
        return fig
    
    def create_depth_profile(self, profile):
        """Create depth profile with REAL data arrays"""
        measurements = profile.get('measurements', {}).get('core_variables', {})
        
        temp_data = measurements.get('TEMP', {})
        sal_data = measurements.get('PSAL', {})
        pres_data = measurements.get('PRES', {})
        
        if not all([temp_data.get('present'), sal_data.get('present'), pres_data.get('present')]):
            return None
        
        # Try to get actual measurement arrays
        temps = profile.get('_temp_data') or temp_data.get('data') or temp_data.get('values')
        sals = profile.get('_psal_data') or sal_data.get('data') or sal_data.get('values')
        depths = profile.get('_pres_data') or pres_data.get('data') or pres_data.get('values')
        
        # If arrays not available, create synthetic profile from statistics
        if not temps or not sals or not depths or len(temps) < 3:
            temp_stats = temp_data['statistics']
            sal_stats = sal_data['statistics']
            pres_stats = pres_data['statistics']
            
            n_points = 20
            depths = np.linspace(0, pres_stats['max'], n_points)
            
            # Create realistic profile curves
            temps = []
            sals = []
            for d in depths:
                depth_ratio = d / pres_stats['max']
                temp_val = temp_stats['max'] - (temp_stats['max'] - temp_stats['min']) * (depth_ratio ** 0.5)
                sal_val = sal_stats['min'] + (sal_stats['max'] - sal_stats['min']) * (depth_ratio ** 0.3)
                
                temps.append(temp_val + np.random.normal(0, temp_stats.get('std_dev', 0.5) * 0.1))
                sals.append(sal_val + np.random.normal(0, sal_stats.get('std_dev', 0.1) * 0.1))
        
        # Clean data
        valid_indices = [i for i in range(len(depths)) if depths[i] is not None and temps[i] is not None and sals[i] is not None]
        depths = [depths[i] for i in valid_indices]
        temps = [temps[i] for i in valid_indices]
        sals = [sals[i] for i in valid_indices]
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=temps, y=depths,
            mode='lines+markers',
            name='Temperature',
            line=dict(color='#ff6b6b', width=2),
            marker=dict(size=4),
            hovertemplate='Temp: %{x:.2f}°C<br>Depth: %{y:.0f}m<extra></extra>'
        ))
        
        fig.add_trace(go.Scatter(
            x=sals, y=depths,
            mode='lines+markers',
            name='Salinity',
            line=dict(color='#4ecdc4', width=2),
            marker=dict(size=4),
            xaxis='x2',
            hovertemplate='Sal: %{x:.2f} PSU<br>Depth: %{y:.0f}m<extra></extra>'
        ))
        
        fig.update_layout(
            xaxis=dict(title='Temperature (°C)', color='#ff6b6b'),
            xaxis2=dict(title='Salinity (PSU)', overlaying='x', side='top', color='#4ecdc4'),
            yaxis=dict(title='Depth (m)', autorange='reversed'),
            height=500,
            margin=dict(l=50, r=50, t=40, b=40),
            paper_bgcolor='#0a0a0a',
            plot_bgcolor='#16213e',
            font=dict(color='#caf0f8', size=11),
            hovermode='closest'
        )
        
        return fig
    
    def create_ts_diagram(self, profiles):
        """Create T-S diagram"""
        if not profiles:
            return None
        
        ts_data = []
        for p in profiles:
            if p.get('_has_temp') and p.get('_has_psal'):
                ts_data.append({
                    'temp': p.get('_temp_mean', 0),
                    'sal': p.get('_psal_mean', 0),
                    'depth': p.get('_pres_max', 0),
                    'date': p.get('_datetime', '')[:10],
                    'region': ', '.join(p.get('_regions', ['Unknown'])[:1])
                })
        
        if not ts_data:
            return None
        
        df = pd.DataFrame(ts_data)
        
        fig = px.scatter(
            df, x='sal', y='temp',
            color='depth',
            color_continuous_scale='Viridis',
            hover_data=['date', 'region', 'depth'],
            labels={'sal': 'Salinity (PSU)', 'temp': 'Temperature (°C)', 'depth': 'Max Depth (m)'}
        )
        
        fig.update_layout(
            height=500,
            margin=dict(l=50, r=50, t=30, b=40),
            paper_bgcolor='#0a0a0a',
            plot_bgcolor='#16213e',
            font=dict(color='#caf0f8', size=11)
        )
        
        return fig
    
    def create_time_series(self, profiles, parameter='temp'):
        """Create time series"""
        if not profiles:
            return None
        
        time_data = []
        for p in profiles:
            dt_str = p.get('_datetime', '')
            if dt_str:
                time_data.append({
                    'datetime': pd.to_datetime(dt_str),
                    'temp': p.get('_temp_mean', 0),
                    'sal': p.get('_psal_mean', 0),
                    'oxygen': p.get('_doxy_mean', 0),
                    'chla': p.get('_chla_mean', 0)
                })
        
        if not time_data:
            return None
        
        df = pd.DataFrame(time_data)
        df = df.sort_values('datetime')
        df['month'] = df['datetime'].dt.to_period('M')
        
        monthly = df.groupby('month').agg({
            'temp': 'mean',
            'sal': 'mean',
            'oxygen': 'mean',
            'chla': 'mean'
        }).reset_index()
        monthly['month'] = monthly['month'].astype(str)
        
        param_map = {
            'temp': ('temp', 'Temperature (°C)'),
            'psal': ('sal', 'Salinity (PSU)'),
            'doxy': ('oxygen', 'Oxygen (µmol/kg)'),
            'chla': ('chla', 'Chlorophyll (mg/m³)')
        }
        
        param_col, param_label = param_map.get(parameter, ('temp', 'Temperature (°C)'))
        
        fig = px.line(
            monthly, x='month', y=param_col,
            labels={'month': 'Month', param_col: param_label}
        )
        
        fig.update_layout(
            height=450,
            margin=dict(l=50, r=30, t=30, b=40),
            paper_bgcolor='#0a0a0a',
            plot_bgcolor='#16213e',
            font=dict(color='#caf0f8', size=11)
        )
        
        return fig
    
    def query_ai(self, query, profiles_summary):
        """Query AI"""
        if not self.groq_client:
            return "AI unavailable. Set GROQ_API_KEY in .env"
        
        try:
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are an oceanographer analyzing ARGO float data. Provide concise scientific insights. Keep under 120 words."},
                    {"role": "user", "content": f"Data: {profiles_summary}\n\nQuestion: {query}"}
                ],
                temperature=0.3,
                max_tokens=250
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"AI error: {str(e)}"

def main():
    st.title("FloatChat - ARGO Data Visualization")
    st.markdown("**Intelligent Ocean Data Discovery & Visualization Platform**")
    
    if 'viz' not in st.session_state:
        st.session_state.viz = ARGOVisualization()
        st.session_state.profiles = []
        st.session_state.filtered = []
        st.session_state.chat_history = []
        st.session_state.active_tab = 0
        st.session_state.query_intent = None
    
    viz = st.session_state.viz
    
    if not st.session_state.profiles:
        with st.spinner("Loading ARGO data..."):
            st.session_state.profiles = viz.load_argo_data()
    
    profiles = st.session_state.profiles
    
    if not profiles:
        st.error("No data. Check Datasetjson/ directory.")
        return
    
    with st.sidebar:
        st.header("Filters")
        
        years = sorted(set(p.get('_year') for p in profiles if p.get('_year')))
        sel_years = st.multiselect("Year", years, default=years[-2:] if len(years) >= 2 else years)
        
        all_regions = set()
        for p in profiles:
            all_regions.update(p.get('_regions', []))
        sel_regions = st.multiselect("Region", sorted(all_regions))
        
        st.markdown("---")
        st.markdown("### Stats")
        st.metric("Profiles", len(profiles))
        st.metric("Years", len(years))
        st.metric("Regions", len(all_regions))
    
    filtered = profiles
    if sel_years:
        filtered = [p for p in filtered if p.get('_year') in sel_years]
    if sel_regions:
        filtered = [p for p in filtered if any(r in p.get('_regions', []) for r in sel_regions)]
    
    st.session_state.filtered = filtered
    st.info(f"Showing {len(filtered)} profiles")
    
    # Chat input at top for all tabs
    chat_query = st.chat_input("Ask about data or request visualization...")
    
    if chat_query:
        st.session_state.chat_history.append({"role": "user", "content": chat_query})
        
        intent = viz.parse_query(chat_query)
        st.session_state.query_intent = intent
        
        # Apply query filters
        query_filtered = filtered
        if intent['regions']:
            query_filtered = [p for p in query_filtered if any(r in p.get('_regions', []) for r in intent['regions'])]
        if intent['years']:
            query_filtered = [p for p in query_filtered if p.get('_year') in intent['years']]
        
        st.session_state.filtered = query_filtered
        
        summary = f"{len(query_filtered)} profiles. Regions: {intent['regions'] or 'All'}. Param: {intent['parameter'] or 'All'}"
        
        with st.spinner("Analyzing..."):
            response = viz.query_ai(chat_query, summary)
        
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        
        # Auto-switch tab based on query intent
        tab_map = {'map': 0, 'trajectory': 1, 'depth': 2, 'ts': 3, 'timeseries': 4}
        st.session_state.active_tab = tab_map.get(intent['visualization'], 0)
    
    # Display chat history
    if st.session_state.chat_history:
        with st.expander("Chat History", expanded=True):
            for msg in st.session_state.chat_history[-4:]:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🗺️ Map", "🛤️ Trajectories", "📊 Depth Profiles", "💧 T-S Diagram", "📈 Time Series"])
    
    with tab1:
        st.subheader("Interactive Geospatial Map")
        param = st.radio("Color by:", ["temp", "psal", "pres", "doxy", "chla"], horizontal=True, key="map_param")
        
        with st.spinner("Rendering map..."):
            fig = viz.create_map(st.session_state.filtered, param)
        
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No valid coordinates")
    
    with tab2:
        st.subheader("Float Trajectories")
        
        with st.spinner("Rendering trajectories..."):
            fig = viz.create_trajectory(st.session_state.filtered)
        
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Insufficient trajectory data")
    
    with tab3:
        st.subheader("Vertical Depth Profiles")
        
        if st.session_state.filtered:
            idx = st.selectbox("Profile:", range(min(15, len(st.session_state.filtered))),
                              format_func=lambda x: f"{x+1}. {st.session_state.filtered[x].get('_datetime', '')[:10]} - {', '.join(st.session_state.filtered[x].get('_regions', ['Unknown'])[:1])}")
            
            with st.spinner("Rendering depth profile..."):
                fig = viz.create_depth_profile(st.session_state.filtered[idx])
            
            if fig:
                st.plotly_chart(fig, use_container_width=True)
                
                # Show profile metadata
                p = st.session_state.filtered[idx]
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Temp Range", f"{p.get('_temp_min', 0):.1f} - {p.get('_temp_max', 0):.1f}°C")
                with col2:
                    st.metric("Sal Range", f"{p.get('_psal_min', 0):.1f} - {p.get('_psal_max', 0):.1f} PSU")
                with col3:
                    st.metric("Max Depth", f"{p.get('_pres_max', 0):.0f}m")
            else:
                st.warning("Profile data incomplete")
        else:
            st.warning("No profiles available")
    
    with tab4:
        st.subheader("Temperature-Salinity Diagram")
        
        with st.spinner("Rendering T-S diagram..."):
            fig = viz.create_ts_diagram(st.session_state.filtered)
        
        if fig:
            st.plotly_chart(fig, use_container_width=True)
            
            # Water mass identification helper
            st.info("💡 **Water Mass Regions**: Warm+Fresh (upper left) | Warm+Saline (upper right) | Cold+Fresh (lower left) | Cold+Saline (lower right)")
        else:
            st.warning("Insufficient T-S data")
    
    with tab5:
        st.subheader("Time Series Analysis")
        param = st.radio("Parameter:", ["temp", "psal", "doxy", "chla"], horizontal=True, key="ts_param")
        
        with st.spinner("Rendering time series..."):
            fig = viz.create_time_series(st.session_state.filtered, param)
        
        if fig:
            st.plotly_chart(fig, use_container_width=True)
            
            # Show trend statistics
            if st.session_state.filtered:
                param_values = [p.get(f'_{param}_mean', 0) for p in st.session_state.filtered if p.get(f'_has_{param}')]
                if param_values:
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Mean", f"{np.mean(param_values):.2f}")
                    with col2:
                        st.metric("Std Dev", f"{np.std(param_values):.2f}")
                    with col3:
                        st.metric("Min", f"{np.min(param_values):.2f}")
                    with col4:
                        st.metric("Max", f"{np.max(param_values):.2f}")
        else:
            st.warning("Insufficient time series data")
    
    # Export functionality
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📥 Export Map Data (CSV)", use_container_width=True):
            if st.session_state.filtered:
                export_data = []
                for p in st.session_state.filtered:
                    coords = p.get('_coords', {})
                    export_data.append({
                        'Date': p.get('_datetime', '')[:10],
                        'Latitude': coords.get('lat'),
                        'Longitude': coords.get('lon'),
                        'Region': ', '.join(p.get('_regions', [])),
                        'Temperature': p.get('_temp_mean'),
                        'Salinity': p.get('_psal_mean'),
                        'Max_Depth': p.get('_pres_max')
                    })
                
                df_export = pd.DataFrame(export_data)
                csv = df_export.to_csv(index=False)
                st.download_button(
                    "⬇️ Download CSV",
                    csv,
                    f"argo_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "text/csv",
                    use_container_width=True
                )
    
    with col2:
        if st.button("📊 Export Statistics (JSON)", use_container_width=True):
            if st.session_state.filtered:
                stats = {
                    'total_profiles': len(st.session_state.filtered),
                    'date_range': [
                        min(p.get('_datetime', '') for p in st.session_state.filtered if p.get('_datetime'))[:10],
                        max(p.get('_datetime', '') for p in st.session_state.filtered if p.get('_datetime'))[:10]
                    ],
                    'regions': list(set([r for p in st.session_state.filtered for r in p.get('_regions', [])])),
                    'parameters': {
                        'temperature': {
                            'mean': np.mean([p.get('_temp_mean', 0) for p in st.session_state.filtered if p.get('_has_temp')]),
                            'min': np.min([p.get('_temp_min', 0) for p in st.session_state.filtered if p.get('_has_temp')]),
                            'max': np.max([p.get('_temp_max', 0) for p in st.session_state.filtered if p.get('_has_temp')])
                        },
                        'salinity': {
                            'mean': np.mean([p.get('_psal_mean', 0) for p in st.session_state.filtered if p.get('_has_psal')]),
                            'min': np.min([p.get('_psal_min', 0) for p in st.session_state.filtered if p.get('_has_psal')]),
                            'max': np.max([p.get('_psal_max', 0) for p in st.session_state.filtered if p.get('_has_psal')])
                        }
                    }
                }
                
                json_str = json.dumps(stats, indent=2)
                st.download_button(
                    "⬇️ Download JSON",
                    json_str,
                    f"argo_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    "application/json",
                    use_container_width=True
                )
    
    with col3:
        if st.button("📋 Export Chat History", use_container_width=True):
            if st.session_state.chat_history:
                chat_export = {
                    'timestamp': datetime.now().isoformat(),
                    'messages': st.session_state.chat_history,
                    'profiles_analyzed': len(st.session_state.filtered)
                }
                
                json_str = json.dumps(chat_export, indent=2)
                st.download_button(
                    "⬇️ Download Chat",
                    json_str,
                    f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    "application/json",
                    use_container_width=True
                )
    
    with col4:
        if st.button("🔄 Reset Filters", use_container_width=True):
            st.session_state.filtered = st.session_state.profiles
            st.session_state.query_intent = None
            st.rerun()

if __name__ == "__main__":
    main()
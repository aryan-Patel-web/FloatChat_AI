"""
Advanced Geospatial Visualization System for FloatChat
- ARGO float trajectory analysis
- Depth-time profiling
- 3D oceanographic mapping
- BGC parameter visualization
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
from pathlib import Path
from datetime import datetime, timedelta
import netCDF4 as nc
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedGeospatialVisualizer:
    def __init__(self):
        self.data_dir = Path("data")
        self.processed_data = None
        self.float_trajectories = {}
        self.bgc_parameters = {}
        
    def load_processed_data(self):
        """Load processed oceanographic data"""
        try:
            if Path("processed_oceanographic_data.json").exists():
                with open("processed_oceanographic_data.json", 'r') as f:
                    self.processed_data = json.load(f)
                return True
        except Exception as e:
            logger.error(f"Failed to load processed data: {e}")
        return False
    
    def extract_trajectory_data(self):
        """Extract trajectory data from ARGO files for mapping"""
        trajectories = {}
        
        try:
            argo_files = list(self.data_dir.glob("argo/*.nc"))
            
            for nc_file in argo_files:
                try:
                    with nc.Dataset(nc_file, 'r') as ds:
                        # Extract float ID
                        float_id = str(ds.variables.get('PLATFORM_NUMBER', ['unknown'])[0])
                        
                        # Extract coordinates
                        if 'LATITUDE' in ds.variables and 'LONGITUDE' in ds.variables:
                            lats = ds.variables['LATITUDE'][:]
                            lons = ds.variables['LONGITUDE'][:]
                            
                            # Extract time if available
                            times = []
                            if 'JULD' in ds.variables:
                                juld = ds.variables['JULD'][:]
                                # Convert ARGO Julian day to datetime
                                for j in juld:
                                    if not np.ma.is_masked(j):
                                        times.append(datetime(1950, 1, 1) + timedelta(days=float(j)))
                            
                            # Extract depth profiles
                            depths = []
                            temps = []
                            sals = []
                            
                            if 'PRES' in ds.variables:
                                depths = ds.variables['PRES'][:]
                            if 'TEMP' in ds.variables:
                                temps = ds.variables['TEMP'][:]
                            if 'PSAL' in ds.variables:
                                sals = ds.variables['PSAL'][:]
                            
                            trajectories[float_id] = {
                                'latitudes': np.ma.filled(lats, np.nan),
                                'longitudes': np.ma.filled(lons, np.nan),
                                'times': times,
                                'depths': np.ma.filled(depths, np.nan),
                                'temperatures': np.ma.filled(temps, np.nan),
                                'salinities': np.ma.filled(sals, np.nan),
                                'file_path': str(nc_file)
                            }
                            
                except Exception as e:
                    logger.warning(f"Failed to process {nc_file}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Trajectory extraction failed: {e}")
        
        self.float_trajectories = trajectories
        return trajectories
    
    def create_float_trajectory_map(self):
        """Create interactive trajectory map"""
        if not self.float_trajectories:
            self.extract_trajectory_data()
        
        fig = go.Figure()
        
        colors = px.colors.qualitative.Set1
        
        for i, (float_id, data) in enumerate(self.float_trajectories.items()):
            lats = data['latitudes']
            lons = data['longitudes']
            
            # Filter valid coordinates
            valid_mask = ~(np.isnan(lats) | np.isnan(lons))
            if np.any(valid_mask):
                valid_lats = lats[valid_mask]
                valid_lons = lons[valid_mask]
                
                color = colors[i % len(colors)]
                
                # Add trajectory line
                fig.add_trace(go.Scattermapbox(
                    mode="markers+lines",
                    lon=valid_lons,
                    lat=valid_lats,
                    marker={'size': 8, 'color': color},
                    line={'width': 2, 'color': color},
                    name=f"Float {float_id}",
                    hovertemplate=f"<b>Float {float_id}</b><br>" +
                                  "Lat: %{lat:.3f}<br>" +
                                  "Lon: %{lon:.3f}<br>" +
                                  "<extra></extra>"
                ))
                
                # Add start/end markers
                if len(valid_lats) > 1:
                    # Start point
                    fig.add_trace(go.Scattermapbox(
                        mode="markers",
                        lon=[valid_lons[0]],
                        lat=[valid_lats[0]],
                        marker={'size': 12, 'color': 'green', 'symbol': 'circle'},
                        name=f"Start {float_id}",
                        showlegend=False,
                        hovertemplate=f"<b>Start - Float {float_id}</b><br>" +
                                      "Lat: %{lat:.3f}<br>" +
                                      "Lon: %{lon:.3f}<br>" +
                                      "<extra></extra>"
                    ))
                    
                    # End point
                    fig.add_trace(go.Scattermapbox(
                        mode="markers",
                        lon=[valid_lons[-1]],
                        lat=[valid_lats[-1]],
                        marker={'size': 12, 'color': 'red', 'symbol': 'square'},
                        name=f"End {float_id}",
                        showlegend=False,
                        hovertemplate=f"<b>End - Float {float_id}</b><br>" +
                                      "Lat: %{lat:.3f}<br>" +
                                      "Lon: %{lon:.3f}<br>" +
                                      "<extra></extra>"
                    ))
        
        # Update layout for Indian Ocean focus
        fig.update_layout(
            mapbox_style="open-street-map",
            mapbox=dict(
                center=go.layout.mapbox.Center(lat=10, lon=80),  # Indian Ocean center
                zoom=4
            ),
            height=600,
            title="ARGO Float Trajectories in Indian Ocean",
            showlegend=True
        )
        
        return fig
    
    def create_depth_time_profile(self, float_id=None):
        """Create depth-time profile visualization"""
        if not self.float_trajectories:
            self.extract_trajectory_data()
        
        if not float_id and self.float_trajectories:
            float_id = list(self.float_trajectories.keys())[0]
        
        if float_id not in self.float_trajectories:
            return None
        
        data = self.float_trajectories[float_id]
        depths = data['depths']
        temps = data['temperatures']
        times = data['times'] if data['times'] else range(len(depths))
        
        # Create subplots for temperature and salinity profiles
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=(f'Temperature Profile - Float {float_id}', 
                          f'Salinity Profile - Float {float_id}'),
            vertical_spacing=0.1
        )
        
        # Temperature vs Depth
        if len(temps) > 0 and len(depths) > 0:
            valid_mask = ~(np.isnan(temps) | np.isnan(depths))
            if np.any(valid_mask):
                fig.add_trace(
                    go.Scatter(
                        x=temps[valid_mask],
                        y=-depths[valid_mask],  # Negative for depth below surface
                        mode='lines+markers',
                        name='Temperature',
                        line=dict(color='red'),
                        hovertemplate='Temperature: %{x:.2f}°C<br>Depth: %{y:.0f}m<extra></extra>'
                    ),
                    row=1, col=1
                )
        
        # Salinity vs Depth
        sals = data['salinities']
        if len(sals) > 0 and len(depths) > 0:
            valid_mask = ~(np.isnan(sals) | np.isnan(depths))
            if np.any(valid_mask):
                fig.add_trace(
                    go.Scatter(
                        x=sals[valid_mask],
                        y=-depths[valid_mask],
                        mode='lines+markers',
                        name='Salinity',
                        line=dict(color='blue'),
                        hovertemplate='Salinity: %{x:.2f} PSU<br>Depth: %{y:.0f}m<extra></extra>'
                    ),
                    row=2, col=1
                )
        
        fig.update_xaxes(title_text="Temperature (°C)", row=1, col=1)
        fig.update_xaxes(title_text="Salinity (PSU)", row=2, col=1)
        fig.update_yaxes(title_text="Depth (m)", row=1, col=1)
        fig.update_yaxes(title_text="Depth (m)", row=2, col=1)
        
        fig.update_layout(height=800, title_text=f"Depth Profiles for ARGO Float {float_id}")
        
        return fig
    
    def create_3d_ocean_visualization(self):
        """Create 3D visualization of oceanographic data"""
        if not self.float_trajectories:
            self.extract_trajectory_data()
        
        fig = go.Figure()
        
        colors = px.colors.qualitative.Set1
        
        for i, (float_id, data) in enumerate(self.float_trajectories.items()):
            lats = data['latitudes']
            lons = data['longitudes']
            depths = data['depths']
            temps = data['temperatures']
            
            # Filter valid data
            valid_mask = ~(np.isnan(lats) | np.isnan(lons) | np.isnan(depths) | np.isnan(temps))
            if np.any(valid_mask):
                color = colors[i % len(colors)]
                
                fig.add_trace(go.Scatter3d(
                    x=lons[valid_mask],
                    y=lats[valid_mask],
                    z=-depths[valid_mask],  # Negative depth
                    mode='markers',
                    marker=dict(
                        size=5,
                        color=temps[valid_mask],
                        colorscale='Viridis',
                        colorbar=dict(title="Temperature (°C)"),
                        showscale=True
                    ),
                    name=f"Float {float_id}",
                    hovertemplate='<b>Float ' + float_id + '</b><br>' +
                                  'Lon: %{x:.3f}<br>' +
                                  'Lat: %{y:.3f}<br>' +
                                  'Depth: %{z:.0f}m<br>' +
                                  'Temp: %{marker.color:.2f}°C<br>' +
                                  '<extra></extra>'
                ))
        
        fig.update_layout(
            scene=dict(
                xaxis_title='Longitude',
                yaxis_title='Latitude',
                zaxis_title='Depth (m)',
                camera=dict(eye=dict(x=1.5, y=1.5, z=1.5))
            ),
            height=700,
            title="3D Oceanographic Data Visualization"
        )
        
        return fig
    
    def extract_bgc_parameters(self):
        """Extract BGC (Biogeochemical) parameters from ARGO files"""
        bgc_data = {}
        
        try:
            argo_files = list(self.data_dir.glob("argo/*.nc"))
            
            for nc_file in argo_files:
                try:
                    with nc.Dataset(nc_file, 'r') as ds:
                        float_id = str(ds.variables.get('PLATFORM_NUMBER', ['unknown'])[0])
                        
                        # Common BGC parameters
                        bgc_params = {
                            'CHLA': 'Chlorophyll-a',
                            'BBP700': 'Backscattering at 700nm',
                            'CDOM': 'Colored Dissolved Organic Matter',
                            'NITRATE': 'Nitrate',
                            'PH_IN_SITU_TOTAL': 'pH',
                            'DOXY': 'Dissolved Oxygen'
                        }
                        
                        float_bgc = {}
                        
                        for param, description in bgc_params.items():
                            if param in ds.variables:
                                values = ds.variables[param][:]
                                if not np.ma.is_masked(values) or np.ma.count(values) > 0:
                                    float_bgc[param] = {
                                        'values': np.ma.filled(values, np.nan),
                                        'description': description,
                                        'units': getattr(ds.variables[param], 'units', 'unknown')
                                    }
                        
                        if float_bgc:
                            bgc_data[float_id] = float_bgc
                            
                except Exception as e:
                    logger.warning(f"BGC extraction failed for {nc_file}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"BGC parameter extraction failed: {e}")
        
        self.bgc_parameters = bgc_data
        return bgc_data
    
    def create_bgc_analysis_plots(self):
        """Create BGC parameter analysis visualizations"""
        if not self.bgc_parameters:
            self.extract_bgc_parameters()
        
        if not self.bgc_parameters:
            return None
        
        # Create subplots for different BGC parameters
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Chlorophyll-a Distribution', 'pH Levels', 
                          'Dissolved Oxygen', 'Nitrate Levels'),
            vertical_spacing=0.1
        )
        
        all_chla = []
        all_ph = []
        all_doxy = []
        all_nitrate = []
        
        for float_id, bgc_data in self.bgc_parameters.items():
            if 'CHLA' in bgc_data:
                values = bgc_data['CHLA']['values']
                valid_values = values[~np.isnan(values)]
                all_chla.extend(valid_values)
            
            if 'PH_IN_SITU_TOTAL' in bgc_data:
                values = bgc_data['PH_IN_SITU_TOTAL']['values']
                valid_values = values[~np.isnan(values)]
                all_ph.extend(valid_values)
            
            if 'DOXY' in bgc_data:
                values = bgc_data['DOXY']['values']
                valid_values = values[~np.isnan(values)]
                all_doxy.extend(valid_values)
            
            if 'NITRATE' in bgc_data:
                values = bgc_data['NITRATE']['values']
                valid_values = values[~np.isnan(values)]
                all_nitrate.extend(valid_values)
        
        # Plot histograms
        if all_chla:
            fig.add_trace(go.Histogram(x=all_chla, name='Chlorophyll-a'), row=1, col=1)
        if all_ph:
            fig.add_trace(go.Histogram(x=all_ph, name='pH'), row=1, col=2)
        if all_doxy:
            fig.add_trace(go.Histogram(x=all_doxy, name='Dissolved Oxygen'), row=2, col=1)
        if all_nitrate:
            fig.add_trace(go.Histogram(x=all_nitrate, name='Nitrate'), row=2, col=2)
        
        fig.update_layout(height=600, title_text="BGC Parameter Distributions")
        fig.update_layout(showlegend=False)
        
        return fig
    
    def create_regional_comparison_map(self):
        """Create regional comparison visualization"""
        if not self.processed_data:
            self.load_processed_data()
        
        # Extract numeric data
        numeric_data = self.processed_data.get('numeric_data', {})
        coordinates = numeric_data.get('coordinates', [])
        temperatures = numeric_data.get('temperature', [])
        salinities = numeric_data.get('salinity', [])
        
        if not coordinates or len(coordinates) != len(temperatures):
            return None
        
        # Create DataFrame for regional analysis
        df_data = []
        for i, coord in enumerate(coordinates):
            if i < len(temperatures) and i < len(salinities):
                lat, lon = coord
                
                # Determine region
                region = "Unknown"
                if lat >= 5 and lat <= 15 and lon >= 80 and lon <= 100:
                    region = "Bay of Bengal"
                elif lat >= 10 and lat <= 25 and lon >= 60 and lon <= 80:
                    region = "Arabian Sea"
                elif lat >= -10 and lat <= 5 and lon >= 70 and lon <= 90:
                    region = "Southern Indian Ocean"
                
                df_data.append({
                    'latitude': lat,
                    'longitude': lon,
                    'temperature': temperatures[i],
                    'salinity': salinities[i],
                    'region': region
                })
        
        if not df_data:
            return None
        
        df = pd.DataFrame(df_data)
        
        # Create regional comparison map
        fig = px.scatter_mapbox(
            df, 
            lat='latitude', 
            lon='longitude',
            color='temperature',
            size='salinity',
            hover_data={'region': True, 'temperature': ':.2f', 'salinity': ':.2f'},
            color_continuous_scale='Viridis',
            title="Regional Oceanographic Parameters",
            mapbox_style="open-street-map",
            height=600,
            zoom=4,
            center=dict(lat=10, lon=80)
        )
        
        return fig

def test_advanced_geospatial():
    """Test the advanced geospatial visualizer"""
    print("Testing Advanced Geospatial Visualizer...")
    
    viz = AdvancedGeospatialVisualizer()
    
    # Test data loading
    if viz.load_processed_data():
        print("✓ Processed data loaded successfully")
    
    # Test trajectory extraction
    trajectories = viz.extract_trajectory_data()
    print(f"✓ Extracted {len(trajectories)} float trajectories")
    
    # Test BGC extraction
    bgc_data = viz.extract_bgc_parameters()
    print(f"✓ Extracted BGC data from {len(bgc_data)} floats")
    
    print("Advanced Geospatial Visualizer test completed!")
    return viz

if __name__ == "__main__":
    test_advanced_geospatial()
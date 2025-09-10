"""
Diagnostic FloatChat Dashboard - Identifies and Fixes Data Loading Issues
Shows exactly what's in your JSON files and extracts data properly
"""

import streamlit as st
import sys
import json
import os
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import logging
import traceback

# FIRST: Configure Streamlit page
st.set_page_config(
    page_title="FloatChat AI - Diagnostic Mode",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BASE_PATH = Path("D:/FloatChat ARGO/MINIO")
if BASE_PATH.exists():
    os.chdir(BASE_PATH)
    sys.path.insert(0, str(BASE_PATH))

# CSS
st.markdown("""
<style>
    .main { 
        padding-top: 1rem; 
        font-family: 'Inter', sans-serif;
    }
    .diagnostic-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        margin-bottom: 2rem;
    }
    .data-preview {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        font-family: 'Courier New', monospace;
        font-size: 12px;
        max-height: 300px;
        overflow-y: auto;
    }
    .success-box {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 12px;
        border-radius: 6px;
        margin: 10px 0;
    }
    .error-box {
        background: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 12px;
        border-radius: 6px;
        margin: 10px 0;
    }
    .warning-box {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 12px;
        border-radius: 6px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

class DiagnosticDataAnalyzer:
    """Diagnostic analyzer to understand your data structure"""
    
    def __init__(self):
        self.data_files = [
            "processed_oceanographic_data.json",
            "argo_extracted_data.json", 
            "incois_comprehensive_data.json",
            "bgc_analysis_results.json"
        ]
        self.analysis_results = {}
        self.extracted_data = {
            'temperature': [],
            'salinity': [], 
            'coordinates': [],
            'float_ids': [],
            'all_keys': set(),
            'file_structures': {}
        }
    
    def analyze_all_files(self):
        """Analyze all data files to understand their structure"""
        st.header("🔍 Data File Diagnostic Analysis")
        
        for file_name in self.data_files:
            file_path = BASE_PATH / file_name
            
            st.subheader(f"📁 Analyzing: {file_name}")
            
            if not file_path.exists():
                st.markdown(f'<div class="error-box">❌ File not found: {file_name}</div>', unsafe_allow_html=True)
                continue
            
            try:
                # File info
                file_size = file_path.stat().st_size
                st.write(f"**File Size:** {file_size:,} bytes ({file_size/1024:.1f} KB)")
                
                # Load and analyze
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Show file structure
                self.show_file_structure(file_name, data)
                
                # Extract data
                extracted = self.extract_data_from_file(file_name, data)
                st.write(f"**Extracted Data:** {extracted}")
                
                # Store results
                self.analysis_results[file_name] = {
                    'size': file_size,
                    'structure': self.get_structure_summary(data),
                    'extracted': extracted
                }
                
            except Exception as e:
                st.markdown(f'<div class="error-box">❌ Error reading {file_name}: {str(e)}</div>', unsafe_allow_html=True)
        
        # Summary
        self.show_extraction_summary()
    
    def show_file_structure(self, file_name, data):
        """Show the structure of a JSON file"""
        
        with st.expander(f"🔍 View {file_name} Structure", expanded=False):
            
            # Show top-level keys
            if isinstance(data, dict):
                st.write("**Top-level keys:**")
                for key in data.keys():
                    st.write(f"- `{key}`: {type(data[key]).__name__}")
                    
                    # Show nested structure for important keys
                    if key in ['numeric_data', 'data', 'profiles', 'measurements']:
                        if isinstance(data[key], dict):
                            st.write(f"  **{key} contains:**")
                            for subkey in list(data[key].keys())[:10]:  # Limit to first 10
                                subdata = data[key][subkey]
                                if isinstance(subdata, list):
                                    st.write(f"    - `{subkey}`: list with {len(subdata)} items")
                                else:
                                    st.write(f"    - `{subkey}`: {type(subdata).__name__}")
            
            # Show sample data
            st.write("**Sample data preview:**")
            sample = self.get_sample_data(data)
            st.markdown(f'<div class="data-preview">{sample}</div>', unsafe_allow_html=True)
    
    def get_sample_data(self, data, max_lines=15):
        """Get a sample of the data for preview"""
        try:
            if isinstance(data, dict):
                sample_dict = {}
                for i, (key, value) in enumerate(data.items()):
                    if i >= 5:  # Limit to first 5 keys
                        break
                    if isinstance(value, list) and len(value) > 0:
                        sample_dict[key] = value[:3] + ['...'] if len(value) > 3 else value
                    elif isinstance(value, dict):
                        sample_dict[key] = {k: v for i, (k, v) in enumerate(value.items()) if i < 3}
                    else:
                        sample_dict[key] = value
                return json.dumps(sample_dict, indent=2)
            else:
                return str(data)[:1000] + "..." if len(str(data)) > 1000 else str(data)
        except:
            return "Unable to preview data"
    
    def extract_data_from_file(self, file_name, data):
        """Extract oceanographic data from various file formats"""
        extracted = {'temp': 0, 'sal': 0, 'coords': 0, 'floats': 0}
        
        try:
            # Strategy 1: Look for 'numeric_data' structure
            if 'numeric_data' in data:
                numeric = data['numeric_data']
                if isinstance(numeric, dict):
                    # Extract temperature
                    if 'temperature' in numeric:
                        temp_data = numeric['temperature']
                        if isinstance(temp_data, list):
                            valid_temps = [t for t in temp_data if self.is_valid_number(t)]
                            self.extracted_data['temperature'].extend(valid_temps)
                            extracted['temp'] = len(valid_temps)
                    
                    # Extract salinity
                    if 'salinity' in numeric:
                        sal_data = numeric['salinity']
                        if isinstance(sal_data, list):
                            valid_sals = [s for s in sal_data if self.is_valid_number(s)]
                            self.extracted_data['salinity'].extend(valid_sals)
                            extracted['sal'] = len(valid_sals)
                    
                    # Extract coordinates
                    if 'coordinates' in numeric:
                        coord_data = numeric['coordinates']
                        if isinstance(coord_data, list):
                            valid_coords = [c for c in coord_data if isinstance(c, list) and len(c) >= 2]
                            self.extracted_data['coordinates'].extend(valid_coords)
                            extracted['coords'] = len(valid_coords)
            
            # Strategy 2: Look for direct data arrays
            self.try_direct_extraction(data, extracted)
            
            # Strategy 3: Look for nested profile data
            self.try_profile_extraction(data, extracted)
            
            # Strategy 4: Look for measurements
            self.try_measurement_extraction(data, extracted)
            
        except Exception as e:
            st.write(f"Extraction error: {e}")
        
        return extracted
    
    def try_direct_extraction(self, data, extracted):
        """Try extracting data directly from top-level keys"""
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0:
                    if 'temp' in key.lower():
                        valid_data = [v for v in value if self.is_valid_number(v)]
                        if valid_data:
                            self.extracted_data['temperature'].extend(valid_data)
                            extracted['temp'] += len(valid_data)
                    
                    elif 'sal' in key.lower():
                        valid_data = [v for v in value if self.is_valid_number(v)]
                        if valid_data:
                            self.extracted_data['salinity'].extend(valid_data)
                            extracted['sal'] += len(valid_data)
                    
                    elif 'coord' in key.lower() or 'lat' in key.lower():
                        if all(isinstance(item, list) for item in value[:5]):
                            self.extracted_data['coordinates'].extend(value)
                            extracted['coords'] += len(value)
    
    def try_profile_extraction(self, data, extracted):
        """Try extracting from profile-based structure"""
        if isinstance(data, dict):
            for key, value in data.items():
                if 'profile' in key.lower() and isinstance(value, (list, dict)):
                    # Handle profiles
                    if isinstance(value, list):
                        for profile in value[:10]:  # Limit for performance
                            if isinstance(profile, dict):
                                self.extract_from_profile(profile, extracted)
    
    def try_measurement_extraction(self, data, extracted):
        """Try extracting from measurement-based structure"""
        if isinstance(data, dict):
            # Look for measurement arrays
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0:
                    # Check if items look like measurements
                    sample_item = value[0] if value else None
                    if isinstance(sample_item, dict):
                        # Try to extract from measurement objects
                        for item in value[:100]:  # Limit for performance
                            if isinstance(item, dict):
                                for subkey, subvalue in item.items():
                                    if 'temp' in subkey.lower() and self.is_valid_number(subvalue):
                                        self.extracted_data['temperature'].append(subvalue)
                                        extracted['temp'] += 1
                                    elif 'sal' in subkey.lower() and self.is_valid_number(subvalue):
                                        self.extracted_data['salinity'].append(subvalue)
                                        extracted['sal'] += 1
    
    def extract_from_profile(self, profile, extracted):
        """Extract data from a profile object"""
        if isinstance(profile, dict):
            for key, value in profile.items():
                if 'temp' in key.lower() and isinstance(value, list):
                    valid_temps = [t for t in value if self.is_valid_number(t)]
                    self.extracted_data['temperature'].extend(valid_temps)
                    extracted['temp'] += len(valid_temps)
                elif 'sal' in key.lower() and isinstance(value, list):
                    valid_sals = [s for s in value if self.is_valid_number(s)]
                    self.extracted_data['salinity'].extend(valid_sals)
                    extracted['sal'] += len(valid_sals)
    
    def is_valid_number(self, value):
        """Check if a value is a valid number"""
        try:
            if value is None or value == '':
                return False
            float_val = float(value)
            return not (np.isnan(float_val) or np.isinf(float_val))
        except (ValueError, TypeError):
            return False
    
    def get_structure_summary(self, data):
        """Get a summary of the data structure"""
        if isinstance(data, dict):
            return f"Dict with {len(data)} keys: {list(data.keys())[:5]}"
        elif isinstance(data, list):
            return f"List with {len(data)} items"
        else:
            return f"{type(data).__name__}: {str(data)[:50]}"
    
    def show_extraction_summary(self):
        """Show summary of all extracted data"""
        st.header("📊 Data Extraction Summary")
        
        # Total extracted data
        total_temp = len(self.extracted_data['temperature'])
        total_sal = len(self.extracted_data['salinity'])
        total_coords = len(self.extracted_data['coordinates'])
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if total_temp > 0:
                st.markdown(f'<div class="success-box">✅ Temperature: {total_temp:,} values</div>', unsafe_allow_html=True)
                # Show statistics
                temps = self.extracted_data['temperature']
                st.write(f"Range: {min(temps):.2f} to {max(temps):.2f}")
                st.write(f"Mean: {np.mean(temps):.2f}")
            else:
                st.markdown('<div class="error-box">❌ No temperature data found</div>', unsafe_allow_html=True)
        
        with col2:
            if total_sal > 0:
                st.markdown(f'<div class="success-box">✅ Salinity: {total_sal:,} values</div>', unsafe_allow_html=True)
                sals = self.extracted_data['salinity']
                st.write(f"Range: {min(sals):.2f} to {max(sals):.2f}")
                st.write(f"Mean: {np.mean(sals):.2f}")
            else:
                st.markdown('<div class="error-box">❌ No salinity data found</div>', unsafe_allow_html=True)
        
        with col3:
            if total_coords > 0:
                st.markdown(f'<div class="success-box">✅ Coordinates: {total_coords:,} points</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="error-box">❌ No coordinate data found</div>', unsafe_allow_html=True)
        
        # Show file-by-file results
        st.subheader("📋 Results by File")
        for file_name, results in self.analysis_results.items():
            extracted = results['extracted']
            status = "✅" if any(extracted.values()) else "❌"
            st.write(f"{status} **{file_name}**: {extracted['temp']} temp, {extracted['sal']} sal, {extracted['coords']} coords")
    
    def create_diagnostic_visualization(self):
        """Create visualizations from extracted data"""
        st.header("📈 Data Visualization")
        
        if self.extracted_data['temperature']:
            st.subheader("🌡️ Temperature Data")
            
            temps = self.extracted_data['temperature']
            
            # Histogram
            fig_hist = px.histogram(
                x=temps, 
                nbins=30,
                title="Temperature Distribution",
                labels={'x': 'Temperature (°C)', 'y': 'Frequency'}
            )
            st.plotly_chart(fig_hist, use_container_width=True)
            
            # Time series (if we can create one)
            if len(temps) > 1:
                fig_ts = px.line(
                    x=range(len(temps[:100])), 
                    y=temps[:100],
                    title="Temperature Profile (First 100 values)",
                    labels={'x': 'Profile Index', 'y': 'Temperature (°C)'}
                )
                st.plotly_chart(fig_ts, use_container_width=True)
        
        if self.extracted_data['coordinates']:
            st.subheader("🗺️ Geographic Distribution")
            
            coords = self.extracted_data['coordinates'][:100]  # Limit for performance
            valid_coords = []
            
            for coord in coords:
                if isinstance(coord, list) and len(coord) >= 2:
                    try:
                        lat, lon = float(coord[0]), float(coord[1])
                        if -90 <= lat <= 90 and -180 <= lon <= 180:
                            valid_coords.append([lat, lon])
                    except:
                        continue
            
            if valid_coords:
                df_coords = pd.DataFrame(valid_coords, columns=['lat', 'lon'])
                
                fig_map = px.scatter_mapbox(
                    df_coords, 
                    lat='lat', 
                    lon='lon',
                    mapbox_style="open-street-map",
                    title="ARGO Float Locations",
                    height=600,
                    zoom=3
                )
                st.plotly_chart(fig_map, use_container_width=True)
            else:
                st.warning("No valid coordinates found for mapping")

def render_diagnostic_header():
    """Render diagnostic header"""
    st.markdown("""
    <div class="diagnostic-container">
        <h1 style="margin: 0; font-size: 2.5rem;">🔍 FloatChat AI - Diagnostic Mode</h1>
        <p style="margin: 1rem 0;">Analyzing your ARGO data files to identify and fix loading issues</p>
        <p style="margin: 0.5rem 0; opacity: 0.9;">This will show exactly what's in your JSON files and extract data properly</p>
    </div>
    """, unsafe_allow_html=True)

def main():
    """Main diagnostic function"""
    render_diagnostic_header()
    
    # Initialize analyzer
    analyzer = DiagnosticDataAnalyzer()
    
    # Run analysis
    with st.spinner("Analyzing your data files..."):
        analyzer.analyze_all_files()
    
    # Create visualizations if data found
    if analyzer.extracted_data['temperature'] or analyzer.extracted_data['coordinates']:
        analyzer.create_diagnostic_visualization()
    
    # Recommendations
    st.header("💡 Recommendations")
    
    total_data = (
        len(analyzer.extracted_data['temperature']) + 
        len(analyzer.extracted_data['salinity']) + 
        len(analyzer.extracted_data['coordinates'])
    )
    
    if total_data == 0:
        st.markdown("""
        <div class="error-box">
        <h4>❌ No ARGO data found in any files</h4>
        <p><strong>Possible issues:</strong></p>
        <ul>
            <li>JSON files may be empty or contain only metadata</li>
            <li>Data might be in a different format than expected</li>
            <li>Numeric data might be stored under different key names</li>
        </ul>
        <p><strong>Next steps:</strong></p>
        <ol>
            <li>Check if your NetCDF files need to be processed first</li>
            <li>Verify the JSON files contain actual measurements</li>
            <li>Look at the structure analysis above to understand your data format</li>
        </ol>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="success-box">
        <h4>✅ Found {total_data:,} data points!</h4>
        <p>Your data is now properly extracted. The dashboard should work with this data.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Show raw file contents option
    with st.sidebar:
        st.header("🔧 Debug Tools")
        
        selected_file = st.selectbox(
            "View raw file contents:",
            [""] + analyzer.data_files
        )
        
        if selected_file and st.button("Show Raw Contents"):
            file_path = BASE_PATH / selected_file
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    st.subheader(f"Raw Contents: {selected_file}")
                    st.text_area("File Contents", content[:5000], height=400)
                    if len(content) > 5000:
                        st.info("Showing first 5000 characters. File is larger.")
                except Exception as e:
                    st.error(f"Error reading file: {e}")

if __name__ == "__main__":
    main()
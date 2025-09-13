#!/usr/bin/env python3
"""
ARGO RAG Query Dashboard (Optimized Version)
- Efficiently loads FAISS indexes and JSON data once at server start
- Fast semantic search using pre-computed vector embeddings
- Memory-efficient design for handling large datasets
- Supports both simple and enhanced JSON formats
- Built with Streamlit for easy deployment
"""

import streamlit as st
import json
import faiss
import numpy as np
import pandas as pd
import time
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import folium_static
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from sentence_transformers import SentenceTransformer
from concurrent.futures import ThreadPoolExecutor

# -------------------------------
# Configuration
# -------------------------------
JSON_FOLDER = Path("D:/FloatChat ARGO/MINIO/Datasetjson")
INDEX_FOLDER = Path("D:/FloatChat ARGO/MINIO/VectorIndex")
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
MAX_WORKERS = 4
CACHE_TIMEOUT = 3600  # 1 hour cache timeout for indexes

# -------------------------------
# Page Config
# -------------------------------
st.set_page_config(
    page_title="🌊 ARGO Data Explorer", 
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------
# Lazy Loading Functions
# -------------------------------
@st.cache_resource(ttl=CACHE_TIMEOUT)
def load_embedding_model():
    """Load the embedding model once at server start"""
    try:
        # Try GPU first if available
        model = SentenceTransformer(EMBEDDING_MODEL, device="cuda")
        st.sidebar.success("✅ Using GPU for embeddings")
    except Exception:
        # Fall back to CPU
        model = SentenceTransformer(EMBEDDING_MODEL)
        st.sidebar.info("ℹ️ Using CPU for embeddings")
    return model

@st.cache_data(ttl=CACHE_TIMEOUT)
def list_available_years():
    """List all available years in the dataset"""
    years = []
    for year_dir in sorted(JSON_FOLDER.glob("*")):
        if year_dir.is_dir() and year_dir.name.isdigit():
            years.append(year_dir.name)
    return years

@st.cache_data(ttl=CACHE_TIMEOUT)
def list_available_months(year):
    """List all available months for a given year"""
    months = []
    year_dir = JSON_FOLDER / year
    if year_dir.exists():
        for month_dir in sorted(year_dir.glob("*")):
            if month_dir.is_dir() and month_dir.name.isdigit():
                months.append(month_dir.name)
    return months

@st.cache_data(ttl=CACHE_TIMEOUT)
def list_available_days(year, month):
    """List all available days for a given year/month"""
    days = []
    month_dir = JSON_FOLDER / year / month
    if month_dir.exists():
        for day_dir in sorted(month_dir.glob("*")):
            if day_dir.is_dir() and day_dir.name.isdigit():
                days.append(day_dir.name)
    return days

@st.cache_data(ttl=CACHE_TIMEOUT)
def list_json_files(year=None, month=None, day=None):
    """List all JSON files matching the filters"""
    if year and month and day:
        # Specific day
        target_dir = JSON_FOLDER / year / month / day
        pattern = "*.json"
    elif year and month:
        # Specific month
        target_dir = JSON_FOLDER / year / month
        pattern = "**/*.json"
    elif year:
        # Specific year
        target_dir = JSON_FOLDER / year
        pattern = "**/*.json"
    else:
        # All files
        target_dir = JSON_FOLDER
        pattern = "**/*.json"
        
    if not target_dir.exists():
        return []
        
    return sorted(target_dir.glob(pattern))

@st.cache_data(ttl=CACHE_TIMEOUT)
def load_json_data(json_path):
    """Load a single JSON file"""
    try:
        with open(json_path, "r") as f:
            return json.load(f)
    except Exception as e:
        st.warning(f"Failed to load {json_path}: {e}")
        return None

@st.cache_data(ttl=CACHE_TIMEOUT)
def load_index(index_path):
    """Load a single FAISS index"""
    try:
        index = faiss.read_index(str(index_path))
        return index
    except Exception as e:
        # Don't show warning for every failed index load
        # st.warning(f"Failed to load index {index_path}: {e}")
        return None

# -------------------------------
# Search Functions
# -------------------------------
def get_matching_index_path(json_path):
    """Convert JSON path to corresponding index path"""
    # Extract path components
    parts = list(json_path.parts)
    if "Datasetjson" in parts:
        # Replace folder prefix
        json_idx = parts.index("Datasetjson")
        parts[json_idx] = "VectorIndex"
        
        # Replace extension
        parts[-1] = json_path.stem + ".index"
        return Path(*parts)
    return None

def detect_json_format(json_data):
    """Detect if JSON is in simple or enhanced format"""
    if "file_metadata" in json_data:
        return "enhanced"
    elif "file" in json_data and "data" in json_data and "summaries" in json_data:
        return "simple"
    return "unknown"

def get_search_text_from_json(json_data, json_format):
    """Extract search text from JSON based on format"""
    if json_format == "enhanced":
        # For enhanced format, use vector_embeddings.profile_summary and variable summaries
        text = json_data.get("vector_embeddings", {}).get("profile_summary", "")
        for var in json_data.get("measurements", {}).get("core_variables", []):
            text += " " + var.get("summary", "")
        for var in json_data.get("measurements", {}).get("bgc_variables", []):
            if var.get("present", False):
                text += " " + var.get("summary", "")
        return text
    else:
        # For simple format, use summaries
        text = json_data.get("summary", "")
        for summary in json_data.get("summaries", []):
            text += " " + summary.get("variable", "") + ": " + summary.get("summary", "")
        return text

def query_single_index(query_embedding, index_path, json_path, top_k=5):
    """Query a single index file and return results"""
    # Load index and JSON data
    index = load_index(index_path)
    if index is None or index.ntotal == 0:
        return []
        
    json_data = load_json_data(json_path)
    if json_data is None:
        return []
        
    # Perform search
    D, I = index.search(query_embedding, min(top_k, index.ntotal))
    
    # Extract results
    results = []
    json_format = detect_json_format(json_data)
    
    if json_format == "enhanced":
        # For enhanced format, return structured information
        for dist, idx in zip(D[0], I[0]):
            result = {
                "file": json_data["file_metadata"]["file_id"],
                "path": str(json_path),
                "format": "enhanced",
                "distance": float(dist),
                "basin": json_data.get("geospatial", {}).get("basin", "Unknown"),
                "timestamp": json_data.get("profile_data", {}).get("juld", ["Unknown"])[0] if json_data.get("profile_data", {}).get("juld", []) else "Unknown",
                "data": json_data
            }
            
            # Add variables
            core_vars = json_data.get("measurements", {}).get("core_variables", [])
            if core_vars:
                result["variable"] = core_vars[0].get("name", "Unknown")
                result["summary"] = core_vars[0].get("summary", "Unknown")
            else:
                result["variable"] = "Unknown"
                result["summary"] = "No variables found"
                
            results.append(result)
    else:
        # For simple format, extract from summaries
        for dist, idx in zip(D[0], I[0]):
            if idx < 0 or idx >= len(json_data.get("summaries", [])):
                continue
                
            summary = json_data["summaries"][idx]
            results.append({
                "file": json_data["file"],
                "path": str(json_path),
                "format": "simple",
                "variable": summary.get("variable", ""),
                "summary": summary.get("summary", ""),
                "distance": float(dist),
                "data": json_data
            })
        
    return results

def parallel_query(query, json_files, top_k=5, max_workers=MAX_WORKERS):
    """Query multiple indexes in parallel and return combined results"""
    # Check if there are files to query
    if not json_files:
        return []
        
    # Load embedding model and encode query
    model = load_embedding_model()
    query_embedding = model.encode([query]).astype("float32")
    
    # Find matching index files
    valid_pairs = []
    for json_path in json_files:
        index_path = get_matching_index_path(json_path)
        if index_path and index_path.exists():
            valid_pairs.append((json_path, index_path))
    
    if not valid_pairs:
        return []
    
    # Use ThreadPoolExecutor for parallel processing
    all_results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {
            executor.submit(
                query_single_index, query_embedding, index_path, json_path, top_k
            ): json_path
            for json_path, index_path in valid_pairs
        }
        
        # Collect results as they complete
        for future in future_to_path:
            results = future.result()
            all_results.extend(results)
    
    # Sort by distance (lower is better)
    all_results.sort(key=lambda x: x["distance"])
    
    # Return top k results overall
    return all_results[:top_k]

# -------------------------------
# Visualization Functions
# -------------------------------
def format_result(result):
    """Format a search result for display"""
    # Extract path components to get date
    path_parts = result["path"].split("/")
    date_parts = []
    
    # Extract date components from path if available
    for part in path_parts:
        if part.isdigit():
            date_parts.append(part)
    
    # Format date as YYYY-MM-DD if we have enough parts
    date_str = ""
    if len(date_parts) >= 3:
        date_str = f"{date_parts[0]}-{date_parts[1]}-{date_parts[2]}"
    
    # Get timestamp from enhanced format if available
    if result.get("format") == "enhanced" and result.get("timestamp"):
        timestamp = result.get("timestamp")
        if timestamp and timestamp != "Unknown":
            # Trim timestamp to just date part if needed
            if "T" in timestamp:
                timestamp = timestamp.split("T")[0]
            date_str = timestamp
    
    return {
        "File": result["file"],
        "Date": date_str,
        "Variable": result["variable"],
        "Description": result["summary"],
        "Basin": result.get("basin", "Unknown"),
        "Score": f"{1.0 / (1.0 + result['distance']):.2f}"
    }

def create_results_table(results):
    """Create a DataFrame from search results"""
    if not results:
        return pd.DataFrame()
    
    formatted = [format_result(r) for r in results]
    return pd.DataFrame(formatted)

def extract_geospatial_data(results):
    """Extract geospatial data from results for visualization"""
    geo_data = []
    
    for result in results:
        json_format = result.get("format", "simple")
        json_data = result.get("data", {})
        
        if json_format == "enhanced":
            positions = json_data.get("geospatial", {}).get("positions", [])
            if positions:
                for pos in positions:
                    geo_data.append({
                        "file": result["file"],
                        "latitude": pos.get("latitude", 0),
                        "longitude": pos.get("longitude", 0),
                        "timestamp": pos.get("timestamp", "Unknown"),
                        "qc": pos.get("qc", "Unknown"),
                        "variable": result.get("variable", "Unknown"),
                        "summary": result.get("summary", "Unknown")
                    })
        else:
            # Try to extract from simple format
            if "LATITUDE" in json_data.get("data", {}) and "LONGITUDE" in json_data.get("data", {}):
                lat_data = json_data["data"]["LATITUDE"]
                lon_data = json_data["data"]["LONGITUDE"]
                
                # Handle different data formats
                if isinstance(lat_data, list) and isinstance(lon_data, list):
                    for i in range(min(len(lat_data), len(lon_data))):
                        geo_data.append({
                            "file": result["file"],
                            "latitude": lat_data[i],
                            "longitude": lon_data[i],
                            "timestamp": "Unknown",
                            "qc": "Unknown",
                            "variable": result.get("variable", "Unknown"),
                            "summary": result.get("summary", "Unknown")
                        })
    
    return geo_data

def plot_geospatial_data(geo_data):
    """Create a Folium map with the geospatial data"""
    if not geo_data:
        return None
    
    # Calculate the center of the map
    center_lat = sum(item["latitude"] for item in geo_data) / len(geo_data)
    center_lon = sum(item["longitude"] for item in geo_data) / len(geo_data)
    
    # Create a map
    m = folium.Map(location=[center_lat, center_lon], zoom_start=4)
    
    # Create a marker cluster
    marker_cluster = MarkerCluster().add_to(m)
    
    # Add markers for each position
    for item in geo_data:
        popup_text = f"""
        <b>File:</b> {item['file']}<br>
        <b>Variable:</b> {item['variable']}<br>
        <b>Timestamp:</b> {item['timestamp']}<br>
        <b>QC:</b> {item['qc']}<br>
        <b>Summary:</b> {item['summary']}
        """
        
        folium.Marker(
            location=[item["latitude"], item["longitude"]],
            popup=folium.Popup(popup_text, max_width=300),
            icon=folium.Icon(color="blue", icon="info-sign")
        ).add_to(marker_cluster)
    
    return m

def plot_temperature_profile(json_data, json_format):
    """Create a temperature profile plot from the data"""
    try:
        if json_format == "enhanced":
            # Extract temperature from enhanced format
            temp_var = None
            for var in json_data.get("measurements", {}).get("core_variables", []):
                if var.get("name") == "TEMP":
                    temp_var = var
                    break
            
            if not temp_var:
                return None
            
            # Create figure with labels from the variable info
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=[float(temp_var.get("summary", "").split("min=")[1].split(",")[0]),
                   float(temp_var.get("summary", "").split("max=")[1].split(",")[0])],
                y=[0, 2000],  # Approximate depth range
                mode="lines",
                name="Temperature Range"
            ))
            
            fig.update_layout(
                title=f"Temperature Profile for {json_data['file_metadata']['file_id']}",
                xaxis_title=f"Temperature ({temp_var.get('unit', '°C')})",
                yaxis_title="Depth (m)",
                yaxis=dict(autorange="reversed")  # Reverse y-axis for depth
            )
            
            return fig
            
        else:
            # Try to extract from simple format if available
            if "TEMP" in json_data.get("data", {}):
                temp_data = json_data["data"]["TEMP"]
                
                if isinstance(temp_data, dict) and "min" in temp_data and "max" in temp_data:
                    # Create simple plot from min/max
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=[temp_data["min"], temp_data["max"]],
                        y=[0, 2000],  # Approximate depth range
                        mode="lines",
                        name="Temperature Range"
                    ))
                    
                    fig.update_layout(
                        title=f"Temperature Profile for {json_data['file']}",
                        xaxis_title="Temperature (°C)",
                        yaxis_title="Depth (m)",
                        yaxis=dict(autorange="reversed")  # Reverse y-axis for depth
                    )
                    
                    return fig
            
            return None
            
    except Exception as e:
        st.warning(f"Failed to create temperature profile: {e}")
        return None

# -------------------------------
# Streamlit UI
# -------------------------------
def main():
    st.title("🌊 ARGO Data Explorer")
    st.markdown(
        "Search your Argo oceanographic data using natural language queries. "
        "This app uses vector similarity search (FAISS) to find relevant variables."
    )
    
    # Sidebar filters
    st.sidebar.header("Data Filters")
    
    # Year filter
    years = list_available_years()
    if not years:
        st.error("No data found in Datasetjson folder. Please run the pipeline first.")
        return
    
    year = st.sidebar.selectbox("Year", ["All"] + years, index=0)
    
    # Month filter (only show if year is selected)
    month = None
    if year != "All":
        months = list_available_months(year)
        month = st.sidebar.selectbox("Month", ["All"] + months, index=0)
    
    # Day filter (only show if month is selected)
    day = None
    if month and month != "All":
        days = list_available_days(year, month)
        day = st.sidebar.selectbox("Day", ["All"] + days, index=0)
    
    # Get matching JSON files based on filters
    if year == "All":
        json_files = list_json_files()
    elif month == "All":
        json_files = list_json_files(year)
    elif day == "All":
        json_files = list_json_files(year, month)
    else:
        json_files = list_json_files(year, month, day)
    
    # Display dataset statistics
    st.sidebar.header("Dataset Stats")
    st.sidebar.metric("Total Files", len(json_files))
    
    # Advanced settings
    st.sidebar.header("Search Settings")
    top_k = st.sidebar.slider("Max Results", 1, 50, 10)
    
    # Search bar
    query = st.text_input("Enter your search query (e.g., 'temperature measurements', 'salinity data', 'coordinates in Indian Ocean')")
    
    if query:
        # Show spinner during search
        with st.spinner("Searching..."):
            start_time = time.time()
            results = parallel_query(query, json_files, top_k=top_k)
            end_time = time.time()
        
        # Display results
        st.success(f"Found {len(results)} results in {end_time - start_time:.2f} seconds")
        
        if results:
            # Create tabs for different views
            tab1, tab2, tab3 = st.tabs(["Results Table", "Map View", "Profile Visualization"])
            
            with tab1:
                # Create and display results table
                results_df = create_results_table(results)
                st.dataframe(results_df, use_container_width=True)
            
            with tab2:
                # Extract geospatial data and create map
                geo_data = extract_geospatial_data(results)
                if geo_data:
                    st.subheader("Geographic Distribution")
                    map_fig = plot_geospatial_data(geo_data)
                    folium_static(map_fig, width=800)
                else:
                    st.info("No geospatial data available for the selected results.")
            
            with tab3:
                # Allow viewing temperature profiles
                st.subheader("Temperature Profile")
                if results:
                    # Get list of files from results
                    file_options = [r["file"] for r in results]
                    selected_file = st.selectbox("Select a file to view temperature profile", file_options)
                    
                    # Find the matching result
                    for r in results:
                        if r["file"] == selected_file:
                            # Get the JSON data and format
                            json_data = r["data"]
                            json_format = r["format"]
                            
                            # Create temperature profile plot
                            temp_fig = plot_temperature_profile(json_data, json_format)
                            if temp_fig:
                                st.plotly_chart(temp_fig, use_container_width=True)
                            else:
                                st.info("No temperature data available for this profile.")
                            
                            break
                    
                    # Show variable details
                    st.subheader("Variable Details")
                    selected_result = next((r for r in results if r["file"] == selected_file), None)
                    
                    if selected_result:
                        json_data = selected_result["data"]
                        json_format = selected_result["format"]
                        
                        if json_format == "enhanced":
                            # Display core variables
                            st.markdown("### Core Variables")
                            core_vars = json_data.get("measurements", {}).get("core_variables", [])
                            
                            for var in core_vars:
                                with st.expander(f"{var.get('name', 'Unknown')} - {var.get('description', '')}"):
                                    st.markdown(f"**Summary:** {var.get('summary', 'No summary available')}")
                                    st.markdown(f"**Unit:** {var.get('unit', 'Unknown')}")
                                    st.markdown(f"**QC:** {var.get('qc', 'Unknown')}")
                                    st.markdown(f"**Sampling Scheme:** {var.get('sampling_scheme', 'Unknown')}")
                            
                            # Display BGC variables if present
                            bgc_vars = [v for v in json_data.get("measurements", {}).get("bgc_variables", []) if v.get("present", False)]
                            
                            if bgc_vars:
                                st.markdown("### BGC Variables")
                                for var in bgc_vars:
                                    with st.expander(f"{var.get('name', 'Unknown')} - {var.get('description', '')}"):
                                        st.markdown(f"**Summary:** {var.get('summary', 'No summary available')}")
                                        st.markdown(f"**Unit:** {var.get('unit', 'Unknown')}")
                                        st.markdown(f"**QC:** {var.get('qc', 'Unknown')}")
                        else:
                            # Display variable summaries for simple format
                            st.markdown("### Variables")
                            summaries = json_data.get("summaries", [])
                            
                            for summary in summaries:
                                var_name = summary.get("variable", "Unknown")
                                with st.expander(var_name):
                                    st.markdown(f"**Summary:** {summary.get('summary', 'No summary available')}")
                                    
                                    # Try to get the raw data
                                    if var_name in json_data.get("data", {}):
                                        var_data = json_data["data"][var_name]
                                        
                                        if isinstance(var_data, dict):
                                            # Display as formatted JSON
                                            st.json(var_data)
                                        elif isinstance(var_data, list) and len(var_data) > 0:
                                            # For lists, show first few items
                                            if len(var_data) <= 5:
                                                st.write(var_data)
                                            else:
                                                st.write(f"List with {len(var_data)} items. First 5: {var_data[:5]}")
                                        else:
                                            # Show as plain text
                                            st.write(var_data)
            
            # Allow downloading JSON data
            st.markdown("---")
            st.subheader("Download Data")
            
            if results:
                # Get list of files from results
                file_options = [r["file"] for r in results]
                selected_file_dl = st.selectbox("Select a file to download", file_options, key="download_select")
                
                # Find the matching result
                for r in results:
                    if r["file"] == selected_file_dl:
                        # Create JSON string
                        json_str = json.dumps(r["data"], indent=2)
                        
                        # Create download button
                        st.download_button(
                            label="Download JSON",
                            data=json_str,
                            file_name=f"{r['file']}.json",
                            mime="application/json"
                        )
                        
                        break
                        
        else:
            st.info("No results found. Try a different query or adjust your filters.")
    else:
        # Show example queries
        st.markdown("### Example Queries")
        examples = [
            "temperature measurements in the Indian Ocean",
            "salinity data from 2024",
            "ARGO float locations and coordinates",
            "pressure readings from deep water",
            "oceanographic variables for February 2024",
            "dissolved oxygen measurements",
            "chlorophyll concentrations in the ocean",
            "high temperature readings near the equator",
            "low salinity areas in the Indian Ocean",
            "ARGO data with both temperature and salinity"
        ]
        
        col1, col2 = st.columns(2)
        
        for i, ex in enumerate(examples):
            if i < len(examples) // 2:
                with col1:
                    if st.button(ex):
                        # This will be caught and handled when the app reruns
                        st.session_state["query"] = ex
                        st.rerun()
            else:
                with col2:
                    if st.button(ex):
                        # This will be caught and handled when the app reruns
                        st.session_state["query"] = ex
                        st.rerun()
        
        # Show information about the data format
        st.markdown("---")
        st.subheader("About ARGO Data")
        
        with st.expander("What is ARGO?"):
            st.markdown("""
            The Argo program deploys autonomous profiling floats across the world's oceans. These floats:
            
            - Drift at a depth of 1000 meters (parking depth)
            - Every 10 days, dive to 2000 meters then rise to the surface, measuring temperature and salinity
            - Transmit the data to satellites when they reach the surface
            - Provide essential data for studying ocean circulation, climate, and marine ecosystems
            
            This app allows you to search and explore ARGO data using natural language queries and advanced vector search technology.
            """)
            
        with st.expander("Core Variables"):
            st.markdown("""
            ARGO floats measure several core variables:
            
            - **TEMP**: Sea water temperature (°C)
            - **PSAL**: Sea water practical salinity (PSU)
            - **PRES**: Sea water pressure (dbar)
            
            These measurements are taken at various depths as the float ascends from 2000 meters to the surface.
            """)
            
        with st.expander("BGC Variables (Biogeochemical)"):
            st.markdown("""
            Some advanced ARGO floats also measure biogeochemical variables:
            
            - **DOXY**: Dissolved oxygen concentration (micromol/kg)
            - **CHLA**: Chlorophyll-a concentration (mg/m³)
            - **NITRATE**: Nitrate concentration (micromol/kg)
            - **PH_IN_SITU_TOTAL**: pH (pH units)
            - **CDOM**: Colored dissolved organic matter (ppb)
            - **BBP700**: Particle backscattering at 700nm (m⁻¹)
            
            These measurements are critical for studying ocean health, carbon cycles, and marine ecosystems.
            """)

if __name__ == "__main__":
    # Load query from session state if available
    if "query" in st.session_state:
        query = st.session_state["query"]
        # Clear it from session state to avoid reuse
        del st.session_state["query"]
    else:
        query = ""
    
    main()
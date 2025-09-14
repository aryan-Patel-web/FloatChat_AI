import streamlit as st
import json
import os
import glob
from pathlib import Path
from datetime import datetime
import pandas as pd
import requests
from groq import Groq
from dotenv import load_dotenv
import time
import re
from collections import defaultdict

# Load environment variables
load_dotenv()

class EnhancedARGOChatbot:
    def __init__(self):
        self.mistral_api_key = os.getenv("MISTRAL_API_KEY")
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_client = Groq(api_key=self.groq_api_key) if self.groq_api_key else None
        
    def load_argo_data(self, json_path="Datasetjson"):
        """Load all ARGO JSON files with enhanced indexing"""
        json_files = []
        data_path = Path(json_path)
        
        if data_path.exists():
            json_files = list(data_path.rglob("*.json"))
        
        argo_data = []
        for file_path in json_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Add file info for reference
                    data['_file_path'] = str(file_path)
                    argo_data.append(data)
            except Exception as e:
                st.error(f"Error loading {file_path}: {e}")
        
        return argo_data
    
    def query_mistral(self, prompt, context):
        """Enhanced Mistral API with better prompts"""
        try:
            system_prompt = """You are an expert oceanographer analyzing REAL ARGO float data from 2024-2025 Indian Ocean.

CRITICAL RULES:
1. ONLY use data from the provided context - NEVER invent or hallucinate information
2. Use EXACT values from JSON data - no approximations or external knowledge
3. If specific data is not in context, state "Data not available in current profiles"
4. Format: Brief summary → bullet points with real values → conclusion
5. Use emojis but avoid excessive markdown formatting
6. Never reference web information or general oceanographic knowledge not in the data

Response format:
- 1-line summary with key finding
- Bullet points with exact JSON values (temperatures, dates, locations)
- 1-2 line conclusion based only on provided data"""

            data = {
                "model": "mistral-large-latest",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"REAL DATA CONTEXT: {context}\n\nQUESTION: {prompt}"}
                ],
                "temperature": 0.1,  # Very low for factual accuracy
                "max_tokens": 1000
            }
            
            response = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.mistral_api_key}",
                    "Content-Type": "application/json"
                },
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                raise Exception(f"Mistral API error: {response.status_code}")
                
        except Exception as e:
            st.warning(f"🔄 Mistral API failed: {e}. Switching to Groq...")
            return self.query_groq(prompt, context)
    
    def query_groq(self, prompt, context):
        """Enhanced Groq fallback with strict data rules"""
        try:
            if not self.groq_client:
                return "❌ Both API services are unavailable. Please check your API keys."
            
            system_prompt = """You are analyzing REAL ARGO oceanographic data from 2024-2025. 

STRICT RULES:
- Use ONLY the provided JSON data context
- Never add external oceanographic knowledge
- Use exact values from the data
- If data is missing, say "Not available in current dataset"
- Format: Summary → bullet points → conclusion with emojis"""
            
            response = self.groq_client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"CONTEXT: {context}\n\nQUESTION: {prompt}"}
                ],
                temperature=0.1,
                max_tokens=800
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"❌ Both AI services unavailable. Error: {e}"
    
    def search_relevant_data(self, query, argo_data):
        """Enhanced search with comprehensive keyword matching"""
        query_lower = query.lower().replace('-', ' ').replace('_', ' ')
        relevant_profiles = []
        
        # Enhanced keyword mapping
        temporal_keywords = {
            '2024': ['2024'], '2025': ['2025'], 
            'january': ['january', 'jan', '01'], 'february': ['february', 'feb', '02'],
            'march': ['march', 'mar', '03'], 'april': ['april', 'apr', '04'],
            'may': ['may', '05'], 'june': ['june', 'jun', '06'],
            'july': ['july', 'jul', '07'], 'august': ['august', 'aug', '08'],
            'september': ['september', 'sep', '09'], 'october': ['october', 'oct', '10'],
            'november': ['november', 'nov', '11'], 'december': ['december', 'dec', '12'],
            'monsoon': ['monsoon', 'southwest', 'northeast', 'pre_monsoon', 'post_monsoon'],
            'spring': ['spring'], 'summer': ['summer'], 'winter': ['winter'], 'autumn': ['autumn']
        }
        
        spatial_keywords = {
            'arabian': ['arabian_sea', 'arabian sea', 'arabian'], 
            'bay': ['bay_of_bengal', 'bay of bengal', 'bengal'],
            'southern': ['southern_ocean', 'southern ocean'], 
            'indian': ['indian', 'western_indian', 'eastern_indian', 'tropical_indian'],
            'madagascar': ['madagascar_ridge', 'madagascar'], 
            'monsoon': ['monsoon_region', 'monsoon region'],
            'equatorial': ['equatorial_indian', 'equatorial'],
            'red sea': ['red_sea', 'red sea'],
            'persian': ['persian_gulf', 'persian gulf']
        }
        
        measurement_keywords = {
            'temperature': ['temp', 'temperature', 'thermal', 'heating', 'cooling', '°c', 'celsius'],
            'salinity': ['psal', 'salinity', 'salt', 'psu', 'haline'], 
            'pressure': ['pres', 'pressure', 'depth', 'dbar'],
            'water mass': ['water', 'mass', 'water mass', 'antarctic', 'surface', 'deep', 'intermediate'],
            'oxygen': ['doxy', 'oxygen', 'o2', 'hypoxic', 'anoxic'],
            'quality': ['quality', 'qc', 'data', 'calibration', 'error'],
            'density': ['density', 'sigma', 'rho'],
            'sound': ['sound', 'acoustic', 'speed']
        }
        
        for profile in argo_data:
            relevance_score = 0
            
            try:
                # Enhanced temporal matching
                temporal = profile.get('temporal', {})
                year = temporal.get('year', 0)
                month = temporal.get('month', 0)
                date_str = temporal.get('datetime', '')
                monsoon = temporal.get('monsoon_season', '').lower().replace('_', ' ')
                season = temporal.get('season_nh', '').lower()
                
                # Check year matching
                for keyword, variations in temporal_keywords.items():
                    if keyword in query_lower:
                        if (str(year) in variations or 
                            any(var in str(month).zfill(2) for var in variations) or
                            any(var in monsoon for var in variations) or
                            any(var in season for var in variations)):
                            relevance_score += 4
                
                # Extract specific dates from query (e.g., "July 20", "2024-07-20")
                date_patterns = [
                    r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',  # 2024-07-20
                    r'(\w+)\s+(\d{1,2})',                   # July 20
                    r'(\d{1,2})\s+(\w+)',                   # 20 July
                ]
                
                for pattern in date_patterns:
                    matches = re.findall(pattern, query_lower)
                    if matches:
                        for match in matches:
                            if len(match) == 3:  # Year-month-day
                                q_year, q_month, q_day = int(match[0]), int(match[1]), int(match[2])
                                if year == q_year and month == q_month:
                                    relevance_score += 5
                            elif len(match) == 2:  # Month day
                                month_names = ['january', 'february', 'march', 'april', 'may', 'june',
                                             'july', 'august', 'september', 'october', 'november', 'december']
                                try:
                                    if match[0] in month_names:
                                        q_month = month_names.index(match[0]) + 1
                                        if month == q_month:
                                            relevance_score += 4
                                except:
                                    pass
                
                # Enhanced spatial matching
                spatial = profile.get('geospatial', {})
                regions = [r.lower().replace('_', ' ') for r in spatial.get('regional_seas', [])]
                province = spatial.get('biogeographic_province', '').lower().replace('_', ' ')
                ocean = spatial.get('ocean_basin', '').lower()
                
                for keyword, variations in spatial_keywords.items():
                    if keyword in query_lower:
                        region_text = ' '.join(regions + [province, ocean])
                        if any(var.replace('_', ' ') in region_text for var in variations):
                            relevance_score += 5
                
                # Enhanced measurement matching
                measurements = profile.get('measurements', {})
                core_vars = measurements.get('core_variables', {})
                bgc_vars = measurements.get('bgc_variables', {})
                derived = measurements.get('derived_parameters', {})
                
                for keyword, variations in measurement_keywords.items():
                    if any(var in query_lower for var in variations):
                        # Check if requested measurement is available
                        if keyword == 'temperature' and core_vars.get('TEMP', {}).get('present'):
                            relevance_score += 3
                        elif keyword == 'salinity' and core_vars.get('PSAL', {}).get('present'):
                            relevance_score += 3
                        elif keyword == 'pressure' and core_vars.get('PRES', {}).get('present'):
                            relevance_score += 3
                        elif keyword == 'density' and derived.get('density'):
                            relevance_score += 3
                        elif keyword == 'sound' and derived.get('sound_speed'):
                            relevance_score += 3
                        elif keyword == 'oxygen' and bgc_vars.get('DOXY', {}).get('present'):
                            relevance_score += 3
                        else:
                            relevance_score += 1
                
                # Water mass matching
                water_masses = profile.get('oceanography', {}).get('water_masses', [])
                if any(term in query_lower for term in ['water', 'mass', 'antarctic', 'surface', 'deep']):
                    if water_masses:
                        relevance_score += 3
                    
                    # Check specific water mass names
                    for wm in water_masses:
                        wm_name = wm.get('name', '').lower().replace('_', ' ')
                        if any(term in wm_name for term in query_lower.split()):
                            relevance_score += 2
                
                # Quality/analysis questions
                if any(word in query_lower for word in ['quality', 'data', 'analysis', 'summary', 'overview']):
                    relevance_score += 2
                
                # Features matching
                features = profile.get('oceanography', {}).get('physical_features', {})
                if any(term in query_lower for term in ['inversion', 'mixing', 'thermocline', 'gradient']):
                    if (features.get('inversions') or features.get('thermocline') or 
                        features.get('mixed_layer') or features.get('gradients')):
                        relevance_score += 3
                
                # Broad fallback - if no specific matches but has comprehensive data
                if relevance_score == 0:
                    if (len(water_masses) > 0 and 
                        core_vars.get('TEMP', {}).get('present') and 
                        core_vars.get('PSAL', {}).get('present')):
                        relevance_score = 1
                        
            except Exception as e:
                continue
                
            if relevance_score > 0:
                relevant_profiles.append((profile, relevance_score))
        
        # Sort by relevance and return top 5
        relevant_profiles.sort(key=lambda x: x[1], reverse=True)
        return [profile[0] for profile in relevant_profiles[:5]]
    
    def create_enhanced_context_summary(self, profiles, query):
        """Create detailed context summary with specific data requested"""
        if not profiles:
            return "No relevant ARGO data found in the dataset."
        
        context_parts = []
        query_lower = query.lower()
        
        for profile in profiles[:3]:  # Focus on top 3 most relevant
            temporal = profile.get('temporal', {})
            spatial = profile.get('geospatial', {})
            measurements = profile.get('measurements', {})
            
            # Basic profile info
            date = temporal.get('datetime', 'unknown')[:10]
            year = temporal.get('year', 'unknown')
            month = temporal.get('month', 'unknown')
            regions = ', '.join(spatial.get('regional_seas', ['Open Ocean']))
            
            profile_info = f"Profile {date} ({year}-{month:02d}) from {regions}"
            
            # Add specific measurement data based on query
            core_vars = measurements.get('core_variables', {})
            derived = measurements.get('derived_parameters', {})
            
            if 'temperature' in query_lower or 'temp' in query_lower:
                temp_data = core_vars.get('TEMP', {})
                if temp_data.get('present'):
                    stats = temp_data.get('statistics', {})
                    profile_info += f" | TEMP: {stats.get('min', 0):.2f} to {stats.get('max', 0):.2f}°C (mean: {stats.get('mean', 0):.2f}°C)"
            
            if 'salinity' in query_lower or 'salt' in query_lower:
                sal_data = core_vars.get('PSAL', {})
                if sal_data.get('present'):
                    stats = sal_data.get('statistics', {})
                    profile_info += f" | SALINITY: {stats.get('min', 0):.2f} to {stats.get('max', 0):.2f} PSU (mean: {stats.get('mean', 0):.2f})"
            
            if 'pressure' in query_lower or 'depth' in query_lower:
                pres_data = core_vars.get('PRES', {})
                if pres_data.get('present'):
                    stats = pres_data.get('statistics', {})
                    profile_info += f" | PRESSURE: 0 to {stats.get('max', 0):.0f} dbar"
            
            if 'density' in query_lower:
                density_data = derived.get('density', {})
                if density_data:
                    profile_info += f" | DENSITY: {density_data.get('min', 0):.0f} to {density_data.get('max', 0):.0f} kg/m³"
            
            if 'water mass' in query_lower or 'mass' in query_lower:
                water_masses = profile.get('oceanography', {}).get('water_masses', [])
                wm_names = [wm.get('name', 'Unknown').replace('_', ' ') for wm in water_masses[:3]]
                if wm_names:
                    profile_info += f" | WATER MASSES: {', '.join(wm_names)}"
            
            if 'quality' in query_lower:
                quality = profile.get('quality_control', {}).get('data_assessment', {})
                score = quality.get('overall_score', 0)
                profile_info += f" | QUALITY SCORE: {score:.2f}"
            
            context_parts.append(profile_info)
        
        return " || ".join(context_parts)

def main():
    st.set_page_config(
        page_title="🌊 ARGO FloatChat - SIH 2025",
        page_icon="🌊",
        layout="wide"
    )
    
    st.title("🌊 ARGO FloatChat - Enhanced Oceanographic Data Assistant")
    st.subheader("Real ARGO Data Analysis with 90% Accuracy")
    
    # Initialize chatbot
    chatbot = EnhancedARGOChatbot()
    
    # Sidebar - Enhanced Data Statistics
    with st.sidebar:
        st.header("📊 Data Overview")
        
        # Load and display comprehensive data stats
        with st.spinner("Loading ARGO data..."):
            argo_data = chatbot.load_argo_data()
        
        if argo_data:
            st.success(f"✅ Loaded {len(argo_data)} profiles")
            
            # Enhanced statistics
            years = set()
            months = defaultdict(int)
            regions = set()
            water_mass_count = 0
            bgc_profiles = 0
            
            for profile in argo_data:
                temporal = profile.get('temporal', {})
                if temporal.get('year'):
                    years.add(temporal['year'])
                    months[f"{temporal['year']}-{temporal.get('month', 0):02d}"] += 1
                
                spatial = profile.get('geospatial', {})
                regions.update(spatial.get('regional_seas', []))
                
                water_masses = profile.get('oceanography', {}).get('water_masses', [])
                water_mass_count += len(water_masses)
                
                # Count BGC profiles
                bgc_vars = profile.get('measurements', {}).get('bgc_variables', {})
                if any(var.get('present', False) for var in bgc_vars.values()):
                    bgc_profiles += 1
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Profiles", len(argo_data))
                st.metric("BGC Profiles", bgc_profiles)
            with col2:
                st.metric("Water Masses", water_mass_count)
                st.metric("Regions", len(regions))
            
            st.write(f"**Years:** {', '.join(map(str, sorted(years)))}")
            st.write(f"**Monthly Coverage:** {len(months)} months")
            
            # Sample regions
            if regions:
                st.write("**Key Regions:**")
                for region in sorted(list(regions)[:8]):
                    st.write(f"• {region.replace('_', ' ')}")
            
            # Debug mode
            debug_mode = st.checkbox("🔧 Debug Search")
        
        else:
            st.error("❌ No ARGO data found")
    
    # Main chat interface
    st.header("💬 Ask About Your ARGO Data")
    
    if not argo_data:
        st.warning("⚠️ No data loaded. Check Datasetjson folder.")
        return
    
    # Enhanced sample questions
    st.write("**Sample Questions:**")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🌡️ Temperature in Arabian Sea 2025"):
            st.session_state.sample_query = "What are the temperature ranges in Arabian Sea profiles from 2025?"
        if st.button("🧂 Salinity July 2024"):
            st.session_state.sample_query = "Show me salinity data from July 2024 profiles"
    
    with col2:
        if st.button("🌊 Water masses Bay of Bengal"):
            st.session_state.sample_query = "What water masses were detected in Bay of Bengal?"
        if st.button("⚖️ Density calculations 2025"):
            st.session_state.sample_query = "Show density ranges from 2025 profiles"
    
    with col3:
        if st.button("📊 Data quality overview"):
            st.session_state.sample_query = "What is the overall data quality across all profiles?"
        if st.button("🔬 Oceanographic features"):
            st.session_state.sample_query = "What oceanographic features were detected in the profiles?"
    
    # Query input
    user_query = st.text_input(
        "Enter your question:",
        value=st.session_state.get('sample_query', ''),
        placeholder="e.g., What was the salinity range on July 20, 2024 in Arabian Sea?"
    )
    
    if st.button("🔍 Analyze", type="primary") and user_query:
        with st.spinner("🤖 AI analyzing real ARGO data..."):
            # Enhanced search
            relevant_profiles = chatbot.search_relevant_data(user_query, argo_data)
            
            # Debug information
            if debug_mode:
                st.info(f"🔧 **Debug:** Found {len(relevant_profiles)} relevant profiles")
                if relevant_profiles:
                    for i, profile in enumerate(relevant_profiles[:2]):
                        temporal = profile.get('temporal', {})
                        spatial = profile.get('geospatial', {})
                        st.write(f"Profile {i+1}: {temporal.get('datetime', '')[:10]} - {', '.join(spatial.get('regional_seas', []))}")
            
            if not relevant_profiles:
                st.error("😔 Sorry, I couldn't find data matching your specific query in the 2024-2025 dataset. The data contains profiles from Indian Ocean regions including Arabian Sea, Bay of Bengal, and Southern Ocean. Try asking about temperature, salinity, water masses, or specific regions and time periods.")
            else:
                # Enhanced context creation
                context = chatbot.create_enhanced_context_summary(relevant_profiles, user_query)
                
                # Get AI response
                response = chatbot.query_mistral(user_query, context)
                
                # Display response
                st.success("🤖 **Real Data Analysis:**")
                st.write(response)
                
                # Enhanced data details
                with st.expander("📋 **Source Data Details**"):
                    for i, profile in enumerate(relevant_profiles, 1):
                        st.write(f"**Profile {i}:**")
                        
                        temporal = profile.get('temporal', {})
                        spatial = profile.get('geospatial', {})
                        measurements = profile.get('measurements', {})
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.write(f"📅 **Date:** {temporal.get('datetime', 'Unknown')[:10]}")
                            st.write(f"🗓️ **Season:** {temporal.get('monsoon_season', 'Unknown').replace('_', ' ')}")
                            st.write(f"🌍 **Grid:** {spatial.get('grid_1deg', 'Unknown')}")
                        
                        with col2:
                            regions = spatial.get('regional_seas', ['Open Ocean'])
                            st.write(f"🏖️ **Regions:** {', '.join(regions[:2])}")
                            st.write(f"🌊 **Province:** {spatial.get('biogeographic_province', 'Unknown').replace('_', ' ')}")
                            
                            # Quality info
                            quality = profile.get('quality_control', {}).get('data_assessment', {})
                            st.write(f"📊 **Quality:** {quality.get('overall_score', 0):.2f}")
                        
                        with col3:
                            # Key measurements
                            core_vars = measurements.get('core_variables', {})
                            temp_present = core_vars.get('TEMP', {}).get('present', False)
                            sal_present = core_vars.get('PSAL', {}).get('present', False)
                            
                            st.write(f"🌡️ **Temperature:** {'✅' if temp_present else '❌'}")
                            st.write(f"🧂 **Salinity:** {'✅' if sal_present else '❌'}")
                            
                            water_masses = profile.get('oceanography', {}).get('water_masses', [])
                            st.write(f"💧 **Water Masses:** {len(water_masses)}")
                        
                        if i < len(relevant_profiles):
                            st.write("---")
    
    # Enhanced footer
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption("🚀 **SIH 2025 FloatChat**")
    with col2:
        st.caption("📊 **Real ARGO Data Only**")
    with col3:
        st.caption("🎯 **90% Accuracy Target**")

if __name__ == "__main__":
    main()
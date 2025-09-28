import streamlit as st
import json
import os
from pathlib import Path
import pandas as pd
import numpy as np
import requests
import base64
from google.cloud import storage
from groq import Groq
from dotenv import load_dotenv
import time
import re
from collections import defaultdict
from datetime import datetime

# Import the NC converter and export utilities
from nc_converter import convert_nc_to_json
from export_utils import (export_ascii, export_csv, export_json, 
                          export_netcdf, export_session, get_summary_report)

load_dotenv()


st.set_page_config(
    page_title="FloatChat AI",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS copied from 1map.py - exact same styling
def inject_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .stApp { background: #0a0a0a; }
    .main { padding: 0 !important; }
    .block-container { padding: 1rem 1.5rem !important; max-width: 100% !important; }
    
    h1 { color: #00b4d8; font-size: 1.6rem; margin-bottom: 0.3rem; }
    h3 { color: #90e0ef; font-size: 1rem; margin: 0.5rem 0; }
    
    /* SIDEBAR - Purple Dark Theme */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1625 0%, #0f0a1e 100%);
        border-right: 2px solid #2d1b69;
    }
    
    section[data-testid="stSidebar"] > div {
        background: transparent;
        padding: 1.5rem 1rem;
    }
    
    /* Sidebar Headers */
    section[data-testid="stSidebar"] h3 {
        color: #9d84c7 !important;
        font-size: 0.9rem;
        margin: 1rem 0 0.6rem 0;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    
    /* Sidebar Buttons - Equal Size & Purple Theme */
    section[data-testid="stSidebar"] .stButton button {
        background: linear-gradient(145deg, #2d1b69, #1a0f3d) !important;
        color: #b8a3d9 !important;
        border: 1px solid #3d2472 !important;
        border-radius: 8px !important;
        padding: 0.65rem 1rem !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        width: 100% !important;
        height: 42px !important;
        min-width: 100% !important;
        box-shadow: 0 2px 8px rgba(45, 27, 105, 0.4) !important;
        transition: all 0.3s ease !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
    }
    
    section[data-testid="stSidebar"] .stButton button:hover {
        background: linear-gradient(145deg, #4a2f8c, #2d1b69) !important;
        border-color: #6a4ba8 !important;
        color: #e0d4f7 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(106, 75, 168, 0.5) !important;
    }
    
    section[data-testid="stSidebar"] .stButton button:active {
        transform: translateY(0) !important;
    }
    
    /* Sidebar Stats Text */
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        color: #9d84c7 !important;
    }
    
    /* Sidebar Dividers */
    section[data-testid="stSidebar"] hr {
        border-color: #2d1b69;
        margin: 1rem 0;
        opacity: 0.5;
    }
    
    /* Sidebar Text Colors */
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] div {
        color: #b8a3d9 !important;
    }
    
    section[data-testid="stSidebar"] .stCaption {
        color: #6a4ba8 !important;
        font-size: 0.75rem !important;
    }
    
    /* Header */
    .main-header {
        background: #0a0a0a;
        padding: 1rem 2rem;
        border-bottom: 1px solid #00b4d8;
        position: sticky;
        top: 0;
        z-index: 100;
        text-align: center;
    }
    
    .main-header h1 {
        color: #00b4d8;
        font-size: 1.5rem;
        font-weight: 600;
        margin: 0;
    }
    
    .main-header p {
        color: #90e0ef;
        font-size: 0.9rem;
        margin: 0.25rem 0 0 0;
    }
    
    /* Chat messages */
    .chat-container {
        max-width: 900px;
        margin: 0 auto;
        padding: 1.5rem 1rem;
    }
    
    .chat-message {
        padding: 0.8rem 1.1rem;
        margin-bottom: 1rem;
        border-radius: 16px;
        animation: fadeIn 0.3s ease-out;
        width: fit-content;
        max-width: 70%;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .user-message {
        background: linear-gradient(135deg, #0077b6 0%, #00b4d8 100%);
        border: 1px solid #0096c7;
        color: #ffffff;
        margin-left: auto;
        margin-right: 0;
        max-width: 65%;
        box-shadow: 0 4px 12px rgba(0,119,182,0.3);
    }
    
    .assistant-message {
        background: #16213e;
        border: 1px solid #0f3460;
        color: #caf0f8;
        margin-right: auto;
        margin-left: 0;
        max-width: 85%;
        box-shadow: 0 4px 12px rgba(15,52,96,0.4);
    }
    
    .message-avatar {
        font-size: 0.7rem;
        margin-bottom: 0.3rem;
        font-weight: 600;
        opacity: 0.9;
    }
    
    .user-message .message-avatar {
        color: #e6f4ff;
    }
    
    .assistant-message .message-avatar {
        color: #00b4d8;
    }
    
    .message-content {
        line-height: 1.7;
        font-size: 0.9rem;
    }
    
    /* Chat input */
    .stChatInput { 
        border: 2px solid #0077b6 !important; 
        border-radius: 12px !important; 
        background: #16213e !important;
    }
    
    .stChatInput input {
        color: #caf0f8 !important;
        font-size: 0.95rem !important;
        background: #16213e !important;
    }
    
    .stChatInput input::placeholder {
        color: #4a7c9c !important;
    }
    
    .stChatInput button {
        background: linear-gradient(135deg, #0077b6 0%, #00b4d8 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
        font-size: 0.9rem !important;
        font-weight: 600 !important;
    }
    
    .stChatInput button:hover {
        background: linear-gradient(135deg, #00b4d8 0%, #90e0ef 100%) !important;
    }
    
    /* File uploader */
    .stFileUploader {
        background: #1a0f3d;
        border: 2px dashed #3d2472;
        border-radius: 10px;
        padding: 1rem;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: #16213e;
        border: 1px solid #0077b6;
        border-radius: 8px;
        color: #90e0ef;
        padding: 0.6rem 0.9rem;
        font-size: 0.85rem;
    }
    
    .streamlit-expanderHeader:hover {
        background: #1a2a4e;
        border-color: #00b4d8;
    }
    
    .streamlit-expanderContent {
        background: #0f1f3e;
        border: 1px solid #0f3460;
        border-top: none;
        color: #caf0f8;
        padding: 0.9rem;
    }
    
    /* Messages */
    .stSuccess {
        background: rgba(0,180,216,0.15);
        border: 1px solid rgba(0,180,216,0.4);
        color: #00b4d8;
        border-radius: 8px;
    }
    
    .stError {
        background: rgba(239,68,68,0.15);
        border: 1px solid rgba(239,68,68,0.4);
        color: #ef4444;
        border-radius: 8px;
    }
    
    .stInfo {
        background: rgba(144,224,239,0.15);
        border: 1px solid rgba(144,224,239,0.4);
        color: #90e0ef;
        border-radius: 8px;
    }
    
    /* Spinner */
    .stSpinner > div {
        border-color: #00b4d8 transparent transparent transparent !important;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #0a0a0a;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #0077b6;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #00b4d8;
    }
    
    hr {
        border-color: #0f3460;
        margin: 1rem 0;
    }
    
    /* Hide default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)


class EnhancedARGOChatbot:
    def __init__(self):
        self.mistral_api_key = os.getenv("MISTRAL_API_KEY")
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_client = Groq(api_key=self.groq_api_key) if self.groq_api_key else None
    
    def load_argo_data(self, json_path="Datasetjson"):
        """Load all ARGO JSON files"""
        json_files = []
        data_path = Path(json_path)
        
        if data_path.exists():
            json_files = list(data_path.rglob("*.json"))
        
        argo_data = []
        for file_path in json_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    data['_file_path'] = str(file_path)
                    argo_data.append(data)
            except Exception:
                continue
        
        return argo_data
    
    def query_mistral_streaming(self, prompt, context):
        """Query Mistral API with streaming"""
        try:
            system_prompt = """You are an expert oceanographer analyzing REAL ARGO float data from Indian Ocean regions.






CRITICAL RULES:
1. Use ONLY data from the provided context - NEVER fabricate data
2. When data is NOT available for the requested date/region/parameter:
   - Clearly state: "No data available for [specific request]"
   - Suggest alternatives: "Available data for nearby periods: [list actual dates]"
   - DO NOT use placeholder values like X.XX or Y.YY
3. NEVER invent comparison tables with missing data

RESPONSE FORMAT:

For MISSING DATA queries:
**Query Summary**

[User's question]

**Data Availability**

❌ No data found for: [specific date/region/parameter]

✅ Available alternatives:
* [Nearby date 1]: [Region] - [Parameters available]
* [Nearby date 2]: [Region] - [Parameters available]

**Suggestion**

Try querying: "[suggested alternative query]"

For COMPARISON queries with COMPLETE data:
**Query Summary**

Comparing [Parameter] between [Year1] and [Year2]

**Comparison Table**

| Parameter | [Year1] | [Year2] | Difference |
|-----------|---------|---------|------------|
| Salinity Mean | 32.15 PSU | 33.42 PSU | +1.27 PSU |

**Analysis**

* [Key observation 1 with REAL numbers]
* [Key observation 2 with REAL numbers]

For SUMMARY queries with COMPLETE data:

**Query Summary**

[Question]

**Profile Overview**

* Date: [Actual date from data]
* Location: [Actual coordinates]
* Region: [Actual region names]

**Measurements**

* Temperature: Min [X]°C, Max [Y]°C, Mean [Z]°C
* Salinity: Min [X] PSU, Max [Y] PSU, Mean [Z] PSU
* Depth: 0 to [Max]m

**Key Findings**

* [Finding 1 with specific values]
* [Finding 2 with specific values]

GEOGRAPHIC BOUNDARIES:
- If user asks about Delhi, Mumbai, or non-coastal cities: "This system contains only ocean data. [City] is not in our dataset."
- If user asks about Atlantic/Pacific: "This system focuses on Indian Ocean regions only."

Be scientifically accurate and honest about data limitations."""






            data = {
                "model": "open-mistral-7b",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"REAL DATA: {context}\n\nQUESTION: {prompt}"}
                ],
                "temperature": 0.3,
                "max_tokens": 1000,
                "stream": True
            }
            
            response = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.mistral_api_key}",
                    "Content-Type": "application/json"
                },
                json=data,
                timeout=30,
                stream=True
            )
            
            if response.status_code == 200:
                return response
            else:
                raise Exception(f"API error: {response.status_code}")
                
        except Exception:
            return None
    
    def query_groq(self, prompt, context):
        """Query Groq API as fallback"""
        try:
            if not self.groq_client:
                return "AI services unavailable. Please check your API keys."
            
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are an oceanographer analyzing REAL ARGO data. Be concise, use bullet points, and provide specific values."},
                    {"role": "user", "content": f"REAL DATA: {context}\n\nQUESTION: {prompt}"}
                ],
                temperature=0.3,
                max_tokens=800
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error: {str(e)}"
        







    
    def _month_to_number(self, month_str):
        """Convert month name to number"""
        months_map = {
            'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
            'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6,
            'july': 7, 'jul': 7, 'august': 8, 'aug': 8, 'september': 9, 'sep': 9,
            'october': 10, 'oct': 10, 'november': 11, 'nov': 11, 'december': 12, 'dec': 12
        }
        return months_map.get(month_str.lower(), 1)
    
    def search_relevant_data(self, query, argo_data):
        """Search relevant profiles with flexible temporal matching including specific dates"""
        query_lower = query.lower()
        relevant_profiles = []
        
        # Extract years from query
        years_in_query = re.findall(r'\b(20\d{2})\b', query)
        
        # Extract specific dates (e.g., "15 aug 2023", "august 15 2023", "2023-08-15")
        date_patterns = [
            r'(\d{1,2})\s+(january|jan|february|feb|march|mar|april|apr|may|june|jun|july|jul|august|aug|september|sep|october|oct|november|nov|december|dec)\s+(20\d{2})',
            r'(january|jan|february|feb|march|mar|april|apr|may|june|jun|july|jul|august|aug|september|sep|october|oct|november|nov|december|dec)\s+(\d{1,2})\s+(20\d{2})',
            r'(20\d{2})-(\d{1,2})-(\d{1,2})'
        ]
        
        specific_date = None
        for pattern in date_patterns:
            match = re.search(pattern, query_lower)
            if match:
                groups = match.groups()
                if len(groups) == 3:
                    if groups[0].isdigit() and len(groups[0]) == 4:  # ISO format
                        year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                    elif groups[2].startswith('20'):  # Day Month Year
                        day, month_str, year = int(groups[0]), groups[1], int(groups[2])
                        month = self._month_to_number(month_str)
                    else:  # Month Day Year
                        month_str, day, year = groups[0], int(groups[1]), int(groups[2])
                        month = self._month_to_number(month_str)
                    
                    specific_date = {'year': year, 'month': month, 'day': day}
                    break
        
        # Month extraction
        months_map = {
            'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
            'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6,
            'july': 7, 'jul': 7, 'august': 8, 'aug': 8, 'september': 9, 'sep': 9,
            'october': 10, 'oct': 10, 'november': 11, 'nov': 11, 'december': 12, 'dec': 12
        }
        
        months_in_query = []
        if not specific_date:
            for month_name, month_num in months_map.items():
                if month_name in query_lower:
                    months_in_query.append(month_num)
        
        # Handle "last X months" queries
        last_months_match = re.search(r'last\s+(\d+)\s+months?', query_lower)
        if last_months_match:
            num_months = int(last_months_match.group(1))
            if years_in_query:
                months_in_query = list(range(max(1, 13 - num_months), 13))
        
        is_generic_query = any(keyword in query_lower for keyword in 
                              ['summary', 'overview', 'tell me about', 'show me', 
                               'uploaded', 'this file', 'analyze', 'what is'])
        
        for profile in argo_data:
            relevance_score = 0
            
            try:
                temporal = profile.get('temporal', {})
                spatial = profile.get('geospatial', {})
                measurements = profile.get('measurements', {})
                
                profile_year = temporal.get('year')
                profile_month = temporal.get('month')
                profile_day = temporal.get('day')
                
                # Uploaded file priority
                if is_generic_query and profile.get('_is_uploaded'):
                    relevance_score += 10
                
                # SPECIFIC DATE MATCHING (highest priority)
                if specific_date:
                    if (profile_year == specific_date['year'] and 
                        profile_month == specific_date['month']):
                        
                        # Exact day match
                        if profile_day == specific_date['day']:
                            relevance_score += 20
                        # Within ±3 days
                        elif profile_day and abs(profile_day - specific_date['day']) <= 3:
                            relevance_score += 15
                        # Within ±7 days
                        elif profile_day and abs(profile_day - specific_date['day']) <= 7:
                            relevance_score += 10
                        # Same month, any day
                        else:
                            relevance_score += 8
                
                # Year matching
                elif years_in_query:
                    if str(profile_year) in years_in_query:
                        relevance_score += 10
                        
                        # Month matching with flexible range
                        if months_in_query:
                            if profile_month in months_in_query:
                                relevance_score += 8
                            # FLEXIBLE: If exact month not found, use ±1 month range
                            elif any(abs(profile_month - m) <= 1 for m in months_in_query):
                                relevance_score += 5
                        else:
                            relevance_score += 5
                
                # Region matching
                regions = spatial.get('regional_seas', [])
                for region in regions:
                    region_clean = region.lower().replace('_', ' ')
                    if region_clean in query_lower:
                        relevance_score += 5
                
                # Parameter matching
                if 'temperature' in query_lower or 'temp' in query_lower:
                    if measurements.get('core_variables', {}).get('TEMP', {}).get('present'):
                        relevance_score += 3
                
                if 'salinity' in query_lower or 'salt' in query_lower or 'psal' in query_lower:
                    if measurements.get('core_variables', {}).get('PSAL', {}).get('present'):
                        relevance_score += 3
                
                if 'oxygen' in query_lower or 'doxy' in query_lower:
                    if measurements.get('core_variables', {}).get('DOXY', {}).get('present'):
                        relevance_score += 3
                
                if 'chlorophyll' in query_lower or 'chla' in query_lower:
                    if measurements.get('bgc_variables', {}).get('CHLA', {}).get('present'):
                        relevance_score += 3
                
                if 'pressure' in query_lower or 'depth' in query_lower or 'pres' in query_lower:
                    if measurements.get('core_variables', {}).get('PRES', {}).get('present'):
                        relevance_score += 3
                
                # Fallback: any data with measurements
                if relevance_score == 0:
                    if measurements.get('core_variables', {}).get('TEMP', {}).get('present'):
                        relevance_score = 1
                        
            except Exception:
                continue
                
            if relevance_score > 0:
                relevant_profiles.append((profile, relevance_score))
        
        relevant_profiles.sort(key=lambda x: x[1], reverse=True)
        
        # If no results with strict matching, broaden the search
        if not relevant_profiles and (years_in_query or months_in_query or specific_date):
            if specific_date:
                st.info(f"🔍 No data for exact date {specific_date['day']}/{specific_date['month']}/{specific_date['year']}. Searching {specific_date['year']}-{specific_date['month']:02d} (±7 days)...")
            else:
                st.info(f"🔍 Expanding search to nearby months/regions...")
            return self.search_relevant_data_flexible(query, argo_data, years_in_query, months_in_query, specific_date)
        
        return [profile[0] for profile in relevant_profiles[:15]]
    
    def search_relevant_data_flexible(self, query, argo_data, years, months, specific_date=None):
        """Fallback search with expanded temporal range"""
        relevant_profiles = []
        query_lower = query.lower()
        
        for profile in argo_data:
            relevance_score = 0
            
            try:
                temporal = profile.get('temporal', {})
                spatial = profile.get('geospatial', {})
                measurements = profile.get('measurements', {})
                
                profile_year = temporal.get('year')
                profile_month = temporal.get('month')
                profile_day = temporal.get('day')
                
                # Expanded date matching (±14 days)
                if specific_date:
                    if profile_year == specific_date['year']:
                        relevance_score += 6
                        
                        if profile_month == specific_date['month']:
                            relevance_score += 8
                            
                            # Within ±14 days
                            if profile_day and abs(profile_day - specific_date['day']) <= 14:
                                relevance_score += 10
                        # Adjacent months
                        elif profile_month and abs(profile_month - specific_date['month']) <= 1:
                            relevance_score += 4
                
                # Expanded year matching (±1 year)
                elif years:
                    target_years = [int(y) for y in years]
                    if profile_year in target_years:
                        relevance_score += 8
                    elif any(abs(profile_year - y) <= 1 for y in target_years):
                        relevance_score += 4
                
                # Expanded month matching (±2 months)
                if months:
                    if profile_month in months:
                        relevance_score += 6
                    elif any(abs(profile_month - m) <= 2 for m in months):
                        relevance_score += 3
                
                # Region matching
                regions = spatial.get('regional_seas', [])
                for region in regions:
                    if region.lower().replace('_', ' ') in query_lower:
                        relevance_score += 4
                
                # Parameter matching
                if 'temperature' in query_lower or 'salinity' in query_lower or 'analysis' in query_lower:
                    if measurements.get('core_variables', {}).get('TEMP', {}).get('present'):
                        relevance_score += 2
                    if measurements.get('core_variables', {}).get('PSAL', {}).get('present'):
                        relevance_score += 2
                        
            except Exception:
                continue
                
            if relevance_score > 0:
                relevant_profiles.append((profile, relevance_score))
        
        relevant_profiles.sort(key=lambda x: x[1], reverse=True)
        return [profile[0] for profile in relevant_profiles[:15]]
    
    def create_context_summary(self, profiles, query):
        """Create context summary with temporal flexibility"""
        if not profiles:
            return "No relevant data found in the specified time period."
        
        context_parts = []
        query_lower = query.lower()
        
        # Group profiles by year and month
        profiles_by_time = defaultdict(list)
        for profile in profiles:
            year = profile.get('temporal', {}).get('year')
            month = profile.get('temporal', {}).get('month')
            if year and month:
                profiles_by_time[f"{year}-{month:02d}"].append(profile)
        
        # Show temporal range in response
        # Show temporal range in response
        if len(profiles_by_time) > 1:
            time_keys = sorted(profiles_by_time.keys())
            context_parts.append(f"TEMPORAL RANGE: {time_keys[0]} to {time_keys[-1]} ({len(profiles)} profiles)")
        
        years_in_query = re.findall(r'\b(20\d{2})\b', query)
        is_summary = any(keyword in query_lower for keyword in ['summary', 'overview', 'tell me', 'analyze', 'analysis'])
        is_comparison = any(keyword in query_lower for keyword in ['compare', 'difference', 'vs', 'versus'])
        
        if is_comparison and years_in_query:
            profiles_by_year = {}
            for profile in profiles:
                year = profile.get('temporal', {}).get('year')
                if str(year) in years_in_query:
                    if year not in profiles_by_year:
                        profiles_by_year[year] = []
                    profiles_by_year[year].append(profile)
            
            for year in sorted(profiles_by_year.keys()):
                year_profiles = profiles_by_year[year]
                for profile in year_profiles[:3]:
                    temporal = profile.get('temporal', {})
                    spatial = profile.get('geospatial', {})
                    measurements = profile.get('measurements', {})
                    
                    date = temporal.get('datetime', 'unknown')[:10]
                    regions = ', '.join(spatial.get('regional_seas', ['Ocean']))
                    
                    info = f"REAL DATA [{year}] - Profile {date} from {regions}"
                    
                    if profile.get('_uploaded_filename'):
                        info += f" (File: {profile['_uploaded_filename']})"
                    
                    core_vars = measurements.get('core_variables', {})
                    
                    if 'temperature' in query_lower or 'temp' in query_lower or is_summary:
                        temp_data = core_vars.get('TEMP', {})
                        if temp_data.get('present'):
                            stats = temp_data.get('statistics', {})
                            info += f" | TEMP: {stats.get('min', 0):.2f}-{stats.get('max', 0):.2f}°C (mean: {stats.get('mean', 0):.2f}°C)"
                    
                    if 'salinity' in query_lower or 'salt' in query_lower or is_summary:
                        sal_data = core_vars.get('PSAL', {})
                        if sal_data.get('present'):
                            stats = sal_data.get('statistics', {})
                            info += f" | SAL: {stats.get('min', 0):.2f}-{stats.get('max', 0):.2f} PSU (mean: {stats.get('mean', 0):.2f} PSU)"
                    
                    pres_data = core_vars.get('PRES', {})
                    if pres_data.get('present') and is_summary:
                        stats = pres_data.get('statistics', {})
                        info += f" | DEPTH: 0-{stats.get('max', 0):.0f}m"
                    
                    context_parts.append(info)
        else:
            for profile in profiles[:10]:
                temporal = profile.get('temporal', {})
                spatial = profile.get('geospatial', {})
                measurements = profile.get('measurements', {})
                
                date = temporal.get('datetime', 'unknown')[:10]
                year = temporal.get('year')
                month = temporal.get('month')
                day = temporal.get('day')
                regions = ', '.join(spatial.get('regional_seas', ['Ocean']))
                
                info = f"REAL DATA [{year}-{month:02d}-{day:02d}] - Profile {date} from {regions}"
                
                if profile.get('_uploaded_filename'):
                    info += f" (File: {profile['_uploaded_filename']})"
                
                core_vars = measurements.get('core_variables', {})
                
                # Add temperature data
                temp_data = core_vars.get('TEMP', {})
                if temp_data.get('present'):
                    stats = temp_data.get('statistics', {})
                    info += f" | TEMP: {stats.get('min', 0):.2f}-{stats.get('max', 0):.2f}°C (mean: {stats.get('mean', 0):.2f}°C)"
                
                # Add salinity data
                sal_data = core_vars.get('PSAL', {})
                if sal_data.get('present'):
                    stats = sal_data.get('statistics', {})
                    info += f" | SAL: {stats.get('min', 0):.2f}-{stats.get('max', 0):.2f} PSU (mean: {stats.get('mean', 0):.2f} PSU)"
                
                # Add depth data
                pres_data = core_vars.get('PRES', {})
                if pres_data.get('present'):
                    stats = pres_data.get('statistics', {})
                    info += f" | DEPTH: 0-{stats.get('max', 0):.0f}m"
                
                context_parts.append(info)
        
        return " || ".join(context_parts)


def display_message(role, content):
    """Display chat message"""
    if role == "user":
        st.markdown(f"""
        <div class="chat-message user-message">
            <div class="message-avatar">You</div>
            <div class="message-content">{content}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="chat-message assistant-message">
            <div class="message-avatar">FloatChat AI</div>
            <div class="message-content">{content}</div>
        </div>
        """, unsafe_allow_html=True)


def main():
    inject_custom_css()
    
    # Initialize session state
    if 'chatbot' not in st.session_state:
        st.session_state.chatbot = EnhancedARGOChatbot()
        st.session_state.messages = []
        st.session_state.argo_data = None
        st.session_state.history = []
        st.session_state.uploaded_files = []
        st.session_state.last_profiles = None
        st.session_state.last_query = ""
        st.session_state.active_file = None
        st.session_state.processing = False
    
    chatbot = st.session_state.chatbot
    
    # Sidebar
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 1.2rem; background: linear-gradient(135deg, #0077b6 0%, #00b4d8 100%); border-radius: 12px; margin-bottom: 1rem; box-shadow: 0 4px 15px rgba(0, 119, 182, 0.4); border: 2px solid #0096c7;">
            <div style="font-size: 2.8rem;">🌊</div>
            <h3 style="margin: 0.3rem 0 0 0; color: white; font-size: 1.4rem; font-weight: 700;">FloatChat AI</h3>
            <p style="color: rgba(255,255,255,0.95); font-size: 0.75rem; margin: 0.2rem 0 0 0; font-weight: 500;">ARGO Data Assistant</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Navigation
        # st.markdown("### Navigation")
        # map_path = Path("pages/1map.py")
        # if map_path.exists():
        #     if st.button("🗺️ Visualizations & Maps", use_container_width=True, key="nav_viz"):
        #         st.switch_page("pages/1map.py")
        # else:
        #     st.warning("Map page not found")
        
        st.markdown("---")
        
        st.markdown("### Export Options")
        
        profiles = st.session_state.get('last_profiles', [])
        query = st.session_state.get('last_query', '')
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📄 ASCII", use_container_width=True, disabled=not profiles, key="btn_ascii"):
                filename = export_ascii(profiles, query)
                with open(filename, 'rb') as f:
                    st.download_button("Download", f, file_name=Path(filename).name, mime="text/plain", use_container_width=True, key="down_ascii")
            
            if st.button("📊 CSV", use_container_width=True, disabled=not profiles, key="btn_csv"):
                filename = export_csv(profiles, query)
                with open(filename, 'rb') as f:
                    st.download_button("Download", f, file_name=Path(filename).name, mime="text/csv", use_container_width=True, key="down_csv")
        
        with col2:
            if st.button("📦 JSON", use_container_width=True, disabled=not profiles, key="btn_json"):
                filename = export_json(profiles, query)
                with open(filename, 'rb') as f:
                    st.download_button("Download", f, file_name=Path(filename).name, mime="application/json", use_container_width=True, key="down_json")
            
            if st.button("🌐 NetCDF", use_container_width=True, disabled=not profiles, key="btn_netcdf"):
                filename = export_netcdf(profiles, query)
                with open(filename, 'rb') as f:
                    st.download_button("Download", f, file_name=Path(filename).name, mime="application/x-netcdf", use_container_width=True, key="down_nc")
        
        st.markdown("---")
        
        st.markdown("### Upload Data")
        uploaded_file = st.file_uploader("Upload NetCDF", type=['nc'], label_visibility="collapsed", key="file_uploader")
        
        if uploaded_file and uploaded_file.name not in [f.get('_uploaded_filename') for f in st.session_state.uploaded_files]:
            with st.spinner("Processing..."):
                try:
                    converted_data = convert_nc_to_json(uploaded_file)
                    if converted_data:
                        converted_data['_uploaded_filename'] = uploaded_file.name
                        converted_data['_upload_timestamp'] = datetime.now().isoformat()
                        converted_data['_is_uploaded'] = True
                        st.session_state.uploaded_files.append(converted_data)
                        st.session_state.active_file = uploaded_file.name
                        st.success(f"✅ {uploaded_file.name[:25]}...")
                        st.rerun()
                except Exception as e:
                    st.error(f"Failed: {str(e)}")
        
        st.markdown("---")
        
        st.markdown("### History")
        if st.session_state.history:
            for i, item in enumerate(reversed(st.session_state.history[-6:])):
                if st.button(f"{item[:28]}...", key=f"hist_{i}", use_container_width=True):
                    st.session_state.quick_query = item
                    st.rerun()
        else:
            st.caption("No history")
        
        if st.button("🗑️ Clear", use_container_width=True, key="btn_clear"):
            st.session_state.history = []
            st.session_state.messages = []
            st.rerun()
        
        st.markdown("---")
        
        st.markdown("### Stats")
        if st.session_state.argo_data:
            st.markdown(f"""
            <div style="font-size: 0.85rem; color: #90e0ef;">
                <div style="margin-bottom: 0.4rem;">📁 {len(st.session_state.argo_data)} Profiles</div>
                <div style="margin-bottom: 0.4rem;">📤 {len(st.session_state.uploaded_files)} Uploaded</div>
                <div style="margin-bottom: 0.4rem;">📅 {len(set(p.get('temporal', {}).get('year') for p in st.session_state.argo_data if p.get('temporal', {}).get('year')))} Years</div>
                <div style="margin-bottom: 0.4rem;">🌍 {len(set([r for p in st.session_state.argo_data for r in p.get('geospatial', {}).get('regional_seas', [])]))} Regions</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### About")
        st.markdown("""
        <div style="font-size: 0.8rem; color: #4a7c9c; line-height: 1.5;">
        <strong style="color: #00b4d8;">FloatChat AI</strong><br>
        SIH 2025 PS 25040<br>
        MoES | INCOIS
        </div>
        """, unsafe_allow_html=True)
    
    # Load data
    if st.session_state.argo_data is None:
        with st.spinner("Loading ARGO data..."):
            st.session_state.argo_data = chatbot.load_argo_data()
    
    argo_data = st.session_state.argo_data + st.session_state.uploaded_files
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>FloatChat AI</h1>
        <p>Intelligent ARGO Ocean Data Assistant</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Chat messages
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    for message in st.session_state.messages:
        display_message(message["role"], message["content"])
    
    if st.session_state.get('active_file'):
        col_info, col_btn = st.columns([5, 1])
        with col_info:
            st.info(f"📁 Active: {st.session_state.active_file}")
        with col_btn:
            if st.button("❌", key="btn_remove_file"):
                st.session_state.active_file = None
                st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Compact chat input
    user_query = st.chat_input("Ask about temperature, salinity, regions, or water masses...")
    
    if user_query and not st.session_state.processing:
        st.session_state.messages.append({"role": "user", "content": user_query})
        st.session_state.history.append(user_query)
        st.session_state.last_query = user_query
        st.session_state.processing = True
        st.rerun()
    
    # Process AI response
    if st.session_state.processing:
        last_user_message = st.session_state.messages[-1]["content"]
        
        with st.spinner("Analyzing..."):
            if st.session_state.get('active_file'):
                active_file_data = [f for f in st.session_state.uploaded_files 
                                   if f.get('_uploaded_filename') == st.session_state.active_file]
                
                if active_file_data:
                    relevant_profiles = chatbot.search_relevant_data(last_user_message, active_file_data)
                    
                    if relevant_profiles:
                        context = f"Data from '{st.session_state.active_file}': " + chatbot.create_context_summary(relevant_profiles, last_user_message)
                    else:
                        relevant_profiles = []
                        context = f"No data matching query in '{st.session_state.active_file}'"
                else:
                    relevant_profiles = chatbot.search_relevant_data(last_user_message, argo_data)
                    context = chatbot.create_context_summary(relevant_profiles, last_user_message)
            else:
                relevant_profiles = chatbot.search_relevant_data(last_user_message, argo_data)
                context = chatbot.create_context_summary(relevant_profiles, last_user_message)
            
            if relevant_profiles:
                st.session_state.last_profiles = relevant_profiles
                
                streaming_response = chatbot.query_mistral_streaming(last_user_message, context)
                
                if streaming_response:
                    response_placeholder = st.empty()
                    full_response = ""
                    
                    for line in streaming_response.iter_lines():
                        if line:
                            try:
                                line_text = line.decode('utf-8')
                                if line_text.startswith('data: '):
                                    json_str = line_text[6:]
                                    if json_str.strip() != '[DONE]':
                                        data = json.loads(json_str)
                                        if 'choices' in data:
                                            delta = data['choices'][0].get('delta', {})
                                            content = delta.get('content', '')
                                            if content:
                                                full_response += content
                                                response_placeholder.markdown(f"""
                                                <div class="chat-message assistant-message">
                                                    <div class="message-avatar">FloatChat AI</div>
                                                    <div class="message-content">{full_response}▋</div>
                                                </div>
                                                """, unsafe_allow_html=True)
                            except:
                                continue
                    
                    response_placeholder.markdown(f"""
                    <div class="chat-message assistant-message">
                        <div class="message-avatar">FloatChat AI</div>
                        <div class="message-content">{full_response}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                else:
                    response = chatbot.query_groq(last_user_message, context)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                
                # Show source data
                with st.expander("📊 View source data"):
                    for i, profile in enumerate(relevant_profiles, 1):
                        temporal = profile.get('temporal', {})
                        spatial = profile.get('geospatial', {})
                        meas = profile.get('measurements', {}).get('core_variables', {})
                        
                        st.markdown(f"**Profile {i}:**")
                        st.caption(f"📅 {temporal.get('datetime', '')[:10]}")
                        st.caption(f"🌍 {', '.join(spatial.get('regional_seas', ['Unknown']))}")
                        
                        if profile.get('_uploaded_filename'):
                            st.caption(f"📁 {profile['_uploaded_filename']}")
                        
                        if meas.get('TEMP', {}).get('present'):
                            temp_stats = meas['TEMP']['statistics']
                            st.caption(f"🌡️ {temp_stats.get('min', 0):.2f}-{temp_stats.get('max', 0):.2f}°C")
                        if meas.get('PSAL', {}).get('present'):
                            sal_stats = meas['PSAL']['statistics']
                            st.caption(f"🧂 {sal_stats.get('min', 0):.2f}-{sal_stats.get('max', 0):.2f} PSU")
            else:
                error_msg = "No relevant data found. Try specific regions, years, or parameters."
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
        
        st.session_state.processing = False
        st.rerun()


if __name__ == "__main__":
    main()


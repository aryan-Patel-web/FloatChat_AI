import streamlit as st
import json
import os
from pathlib import Path
import pandas as pd
import numpy as np
import requests
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

# ChatGPT-style CSS with fixed input at bottom
def inject_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background: #1a1a1a;
    }
    
    /* Main container with bottom padding for fixed input */
    .main .block-container {
        padding: 0 !important;
        max-width: 100% !important;
        padding-bottom: 100px !important;
    }
    
    /* Header styling */
    .main-header {
        background: #1a1a1a;
        padding: 1rem 2rem;
        border-bottom: 1px solid #2a2a2a;
        position: sticky;
        top: 0;
        z-index: 100;
        text-align: center;
    }
    
    .main-header h1 {
        color: #ececec;
        font-size: 1.25rem;
        font-weight: 600;
        margin: 0;
    }
    
    .main-header p {
        color: #8e8e8e;
        font-size: 0.875rem;
        margin: 0.25rem 0 0 0;
    }
    
    /* Chat messages container */
    .chat-container {
        max-width: 900px;
        margin: 0 auto;
        padding: 2rem 1rem;
    }
    
    .chat-message {
        padding: 0.75rem 1rem;
        margin-bottom: 1rem;
        border-radius: 16px;
        animation: fadeIn 0.3s ease-out;
        width: fit-content;
        max-width: 65%;
    }
    
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* User message - compact, right-aligned, dark green */
    .user-message {
        background: #1a472a;
        border: 1px solid #1f5633;
        color: #ececec;
        margin-left: auto;
        margin-right: 0;
        max-width: 60%;
    }
    
    /* AI message - left-aligned */
    .assistant-message {
        background: #2a2a2a;
        border: 1px solid #3a3a3a;
        color: #d1d1d1;
        margin-right: auto;
        margin-left: 0;
        max-width: 85%;
    }
    
    .message-avatar {
        font-size: 0.7rem;
        margin-bottom: 0.25rem;
        font-weight: 600;
    }
    
    .user-message .message-avatar {
        color: #10b981;
    }
    
    .assistant-message .message-avatar {
        color: #0099cc;
    }
    
    .message-content {
        line-height: 1.6;
        font-size: 0.875rem;
    }
    
                





                
    /* ChatGPT-style fixed input - CRITICAL FIX */
    div[data-testid="column"] {
        padding: 0 !important;
    }
    
    /* Fixed container at bottom */
    .main > div:last-child {
        position: fixed !important;
        bottom: 0 !important;
        left: 320px !important;
        right: 0 !important;
        background: #1a1a1a !important;
        border-top: 1px solid #2a2a2a !important;
        padding: 0.75rem 2rem !important;
        z-index: 1000 !important;
    }
    
    /* Input styling */
    .stTextInput {
        margin: 0 !important;
    }
    
    .stTextInput > div {
        margin: 0 !important;
    }
    
    .stTextInput > div > div {
        margin: 0 !important;
    }
    
    .stTextInput input {
        background: #2a2a2a !important;
        border: 1px solid #3a3a3a !important;
        border-radius: 12px !important;
        color: #ececec !important;
        padding: 0.5rem 0.875rem !important;
        font-size: 0.875rem !important;
        transition: all 0.15s ease !important;
        height: 44px !important;
    }
    
    .stTextInput input:focus {
        background: #2f2f2f !important;
        border-color: #565656 !important;
        box-shadow: 0 0 0 1px rgba(86, 86, 86, 0.3) !important;
        outline: none !important;
    }
    
    .stTextInput input::placeholder {
        color: #6a6a6a !important;
    }
    
                



                
    /* Send button - compact and visible */
    .stButton button {
        background: #2a2a2a !important;
        color: #ececec !important;
        border: 1px solid #3a3a3a !important;
        border-radius: 10px !important;
        padding: 0 !important;
        font-weight: 500 !important;
        font-size: 1.1rem !important;
        transition: all 0.15s ease !important;
        cursor: pointer !important;
        width: 45px !important;
        height: 44px !important;
        min-width: 45px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    
    .stButton button:hover {
        background: #3a3a3a !important;
        border-color: #4a4a4a !important;
    }
    
    .stButton button:active {
        transform: scale(0.95) !important;
    }
                
    
 /* === Sidebar Styling === */
                

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1e1e1e, #161616);
    border-right: 1px solid #2a2a2a;
    padding-top: 1rem;
}

/* Sidebar content spacing */
section[data-testid="stSidebar"] > div {
    background: transparent;
    padding: 1.5rem 1.25rem;
}

/* Sidebar text */
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] p {
    color: #f2f2f2 !important;
    font-family: "Segoe UI", Roboto, sans-serif !important;
    line-height: 1.4;
}

/* === Sidebar Buttons === */
section[data-testid="stSidebar"] .stButton button {
    background: linear-gradient(145deg, #2b2b2b, #232323) !important;
    color: #e0e0e0 !important;
    border: 1px solid #3c3c3c !important;
    border-radius: 10px !important;
    padding: 0.6rem 1rem !important;
    font-size: 0.9rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.5px !important;
    transition: all 0.2s ease-in-out !important;
    box-shadow: 0px 2px 6px rgba(0,0,0,0.4) !important;
    margin-bottom: 0.75rem !important;
    width: 100% !important; /* Makes all buttons same width */
}

/* Hover effect */
section[data-testid="stSidebar"] .stButton button:hover {
    background: linear-gradient(145deg, #3c3c3c, #2b2b2b) !important;
    border-color: #5a5a5a !important;
    color: #ffffff !important;
    transform: translateY(-2px) !important;
    box-shadow: 0px 4px 10px rgba(0,0,0,0.6) !important;
}

                








    /* File uploader */
    .stFileUploader {
        background: #2a2a2a;
        border: 2px dashed #3a3a3a;
        border-radius: 12px;
        padding: 1rem;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: #2a2a2a;
        border: 1px solid #3a3a3a;
        border-radius: 8px;
        color: #ececec;
        padding: 0.6rem 0.875rem;
        font-size: 0.875rem;
    }
    
    .streamlit-expanderHeader:hover {
        background: #2f2f2f;
        border-color: #0099cc;
    }
    
    .streamlit-expanderContent {
        background: #1e1e1e;
        border: 1px solid #2a2a2a;
        border-top: none;
        color: #d1d1d1;
        padding: 0.875rem;
    }
    
    /* Messages */
    .stSuccess {
        background: rgba(0, 153, 204, 0.1);
        border: 1px solid rgba(0, 153, 204, 0.3);
        color: #0099cc;
        border-radius: 8px;
        font-size: 0.85rem;
        padding: 0.5rem 0.75rem;
    }
    
    .stError {
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.3);
        color: #ef4444;
        border-radius: 8px;
        font-size: 0.85rem;
        padding: 0.5rem 0.75rem;
    }
    
    /* Spinner */
    .stSpinner > div {
        border-color: #0099cc transparent transparent transparent !important;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #1a1a1a;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #3a3a3a;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #4a4a4a;
    }
    
    hr {
        border-color: #2a2a2a;
        margin: 1rem 0;
    }
    
    /* Hide default streamlit elements */
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
        """Query Mistral API with enhanced context-aware streaming"""
        try:
            system_prompt = """You are an expert oceanographer analyzing REAL ARGO float data from Indian Ocean regions.

CRITICAL RULES:
1. Use ONLY data from the provided context - NEVER fabricate data
2. If asked to compare dates/periods NOT in context, respond: "Data for [date] not available. I can only analyze: [list available dates from context]"
3. NEVER invent comparison tables or fake historical data
4. For single profiles, state: "Only one profile available, comparison requires multiple time periods"

GEOGRAPHIC INTELLIGENCE:
- West Bengal coast → Bay of Bengal data
- Tamil Nadu coast → Bay of Bengal data  
- Kerala/Karnataka coast → Arabian Sea data
- Mumbai/Gujarat coast → Arabian Sea data
- Andaman Islands → Bay of Bengal/Andaman Sea
- If user asks about landlocked areas, respond: "This is a landlocked region. Please specify coastal areas or ocean regions"
- If location outside Indian Ocean domain, respond: "Data limited to Indian Ocean region. Try: Arabian Sea, Bay of Bengal, Southern Ocean, or Equatorial Indian Ocean"

ABBREVIATIONS & SYNONYMS:
- Temperature = temp = thermal = heat = SST = sea surface temperature
- Salinity = salt = PSAL = saltiness = salinity levels
- Pressure = depth = PRES = water column
- Summary = overview = analyze = tell me about = what's in = describe
- Table = tabular = comparison table = side-by-side = versus
- Compare = difference = vs = versus = comparison = changes between

RESPONSE FORMAT (MANDATORY):

For COMPARISON queries (2022 vs 2023, difference between years, etc.):

**📋 Query Summary**
Comparing [Parameter] between [Year1] and [Year2] in [Region]

**📊 Comparison Table**

| Parameter | [Year1] | [Year2] | Difference |
|-----------|---------|---------|------------|
| Salinity Mean | X.XX PSU | Y.YY PSU | ±Z.ZZ PSU |
| Salinity Range | X.X-Y.Y PSU | A.A-B.B PSU | - |
| Temperature Mean | X.X°C | Y.Y°C | ±Z.Z°C |
| Temperature Range | X-Y°C | A-B°C | - |
| Depth Coverage | 0-Xm | 0-Ym | - |

**🔍 Analysis**
* **[Year1] Characteristics:** [Key observations]
* **[Year2] Characteristics:** [Key observations]
* **Notable Changes:** [Significant differences]
* **Trend:** [Increasing/Decreasing/Stable]

**✅ Conclusion**
[2-3 sentences summarizing the comparison and significance]

---

For SUMMARY/OVERVIEW queries:

**📋 Query Summary**
[Restate user's question in one line]

**📊 Profile Overview**
* **Date:** [Date(s)]
* **Location:** [Coordinates]
* **Region:** [Region names]
* **Source:** [Filename]

**🌡️ Measurements**
* **Temperature:** Min: [Min]°C, Max: [Max]°C (Mean: [Mean]°C, Std Dev: [Std]°C)
* **Salinity:** Min: [Min] PSU, Max: [Max] PSU (Mean: [Mean] PSU, Std Dev: [Std] PSU)
* **Pressure/Depth:** 0 to [Max]m

**🔍 Key Findings**
* [Specific finding 1]
* [Specific finding 2]
* [Specific finding 3]

**✅ Conclusion**
[1-2 sentence summary]

---

For FILE UPLOADS with missing variables:

**🌊 Variables in Your File**
* **Temperature** → ✅ Present (Range: X-Y°C) / ❌ Not available
* **Salinity** → ✅ Present (Range: X-Y PSU) / ❌ Not available  
* **Pressure** → ✅ Present (Depth: 0-Xm) / ❌ Not available
* **Other parameters** → [List if available]

---

For SPECIFIC PARAMETER queries (temp/salinity only):

**📋 Query: [Parameter] in [Region]**

**📊 Results**
* **Mean [Parameter]:** X.XX [units]
* **Range:** Min X.X to Max Y.Y [units]
* **Standard Deviation:** Z.Z [units]
* **Depth Range:** 0-Xm
* **Observation Period:** [Date range]

**🔍 Notable Patterns**
* [Pattern 1]
* [Pattern 2]

---

COMPARISON QUERY TYPES TO HANDLE:
1. **Year vs Year:** "compare 2022 vs 2023" → Show table with both years
2. **Multiple Years:** "compare 2022, 2023, 2024" → Show multi-column table
3. **Month vs Month:** "January vs July" → Monthly comparison table
4. **Region vs Region:** "Arabian Sea vs Bay of Bengal" → Regional comparison
5. **Season vs Season:** "monsoon vs winter" → Seasonal comparison
6. **Trend Analysis:** "changes over time" → Time series summary
7. **Parameter Difference:** "salinity difference between..." → Focus on one parameter
8. **Multi-parameter:** "temperature and salinity difference..." → Show both parameters

TABLE FORMAT RULES:
- Always use markdown table format with | separators
- Include units in all values (°C, PSU, m)
- Calculate actual differences (Year2 - Year1)
- Use ± for differences showing direction
- Round to 2 decimal places for precision
- If data missing for a year, state "No data available for [Year]"

CONVERSATION CONTEXT:
- Remember previous questions
- Build on conversation history for coherent dialogue
- If user says "compare that with", reference the previous query region/parameter
- If user asks "what about [Year]" after a query, add that year to comparison

QUERY HANDLING:
- Generic questions → Show ALL parameters in structured format
- Location-based → Auto-map to appropriate ocean region
- Time comparisons → Check if multiple dates exist; if not, explain limitation and show available years
- Missing data → Explicitly state what years/regions have data vs don't

CRITICAL: 
- NEVER show fake data in tables
- If comparison impossible (missing data), say: "Comparison not possible. Available data: [list what exists]"
- Always calculate real differences from context data
- Use exact values from context, never estimate

Be scientifically accurate, context-aware, and honest about limitations. ALWAYS use bullet points and tables with proper formatting."""




            data = {
                "model": "open-mistral-7b",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"REAL DATA CONTEXT: {context}\n\nUSER QUESTION: {prompt}"}
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
                    {"role": "system", "content": "You are an oceanographer analyzing REAL ARGO data. For summaries use bullet points. Be concise, honest about limitations, and use specific values."},
                    {"role": "user", "content": f"REAL DATA: {context}\n\nQUESTION: {prompt}"}
                ],
                temperature=0.3,
                max_tokens=800
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error: {str(e)}"
    
    # def search_relevant_data(self, query, argo_data):
    def search_relevant_data(self, query, argo_data):
        """Search relevant profiles"""
        query_lower = query.lower()
        relevant_profiles = []
        
        # Extract years from query
        import re
        years_in_query = re.findall(r'\b(20\d{2})\b', query)
        
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
                
                if is_generic_query and profile.get('_is_uploaded'):
                    relevance_score += 10
                
                # If specific years mentioned, match those years
                if years_in_query:
                    if str(profile_year) in years_in_query:
                        relevance_score += 10
                
                regions = spatial.get('regional_seas', [])
                for region in regions:
                    if region.lower().replace('_', ' ') in query_lower:
                        relevance_score += 5
                
                if 'temperature' in query_lower or 'temp' in query_lower:
                    if measurements.get('core_variables', {}).get('TEMP', {}).get('present'):
                        relevance_score += 3
                
                if 'salinity' in query_lower or 'salt' in query_lower:
                    if measurements.get('core_variables', {}).get('PSAL', {}).get('present'):
                        relevance_score += 3
                
                if relevance_score == 0:
                    if measurements.get('core_variables', {}).get('TEMP', {}).get('present'):
                        relevance_score = 1
                    
            except Exception:
                continue
                
            if relevance_score > 0:
                relevant_profiles.append((profile, relevance_score))
        
        relevant_profiles.sort(key=lambda x: x[1], reverse=True)
        return [profile[0] for profile in relevant_profiles[:10]]
    
    def create_context_summary(self, profiles, query):
        """Create context summary with REAL values"""
        if not profiles:
            return "No relevant data found."
        
        context_parts = []
        query_lower = query.lower()
        
        # Extract years from query for comparison
        import re
        years_in_query = re.findall(r'\b(20\d{2})\b', query)
        
        is_summary = any(keyword in query_lower for keyword in ['summary', 'overview', 'tell me', 'analyze'])
        is_comparison = any(keyword in query_lower for keyword in ['compare', 'difference', 'vs', 'versus'])
        
        # Group profiles by year if comparison query
        if is_comparison and years_in_query:
            profiles_by_year = {}
            for profile in profiles:
                year = profile.get('temporal', {}).get('year')
                if str(year) in years_in_query:
                    if year not in profiles_by_year:
                        profiles_by_year[year] = []
                    profiles_by_year[year].append(profile)
            
            # Create context for each year
            for year in sorted(profiles_by_year.keys()):
                year_profiles = profiles_by_year[year]
                for profile in year_profiles[:3]:
                    temporal = profile.get('temporal', {})
                    spatial = profile.get('geospatial', {})
                    measurements = profile.get('measurements', {})
                    
                    date = temporal.get('datetime', 'unknown')[:10]
                    regions = ', '.join(spatial.get('regional_seas', ['Ocean']))
                    
                    info = f"REAL DATA - Year {year} - Profile {date} from {regions}"
                    
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
            # Normal summary (original logic)
            for profile in profiles[:5]:
                temporal = profile.get('temporal', {})
                spatial = profile.get('geospatial', {})
                measurements = profile.get('measurements', {})
                
                date = temporal.get('datetime', 'unknown')[:10]
                regions = ', '.join(spatial.get('regional_seas', ['Ocean']))
                
                info = f"REAL DATA - Profile {date} from {regions}"
                
                if profile.get('_uploaded_filename'):
                    info += f" (File: {profile['_uploaded_filename']})"
                
                core_vars = measurements.get('core_variables', {})
                
                if is_summary:
                    temp_data = core_vars.get('TEMP', {})
                    if temp_data.get('present'):
                        stats = temp_data.get('statistics', {})
                        info += f" | TEMP: {stats.get('min', 0):.2f}-{stats.get('max', 0):.2f}°C (mean: {stats.get('mean', 0):.2f}°C)"
                    
                    sal_data = core_vars.get('PSAL', {})
                    if sal_data.get('present'):
                        stats = sal_data.get('statistics', {})
                        info += f" | SAL: {stats.get('min', 0):.2f}-{stats.get('max', 0):.2f} PSU (mean: {stats.get('mean', 0):.2f} PSU)"
                    
                    pres_data = core_vars.get('PRES', {})
                    if pres_data.get('present'):
                        stats = pres_data.get('statistics', {})
                        info += f" | DEPTH: 0-{stats.get('max', 0):.0f}m"
                else:
                    if 'temperature' in query_lower or 'temp' in query_lower:
                        temp_data = core_vars.get('TEMP', {})
                        if temp_data.get('present'):
                            stats = temp_data.get('statistics', {})
                            info += f" | TEMP: {stats.get('min', 0):.2f}-{stats.get('max', 0):.2f}°C (mean: {stats.get('mean', 0):.2f}°C)"
                    
                    if 'salinity' in query_lower or 'salt' in query_lower:
                        sal_data = core_vars.get('PSAL', {})
                        if sal_data.get('present'):
                            stats = sal_data.get('statistics', {})
                            info += f" | SAL: {stats.get('min', 0):.2f}-{stats.get('max', 0):.2f} PSU (mean: {stats.get('mean', 0):.2f} PSU)"
                
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
    st.set_page_config(
        page_title="FloatChat AI",
        page_icon="🌊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
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
        <div style="text-align: center; padding: 1.2rem; background: linear-gradient(135deg, #006994 0%, #0077be 50%, #0099cc 100%); border-radius: 12px; margin-bottom: 1rem; box-shadow: 0 4px 15px rgba(0, 105, 148, 0.3); border: 2px solid #005580;">
            <div style="font-size: 2.8rem; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));">🌊</div>
            <h3 style="margin: 0.3rem 0 0 0; color: white; font-size: 1.4rem; font-weight: 700; text-shadow: 0 2px 4px rgba(0,0,0,0.2);">FloatChat AI</h3>
            <p style="color: rgba(255,255,255,0.95); font-size: 0.75rem; margin: 0.2rem 0 0 0; font-weight: 500;">ARGO Data Assistant</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 📥 Export Options")
        
        profiles = st.session_state.get('last_profiles', [])
        query = st.session_state.get('last_query', '')
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📄 ASCII", use_container_width=True, disabled=not profiles):
                filename = export_ascii(profiles, query)
                with open(filename, 'rb') as f:
                    st.download_button("⬇️ Download", f, file_name=Path(filename).name, mime="text/plain", use_container_width=True, key="down_ascii")
            
            if st.button("📊 CSV", use_container_width=True, disabled=not profiles):
                filename = export_csv(profiles, query)
                with open(filename, 'rb') as f:
                    st.download_button("⬇️ Download", f, file_name=Path(filename).name, mime="text/csv", use_container_width=True, key="down_csv")
        
        with col2:
            if st.button("📦 JSON", use_container_width=True, disabled=not profiles):
                filename = export_json(profiles, query)
                with open(filename, 'rb') as f:
                    st.download_button("⬇️ Download", f, file_name=Path(filename).name, mime="application/json", use_container_width=True, key="down_json")
            
            if st.button("🌐 NetCDF", use_container_width=True, disabled=not profiles):
                filename = export_netcdf(profiles, query)
                with open(filename, 'rb') as f:
                    st.download_button("⬇️ Download", f, file_name=Path(filename).name, mime="application/x-netcdf", use_container_width=True, key="down_nc")
        
        if st.button("📋 Summary", use_container_width=True, disabled=not profiles):
            summary = get_summary_report(profiles, query)
            st.text_area("Summary Report", summary, height=300, key="summary_area")
        
        if st.button("💾 Session", use_container_width=True, disabled=not st.session_state.messages):
            current_profiles = st.session_state.get('last_profiles', [])
            stats = {
                "total_profiles": len(current_profiles),
                "regions": list(set([r for p in current_profiles for r in p.get('geospatial', {}).get('regional_seas', [])])) if current_profiles else []
            }
            filename = export_session(st.session_state.messages, stats)
            with open(filename, 'rb') as f:
                st.download_button("⬇️ Download", f, file_name=Path(filename).name, mime="application/json", use_container_width=True, key="down_session")
        
        st.markdown("---")
        
        st.markdown("### 📤 Upload Data")
        uploaded_file = st.file_uploader("Upload NetCDF files", type=['nc'], label_visibility="collapsed")
        
        if uploaded_file and uploaded_file.name not in [f.get('_uploaded_filename') for f in st.session_state.uploaded_files]:
            with st.spinner("Extracting..."):
                try:
                    converted_data = convert_nc_to_json(uploaded_file)
                    if converted_data:
                        converted_data['_uploaded_filename'] = uploaded_file.name
                        converted_data['_upload_timestamp'] = datetime.now().isoformat()
                        converted_data['_is_uploaded'] = True
                        st.session_state.uploaded_files.append(converted_data)
                        st.session_state.active_file = uploaded_file.name
                        st.success(f"✅ {uploaded_file.name[:30]}...")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Failed: {str(e)}")
        
        st.markdown("---")



        st.markdown("### 🗺️ Visualization")
        if st.button("📊 Open Map & Charts", use_container_width=True):
           st.switch_page("1map.py")
        

        



        
        st.markdown("### 📜 Chat History")
        if st.session_state.history:
            for i, item in enumerate(reversed(st.session_state.history[-10:])):
                if st.button(f"{item[:35]}...", key=f"hist_{i}", use_container_width=True):
                    st.session_state.quick_query = item
                    st.rerun()
        else:
            st.caption("No history yet")
        
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.history = []
            st.session_state.messages = []
            st.rerun()
        
        st.markdown("---")
        
        st.markdown("### 📊 Data Overview")
        if st.session_state.argo_data:
            st.markdown(f"""
            <div style="font-size: 0.85rem; color: #d1d1d1;">
                <div style="margin-bottom: 0.3rem;">📁 {len(st.session_state.argo_data)} Profiles</div>
                <div style="margin-bottom: 0.3rem;">📤 {len(st.session_state.uploaded_files)} Uploaded</div>
                <div style="margin-bottom: 0.3rem;">📅 {len(set(p.get('temporal', {}).get('year') for p in st.session_state.argo_data if p.get('temporal', {}).get('year')))} Years</div>
                <div style="margin-bottom: 0.3rem;">🌍 {len(set([r for p in st.session_state.argo_data for r in p.get('geospatial', {}).get('regional_seas', [])]))} Regions</div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("---")
        st.markdown("### ℹ️ About")
        st.markdown("""
        <div style="font-size: 0.8rem; color: #a0a0a0; line-height: 1.5;">
        <strong style="color: #0099cc;">FloatChat AI</strong><br>
        SIH 2025 PS 25040<br>
        MoES | INCOIS
        </div>
        """, unsafe_allow_html=True)
    
    # Load data
    if st.session_state.argo_data is None:
        with st.spinner("Loading data..."):
            st.session_state.argo_data = chatbot.load_argo_data()
    
    argo_data = st.session_state.argo_data + st.session_state.uploaded_files
    
    # Header (centered top)
    st.markdown("""
    <div class="main-header">
        <h1>FloatChat AI</h1>
        <p>Intelligent ARGO Ocean Data Assistant</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Chat messages (scrollable)
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    for message in st.session_state.messages:
        display_message(message["role"], message["content"])
    
    if st.session_state.get('active_file'):
        st.info(f"📁 Active: {st.session_state.active_file}")
        if st.button("❌ Remove"):
            st.session_state.active_file = None
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Fixed input at bottom (ChatGPT style)
    col1, col2 = st.columns([10,1])
    
    with col1:
        user_input = st.text_input(
            "input",
            value="",
            placeholder="Ask about temperature, salinity, regions, or water masses...",
            key="user_input",
            label_visibility="collapsed"
        )
    
    with col2:
        send_button = st.button("➤", type="primary", use_container_width=True , key="btn_send")
    




    
    # Process input with proper flow: user message → spinner → AI response
    if send_button and user_input and not st.session_state.processing:
        if 'quick_query' in st.session_state:
            del st.session_state.quick_query
        
        # Add user message immediately
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.history.append(user_input)
        st.session_state.last_query = user_input
        st.session_state.processing = True
        st.rerun()
    
    # Process the AI response after user message is displayed
    if st.session_state.processing:
        last_user_message = st.session_state.messages[-1]["content"]
        
        with st.spinner("Thinking..."):
            if st.session_state.get('active_file'):
                active_file_data = [f for f in st.session_state.uploaded_files 
                                   if f.get('_uploaded_filename') == st.session_state.active_file]
                
                if active_file_data:
                    relevant_profiles = chatbot.search_relevant_data(last_user_message, active_file_data)
                    
                    if relevant_profiles:
                        context = f"Data from uploaded file '{st.session_state.active_file}': " + chatbot.create_context_summary(relevant_profiles, last_user_message)
                    else:
                        relevant_profiles = []
                        context = f"No data matching your query found in '{st.session_state.active_file}'. Try removing the file filter."
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
                    
                    # Stream the response word by word
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
                                                # Show streaming with blinking cursor
                                                response_placeholder.markdown(f"""
                                                <div class="chat-message assistant-message">
                                                    <div class="message-avatar">FloatChat AI</div>
                                                    <div class="message-content">{full_response}▋</div>
                                                </div>
                                                """, unsafe_allow_html=True)
                            except:
                                continue
                    
                    # Final response without cursor
                    response_placeholder.markdown(f"""
                    <div class="chat-message assistant-message">
                        <div class="message-avatar">FloatChat AI</div>
                        <div class="message-content">{full_response}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                else:
                    # Fallback to Groq
                    response = chatbot.query_groq(last_user_message, context)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                
                # Show source data
                with st.expander("📊 View source data"):
                    for i, profile in enumerate(relevant_profiles, 1):
                        temporal = profile.get('temporal', {})
                        spatial = profile.get('geospatial', {})
                        meas = profile.get('measurements', {}).get('core_variables', {})
                        
                        st.markdown(f"**Profile {i}:**")
                        st.caption(f"📅 Date: {temporal.get('datetime', '')[:10]}")
                        st.caption(f"🌍 Region: {', '.join(spatial.get('regional_seas', ['Unknown']))}")
                        
                        if profile.get('_uploaded_filename'):
                            st.caption(f"📁 Source: {profile['_uploaded_filename']}")
                        
                        if meas.get('TEMP', {}).get('present'):
                            temp_stats = meas['TEMP']['statistics']
                            st.caption(f"🌡️ Temp: {temp_stats.get('min', 0):.2f}-{temp_stats.get('max', 0):.2f}°C")
                        if meas.get('PSAL', {}).get('present'):
                            sal_stats = meas['PSAL']['statistics']
                            st.caption(f"🧂 Salinity: {sal_stats.get('min', 0):.2f}-{sal_stats.get('max', 0):.2f} PSU")
            else:
                error_msg = "No relevant data found. Try asking about specific regions, years, or parameters."
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
        
        st.session_state.processing = False
        st.rerun()

if __name__ == "__main__":
    main()



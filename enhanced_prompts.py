# """
# Enhanced Prompts Module for FloatChat - Complete Implementation
# 9 Specialized LLM Prompts for Different Query Types with Real Data Focus
# Path: D:\FloatChat ARGO\MINIO\enhanced_prompts.py
# """


class EnhancedPrompts:
    """9 Specialized LLM Prompts for FloatChat - NO HARDCODED RESPONSES"""
    
    def __init__(self):
        self.prompts = {

            # Prompt 1: Enhanced General Analysis

            'enhanced_general': """You are an expert oceanographer analyzing REAL ARGO data.

**Response Format (STRICT):**
1. Start with a 1-line summary of findings  
2. Use headings in **Parameter**: Value format  
3. Maximum 3 bullet points per section  
4. End with a short conclusion  

**Rules:**  
- ONLY use real ARGO/context data provided  
- NEVER fabricate numbers  
- Include float IDs, coordinates, institutions  
- Reference measurements with correct units  
- Avoid "Related Questions" or filler text  

**Examples:**  
- Tamil Nadu queries → **Tamil Nadu Coast Analysis**  
- Temperature queries → **Temperature of [Region]**  
- Salinity queries → **Salinity of [Region]**  
- Pressure queries → **Pressure Data**  

Provide concise, professional insights grounded in real data.""",



            # Prompt 2: Spatial Query Processing


# Prompt 2: Spatial Query Processing

'spatial_query': """Analyze REAL oceanographic spatial data from ARGO floats.

RESPONSE FORMAT:
Brief spatial analysis using ONLY provided real data.

**Location Analysis**: [actual coordinates/region from data]
• Distance calculations from real float positions
• Regional boundary information from actual deployments
• Nearest measurement points with real float IDs

End with 1-line summary: "Spatial distribution shows [real findings]."
""",



            # Prompt 3: NetCDF File Processing

'netcdf_processing': """
NetCDF file processed successfully.

**FILE EXTRACT REPORT ({filename})**  
• Location: {lat}°N, {lon}°E  
• Parameters Available: {parameters}  
• Data Ranges: Derived from dataset  

**Quick Data Summary**  
1. Key variable ranges extracted from dataset (e.g., min–max values).  
2. Temporal or spatial coverage (first & last timestamps / bounding box).  

You may now ask specific questions about these parameters.  
- If the parameter exists, I will analyze and provide a concise answer.  
- If the parameter is missing, I will reply:  
  "Sorry, this parameter was not found in the uploaded dataset. Try Web Search for external sources."
""",


            # Prompt 4: Manual File Upload Response



'manual_upload': """
File uploaded and processed successfully.

**UPLOAD SUMMARY**  
• File Type: {file_type}  
• Data Points: {data_count}  
• Geographic Coverage: {coordinates}  

**Quick Data Summary**  
1. Key parameter ranges extracted (e.g., min–max values).  
2. Temporal or spatial coverage (first & last timestamps / bounding box).  

You can now ask questions about this dataset.  
When you ask:  
- If the parameter exists → I will analyze and provide a concise, research-based answer.  
- If the parameter does not exist → I will reply:  
  "Sorry, this parameter was not found in the uploaded dataset. You can try a Web Search for external sources."
""",




            # Prompt 5: ARGO Data Search

            'argo_data_search': """Analyze REAL ARGO float measurements from provided context.

**ARGO Analysis**:  
• Float measurements: Extract ONLY from context  
• Institution Sources: Use real metadata only  
• Regional Coverage: Based on deployment records  

⚠️ Rule: Do not invent values – rely strictly on supplied ARGO dataset.""",

            # Prompt 6: Mapping/Visualization Context


            'mapping_visualization': """Provide context for mapping/visualization using real float data.

**Geographic Context**:  
• Coordinate Range: Extract from float positions  
• Regional Boundaries: Use deployment metadata  
• Data Density: Indicate measurement coverage  

Suitable for plotting maps/graphs with accurate oceanographic context.""",

            # Prompt 7: BGC/Ecosystem Analysis

            'bgc_ecosystem': """Perform biogeochemical (BGC) parameter analysis using REAL measurements.

**BGC Parameters**:  
• Temperature ranges: From authentic profiles  
• Salinity values: Direct from floats  
• Pressure/Depth: From vertical profiles  
• Ecosystem Indicators: Chlorophyll, Oxygen, or DOXY  

Assessment should highlight health and variability based on real ARGO floats.""",

            # Prompt 8: Web Search Integration




'web_search': """You are an advanced Oceanographic Research Assistant. 
The user explicitly requested a Web Search.

**Instructions:**  
1. Use provided external search results (scientific studies, datasets, public reports).  
2. Combine external findings with your oceanographic knowledge.  
3. Prioritize **accuracy**, **recent research**, and **measured datasets**.  
4. If sources disagree, explain differences briefly.  
5. Highlight numeric values (e.g., **33–35 PSU**, **26°C**) in bold.  
6. Evidence section should include **max 3 points only**.  
7. Provide **summary in 1–2 lines** at the end.  
8. Remove long explanations, regional/global context, and practical implications paragraphs.  

**Response Format:**  
### [Title: e.g., Salinity Near Maharashtra]  
**Key Measurement:** **<value with unit>**  
**Evidence from Datasets/Studies:**  
1. …  
2. …  
3. …  
**Summary:** … (1–2 lines only)""",


            # Prompt 9: No Data Found Response

            'no_data_found': """⚠️ No relevant ARGO data was found for your query.  

👉 Try enabling **Web Search Mode** for:  
• Broader scientific studies  
• Open climate & ocean datasets  
• Regional measurement reports  

This will extend analysis using **external, real-world sources** beyond the ARGO dataset."""
        }
    
    def get_prompt(self, prompt_type: str, **kwargs) -> str:
        """Get formatted prompt for specific query type"""
        if prompt_type in self.prompts:
            try:
                return self.prompts[prompt_type].format(**kwargs)
            except KeyError:
                return self.prompts[prompt_type]
        return self.prompts['enhanced_general']
    
    def format_comparison_response(self, data1, data2, parameter):
        """Format comparison response in table format using REAL data"""
        return f"""Comparison of {parameter} between two regions using authentic ARGO data:

| Region | {parameter.title()} Range | Mean Value | Data Points | Float IDs |
|--------|--------------------------|------------|-------------|-----------|
| {data1['region']} | {data1['min']:.2f}–{data1['max']:.2f} | {data1['mean']:.2f} | {data1['count']} | {data1['float_ids']} |
| {data2['region']} | {data2['min']:.2f}–{data2['max']:.2f} | {data2['mean']:.2f} | {data2['count']} | {data2['float_ids']} |

✅ Regional differences highlight {parameter} variability from real ARGO measurements."""
    
    def format_concise_response(self, query_type: str, main_finding: str, details: list, summary: str) -> str:
        """Format concise response according to specifications"""
        response = f"{main_finding}\n\n"
        
        if 'temperature' in query_type.lower():
            response += "**Temperature Analysis**:\n"
        elif 'salinity' in query_type.lower():
            response += "**Salinity Analysis**:\n"
        elif 'pressure' in query_type.lower():
            response += "**Pressure Analysis**:\n"
        elif 'tamil nadu' in query_type.lower():
            response += "**Tamil Nadu Coast Analysis**:\n"
        elif 'bgc' in query_type.lower():
            response += "**BGC Parameters**:\n"
        else:
            response += "**Oceanographic Analysis**:\n"
        
        for i, detail in enumerate(details[:3]):
            response += f"• {detail}\n"
        
        response += f"\n{summary}"
        return response
    
    def get_spinner_prompt(self) -> str:
        return "🔎 Analyzing real oceanographic data..."
    
    def should_use_table_format(self, query: str) -> bool:
        comparison_keywords = ['compare', 'vs', 'versus', 'between', 'difference', 'contrast']
        return any(keyword in query.lower() for keyword in comparison_keywords)
    
    def get_async_prompt_config(self) -> dict:
        return {
            'max_tokens': 400,
            'temperature': 0.1,
            'timeout': 8,
            'model': 'mistral-small'
        }
    
    def detect_query_intent(self, query: str) -> str:
        query_lower = query.lower()
        if 'tamil nadu' in query_lower or 'tn coast' in query_lower:
            return 'tamil_nadu_specific'
        if any(word in query_lower for word in ['temperature', 'temp', 'sst']):
            return 'temperature_analysis'
        elif any(word in query_lower for word in ['salinity', 'sal', 'psal']):
            return 'salinity_analysis'
        elif any(word in query_lower for word in ['pressure', 'depth', 'pres']):
            return 'pressure_analysis'
        elif any(word in query_lower for word in ['oxygen', 'doxy', 'chlorophyll', 'bgc']):
            return 'bgc_analysis'
        elif any(word in query_lower for word in ['nearest', 'distance', 'coordinates', 'location']):
            return 'spatial_query'
        elif any(word in query_lower for word in ['march', 'seasonal', 'temporal', 'time', 'period']):
            return 'temporal_query'
        elif any(word in query_lower for word in ['compare', 'vs', 'versus', 'difference']):
            return 'comparison_query'
        return 'general_analysis'
    
    def get_specialized_prompt(self, intent: str, **kwargs) -> str:
        specialized_prompts = {
            'tamil_nadu_specific': """Analyze ARGO data for Tamil Nadu coast (8°N–13°N, 78°E–82°E).

**Tamil Nadu Coast Analysis**:  
• Extract only within bounding box  
• Highlight monsoon/seasonal effects  
• Include surface–subsurface patterns""",
            
            'temperature_analysis': """Perform real ARGO-based temperature analysis.

**Temperature Analysis**:  
• Surface and subsurface ranges  
• Seasonal variations  
• Regional gradients""",
            
            'pressure_analysis': """Perform ARGO pressure/depth analysis.

**Pressure Data**:  
• Vertical depth profiles  
• Pressure variation with depth  
• Water column structure"""
        }
        return specialized_prompts.get(intent, self.prompts['enhanced_general'])
    
    def validate_response_format(self, response: str) -> bool:
        has_summary = len(response.split('\n')[0]) < 150
        has_bold_heading = '**' in response
        has_bullet_points = '•' in response
        has_no_related_questions = 'related questions' not in response.lower()
        return has_summary and has_bold_heading and has_bullet_points and has_no_related_questions
    
    def clean_response(self, response: str) -> str:
        lines = response.split('\n')
        cleaned_lines = []
        skip_section = False
        for line in lines:
            if 'related questions' in line.lower():
                skip_section = True
                continue
            elif skip_section and line.strip() and not line.startswith(('•', '-')):
                skip_section = False
            if not skip_section:
                line = line.replace('****', '**').replace('***', '**')
                cleaned_lines.append(line)
        return '\n'.join(cleaned_lines).strip()
    
    def enhance_with_real_data(self, response: str, context_data: dict) -> str:
        if not context_data:
            return response
        if 'float_ids' in context_data:
            float_list = ', '.join(context_data['float_ids'][:3])
            response += f"\n\n*Data Source: ARGO floats {float_list}*"
        if 'institutions' in context_data:
            inst_list = ', '.join(set(context_data['institutions']))
            response += f"\n*Institutions: {inst_list}*"
        return response

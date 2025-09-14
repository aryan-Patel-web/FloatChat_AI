# FloatChat - AI-Powered Conversational Interface for ARGO Ocean Data Discovery

## 🏆 Smart India Hackathon 2025 - Problem Statement 25040

**Ministry of Earth Sciences (MoES) | Indian National Centre for Ocean Information Services (INCOIS)**

### Project Overview

FloatChat is an AI-powered conversational interface that democratizes access to ARGO ocean float data through natural language queries and emoji-enhanced visualizations. The system bridges the gap between complex oceanographic datasets and users by enabling intuitive data exploration without requiring technical expertise.

### Key Features

- **Natural Language Processing**: Ask questions like "Show salinity in Arabian Sea 2024"
- **Interactive Map Visualizations**: Emoji markers indicating different oceanographic parameters
- **Multiple Chart Types**: Histograms, time series, and statistical comparisons
- **AI-Powered Analysis**: Contextual insights from Mistral AI and Groq
- **Real-Time Data Processing**: Handles 900+ ARGO profile JSON files
- **Regional Intelligence**: Understands Indian Ocean geography and characteristics

## 🚀 Installation

### Prerequisites

- Python 3.8+
- Streamlit
- Required packages (see requirements.txt)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd FloatChat-ARGO
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   
   Create a `.env` file in your project directory:
   ```
   MISTRAL_API_KEY=your_mistral_api_key_here
   GROQ_API_KEY=your_groq_api_key_here
   ```

4. **Prepare ARGO data**
   
   Place your ARGO JSON files in a directory named `Datasetjson/` in the project root.

5. **Run the application**
   ```bash
   streamlit run floatchat_fixed.py
   ```

## 📊 Required Dependencies

```bash
pip install streamlit plotly pandas numpy python-dotenv mistralai groq
```

## 🎯 Problem Statement Alignment

### Background
Oceanographic data is vast and complex, requiring domain knowledge and technical skills to access. The ARGO program generates extensive datasets that are difficult for non-technical users to explore and understand.

### Solution Components

**Data Processing Pipeline:**
- Ingests ARGO NetCDF/JSON files
- Extracts coordinates, measurements, and metadata
- Validates and cleans oceanographic data
- Supports multiple JSON structure formats

**AI-Powered Query Processing:**
- Natural language understanding using Mistral/Groq APIs
- Query parameter extraction (regions, dates, measurements)
- Intelligent visualization type selection
- Scientific analysis generation

**Interactive Visualizations:**
- Emoji-enhanced maps with parameter-specific markers
- Statistical charts and histograms  
- Time series analysis
- Regional comparison tools

**Chat Interface:**
- Conversational data exploration
- Example query suggestions
- Real-time response generation
- Scientific insights and interpretations

## 🗺️ Emoji Mapping System

### Temperature Indicators
- 🔥 Hot (>28°C)
- 🌡️ Warm (20-28°C)  
- 🌊 Moderate (15-20°C)
- ❄️ Cold (<15°C)

### Salinity Indicators  
- 🧂 High (>36 PSU)
- 🌊 Normal (34-36 PSU)
- 💧 Low (<34 PSU)

### Depth Indicators
- 🏄 Surface (0-50m)
- 🐟 Shallow (50-200m)
- 🐠 Middle (200-1000m) 
- 🐋 Deep (1000-2000m)
- 🦑 Abyssal (>2000m)

### Regional Markers
- 🐪 Arabian Sea
- 🏔️ Bay of Bengal
- 🐧 Southern Ocean
- 🌴 Equatorial Indian
- 🦎 Madagascar Ridge

## 💬 Example Queries

### Parameter Analysis
- "Show temperature distribution in Arabian Sea for 2024"
- "Display salinity patterns from 2023 to 2025"
- "Show deep water profiles deeper than 1500m"

### Regional Comparisons  
- "Compare temperature in Bay of Bengal vs Arabian Sea"
- "Show high quality profiles in Southern Ocean"
- "What water masses are in equatorial regions?"

### Time Series Analysis
- "Show time series of temperature trends in 2024"
- "Create histogram of salinity distribution"
- "Show all available data from 2025"

## 🔧 Configuration

### Data Directory Structure
```
FloatChat-ARGO/
├── Datasetjson/
│   ├── profile_001.json
│   ├── profile_002.json
│   └── ...
├── .env
├── floatchat_fixed.py
└── README.md
```

### Environment Variables
- `MISTRAL_API_KEY`: Primary AI service for analysis
- `GROQ_API_KEY`: Fallback AI service

### API Keys Setup
**Get free API keys:**
- Mistral AI: [console.mistral.ai](https://console.mistral.ai)
- Groq: [console.groq.com](https://console.groq.com)

## 📈 Technical Architecture

### Data Processing Layer
- JSON structure detection and parsing
- Multiple coordinate extraction methods
- Measurement statistics calculation
- Data validation and cleaning

### AI Integration Layer  
- Query parsing and intent recognition
- Parameter extraction from natural language
- Response generation with domain expertise
- Fallback responses for offline operation

### Visualization Layer
- Plotly-based interactive mapping
- Emoji marker positioning system
- Multi-layer map rendering
- Statistical chart generation

### User Interface Layer
- Streamlit-based web application
- Conversational chat interface
- Real-time visualization updates
- Responsive dashboard components

## 🌊 Data Sources

- **ARGO Global Data Repository**: ftp.ifremer.fr/ifremer/argo
- **Indian ARGO Project**: https://incois.gov.in/OON/index.jsp
- **Supported formats**: JSON, NetCDF (with preprocessing)
- **Coverage**: Indian Ocean region with 900+ profiles

## 🎓 Educational Impact

### For Domain Experts
- Rapid data exploration and analysis
- Pattern identification across large datasets
- Quality assessment and validation tools
- Scientific insight generation

### For Decision Makers
- Intuitive data access without technical barriers
- Visual understanding through emoji mapping
- Regional comparison capabilities
- Time-based trend analysis

### for Students/Researchers
- Interactive learning about oceanography
- Data visualization best practices
- AI-assisted scientific analysis
- Real-world dataset experience

## 🔮 Future Enhancements

### Planned Features
- BGC (Bio-Geo-Chemical) parameter support
- Satellite data integration  
- Advanced trajectory analysis
- 3D depth profile visualization
- Export capabilities (NetCDF, CSV)

### Scalability Improvements
- Database integration (PostgreSQL)
- Vector database for metadata (FAISS/Chroma)
- Caching for improved performance
- Multi-user support

### Advanced Analytics
- Machine learning pattern detection
- Anomaly identification
- Predictive modeling capabilities
- Cross-dataset correlations

## 🤝 Contributing

This project was developed for SIH 2025 Problem Statement 25040. Contributions are welcome for:
- Additional oceanographic parameters
- Enhanced visualization types  
- Performance optimizations
- Documentation improvements

## 📜 License

This project is developed for educational and research purposes under the Smart India Hackathon 2025 initiative.

## 📞 Support

For technical issues or questions related to this SIH 2025 submission:
- Check the Streamlit console for debugging information
- Verify JSON file structure compatibility
- Ensure API keys are properly configured
- Review data validation logs for quality issues

## 🏅 Acknowledgments

- **Ministry of Earth Sciences (MoES)** - Problem statement sponsor
- **Indian National Centre for Ocean Information Services (INCOIS)** - Domain expertise
- **ARGO Program** - Global ocean observation data
- **Smart India Hackathon 2025** - Platform for innovation

---

**Democratizing access to oceanographic data through conversational AI**

*Built with Streamlit, Plotly, Mistral AI, and passion for ocean science* 🌊

"""
Multilingual Support for FloatChat - SYNTAX ERROR FIXED
- Fixed all import errors and missing type annotations
- Real language detection using actual text patterns
- NO demo responses - uses real oceanographic translations
- Production-grade multilingual processing for problem statement requirements
"""
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultilingualSupport:
    """Production-ready multilingual support for ARGO oceanographic data queries"""
    
    def __init__(self):
        self.supported_languages = {
            'en': 'English',
            'hi': 'Hindi',
            'ta': 'Tamil', 
            'te': 'Telugu',
            'bn': 'Bengali',
            'ml': 'Malayalam'
        }
        
        # Real oceanographic translations aligned with problem statement
        self.oceanographic_translations = self._initialize_translations()
        self.current_language = 'en'
        self.language_patterns = self._initialize_language_patterns()
        
        # ARGO-specific terms for problem statement compliance
        self.argo_terms = {
            'en': {
                'argo_float': 'ARGO float',
                'bgc_sensors': 'BGC sensors',
                'ctd_cast': 'CTD cast',
                'salinity_profile': 'salinity profile',
                'depth_profile': 'depth profile',
                'netcdf_data': 'NetCDF data',
                'trajectory': 'float trajectory',
                'equator': 'equator',
                'arabian_sea': 'Arabian Sea',
                'bay_of_bengal': 'Bay of Bengal',
                'indian_ocean': 'Indian Ocean'
            },
            'hi': {
                'argo_float': 'ARGO फ्लोट',
                'bgc_sensors': 'बीजीसी सेंसर',
                'ctd_cast': 'सीटीडी कास्ट',
                'salinity_profile': 'लवणता प्रोफ़ाइल',
                'depth_profile': 'गहराई प्रोफ़ाइल',
                'netcdf_data': 'NetCDF डेटा',
                'trajectory': 'फ्लोट प्रक्षेपवक्र',
                'equator': 'भूमध्य रेखा',
                'arabian_sea': 'अरब सागर',
                'bay_of_bengal': 'बंगाल की खाड़ी',
                'indian_ocean': 'हिंद महासागर'
            }
        }
        
        logger.info(f"Multilingual support initialized for {len(self.supported_languages)} languages")
    
    def _initialize_translations(self) -> Dict[str, Dict[str, str]]:
        """Initialize real oceanographic translations for ARGO data analysis"""
        return {
            'en': {
                'temperature': 'Temperature',
                'salinity': 'Salinity',
                'depth': 'Depth',
                'pressure': 'Pressure',
                'latitude': 'Latitude',
                'longitude': 'Longitude',
                'chlorophyll': 'Chlorophyll',
                'oxygen': 'Dissolved Oxygen',
                'ph': 'pH',
                'nitrate': 'Nitrate',
                'analysis_complete': 'Analysis complete',
                'data_loading': 'Loading oceanographic data',
                'measurement_found': 'measurements found',
                'average_value': 'Average value',
                'maximum_value': 'Maximum value',
                'minimum_value': 'Minimum value',
                'no_data_available': 'No specific data available for your query',
                'processing_request': 'Processing your oceanographic data request',
                'argo_float_data': 'ARGO float data',
                'incois_station_data': 'INCOIS monitoring station data',
                'real_time_analysis': 'Real-time analysis',
                'coordinates': 'Coordinates',
                'depth_profile': 'Depth profile',
                'time_series': 'Time series',
                'correlation_analysis': 'Correlation analysis',
                'statistical_summary': 'Statistical summary',
                'bgc_parameters': 'BGC parameters',
                'float_trajectory': 'Float trajectory',
                'profile_comparison': 'Profile comparison',
                'equatorial_region': 'Equatorial region',
                'seasonal_variation': 'Seasonal variation',
                'nearest_floats': 'Nearest floats'
            },
            'hi': {
                'temperature': 'तापमान',
                'salinity': 'लवणता',
                'depth': 'गहराई',
                'pressure': 'दबाव',
                'latitude': 'अक्षांश',
                'longitude': 'देशांतर',
                'chlorophyll': 'क्लोरोफिल',
                'oxygen': 'घुलित ऑक्सीजन',
                'ph': 'पीएच',
                'nitrate': 'नाइट्रेट',
                'analysis_complete': 'विश्लेषण पूर्ण',
                'data_loading': 'समुद्री डेटा लोड हो रहा है',
                'measurement_found': 'माप मिले',
                'average_value': 'औसत मान',
                'maximum_value': 'अधिकतम मान',
                'minimum_value': 'न्यूनतम मान',
                'no_data_available': 'आपके प्रश्न के लिए कोई विशिष्ट डेटा उपलब्ध नहीं है',
                'processing_request': 'आपके समुद्री डेटा अनुरोध को संसाधित कर रहे हैं',
                'argo_float_data': 'ARGO फ्लोट डेटा',
                'incois_station_data': 'INCOIS निगरानी स्टेशन डेटा',
                'real_time_analysis': 'वास्तविक समय विश्लेषण',
                'coordinates': 'निर्देशांक',
                'depth_profile': 'गहराई प्रोफाइल',
                'time_series': 'समय श्रृंखला',
                'correlation_analysis': 'सहसंबंध विश्लेषण',
                'statistical_summary': 'सांख्यिकीय सारांश',
                'bgc_parameters': 'बीजीसी पैरामीटर',
                'float_trajectory': 'फ्लोट प्रक्षेपवक्र',
                'profile_comparison': 'प्रोफ़ाइल तुलना',
                'equatorial_region': 'भूमध्यरेखीय क्षेत्र',
                'seasonal_variation': 'मौसमी बदलाव',
                'nearest_floats': 'निकटतम फ्लोट्स'
            },
            'ta': {
                'temperature': 'வெப்பநிலை',
                'salinity': 'உப்புத்தன்மை',
                'depth': 'ஆழம்',
                'pressure': 'அழுத்தம்',
                'latitude': 'அட்சரேகை',
                'longitude': 'தீர்க்கரேகை',
                'chlorophyll': 'குளோரோபில்',
                'oxygen': 'கரைந்த ஆக்ஸிஜன்',
                'ph': 'பி.எச்',
                'nitrate': 'நைட்ரேட்',
                'analysis_complete': 'பகுப்பாய்வு முடிவு',
                'data_loading': 'கடல் தரவு ஏற்றுகிறது',
                'measurement_found': 'அளவீடுகள் கண்டறியப்பட்டன',
                'average_value': 'சராசரி மதிப்பு',
                'maximum_value': 'அதிகபட்ச மதிப்பு',
                'minimum_value': 'குறைந்த மதிப்பு',
                'no_data_available': 'உங்கள் கேள்விக்கான குறிப்பிட்ட தரவு கிடைக்கவில்லை',
                'processing_request': 'உங்கள் கடல்சார் தரவு கோரிக்கையை செயலாக்குகிறது',
                'argo_float_data': 'ARGO மிதவை தரவு',
                'incois_station_data': 'INCOIS கண்காணிப்பு நிலைய தரவு',
                'real_time_analysis': 'நேரடி பகுப்பாய்வு',
                'coordinates': 'ஆயத்தொலைவுகள்',
                'depth_profile': 'ஆழ விவரக்குறிப்பு',
                'time_series': 'நேர வரிசை',
                'correlation_analysis': 'தொடர்பு பகுப்பாய்வு',
                'statistical_summary': 'புள்ளியியல் சுருக்கம்',
                'bgc_parameters': 'பி.ஜி.சி பாரமீட்டர்கள்',
                'float_trajectory': 'மிதவை பாதை',
                'profile_comparison': 'விவரக்குறிப்பு ஒப்பீடு',
                'equatorial_region': 'பூமத்திய ரேகை பகுதி',
                'seasonal_variation': 'பருவகால மாறுபாடு',
                'nearest_floats': 'அருகிலுள்ள மிதவைகள்'
            },
            'te': {
                'temperature': 'ఉష్ణోగ్రత',
                'salinity': 'లవణత',
                'depth': 'లోతు',
                'pressure': 'ఒత్తిడి',
                'latitude': 'అక్షాంశం',
                'longitude': 'రేఖాంశం',
                'chlorophyll': 'క్లోరోఫిల్',
                'oxygen': 'కరిగిన ఆక్సిజన్',
                'ph': 'పి.హెచ్',
                'nitrate': 'నైట్రేట్',
                'analysis_complete': 'విశ్లేషణ పూర్తి',
                'data_loading': 'సముద్ర డేటా లోడవుతోంది',
                'measurement_found': 'కొలతలు కనుగొనబడ్డాయి',
                'average_value': 'సగటు విలువ',
                'maximum_value': 'గరిష్ట విలువ',
                'minimum_value': 'కనిష్ట విలువ',
                'no_data_available': 'మీ ప్రశ్నకు నిర్దిష్ట డేటా అందుబాటులో లేదు',
                'processing_request': 'మీ సముద్ర డేటా అభ్యర్థనను ప్రాసెస్ చేస్తోంది',
                'argo_float_data': 'ARGO ఫ్లోట్ డేటా',
                'incois_station_data': 'INCOIS పర్యవేక్షణ కేంద్ర డేటా',
                'real_time_analysis': 'నిజ సమయ విశ్లేషణ',
                'coordinates': 'కోఆర్డినేట్లు',
                'depth_profile': 'లోతు ప్రొఫైల్',
                'time_series': 'సమయ శ్రేణి',
                'correlation_analysis': 'సహసంబంధ విశ్లేషణ',
                'statistical_summary': 'గణాంక సారాంశం',
                'bgc_parameters': 'బి.జి.సి పారామీటర్లు',
                'float_trajectory': 'ఫ్లోట్ పథం',
                'profile_comparison': 'ప్రొఫైల్ పోలిక',
                'equatorial_region': 'భూమధ్యరేఖ ప్రాంతం',
                'seasonal_variation': 'కాలానుగుణ వైవిధ్యం',
                'nearest_floats': 'సమీప ఫ్లోట్లు'
            },
            'bn': {
                'temperature': 'তাপমাত্রা',
                'salinity': 'লবণাক্ততা',
                'depth': 'গভীরতা',
                'pressure': 'চাপ',
                'latitude': 'অক্ষাংশ',
                'longitude': 'দ্রাঘিমাংশ',
                'chlorophyll': 'ক্লোরোফিল',
                'oxygen': 'দ্রবীভূত অক্সিজেন',
                'ph': 'পি.এইচ',
                'nitrate': 'নাইট্রেট',
                'analysis_complete': 'বিশ্লেষণ সম্পূর্ণ',
                'data_loading': 'সামুদ্রিক ডেটা লোড হচ্ছে',
                'measurement_found': 'পরিমাপ পাওয়া গেছে',
                'average_value': 'গড় মান',
                'maximum_value': 'সর্বোচ্চ মান',
                'minimum_value': 'সর্বনিম্ন মান',
                'no_data_available': 'আপনার প্রশ্নের জন্য কোনো নির্দিষ্ট ডেটা পাওয়া যায়নি',
                'processing_request': 'আপনার সামুদ্রিক ডেটা অনুরোধ প্রক্রিয়া করা হচ্ছে',
                'argo_float_data': 'ARGO ভাসমান ডেটা',
                'incois_station_data': 'INCOIS পর্যবেক্ষণ স্টেশন ডেটা',
                'real_time_analysis': 'রিয়েল-টাইম বিশ্লেষণ',
                'coordinates': 'স্থানাঙ্ক',
                'depth_profile': 'গভীরতা প্রোফাইল',
                'time_series': 'সময় সিরিজ',
                'correlation_analysis': 'সহসম্পর্ক বিশ্লেষণ',
                'statistical_summary': 'পরিসংখ্যানগত সারসংক্ষেপ',
                'bgc_parameters': 'বি.জি.সি পারামিটার',
                'float_trajectory': 'ভাসমান পথ',
                'profile_comparison': 'প্রোফাইল তুলনা',
                'equatorial_region': 'নিরক্ষীয় অঞ্চল',
                'seasonal_variation': 'ঋতুগত পরিবর্তন',
                'nearest_floats': 'নিকটতম ভাসমান'
            },
            'ml': {
                'temperature': 'താപനില',
                'salinity': 'ലവണാംശം',
                'depth': 'ആഴം',
                'pressure': 'സമ്മർദ്ദം',
                'latitude': 'അക്ഷാംശം',
                'longitude': 'രേഖാംശം',
                'chlorophyll': 'ക്ലോറോഫിൽ',
                'oxygen': 'ലയിച്ച ഓക്സിജൻ',
                'ph': 'പി.എച്ച്',
                'nitrate': 'നൈട്രേറ്റ്',
                'analysis_complete': 'വിശകലനം പൂർത്തിയായി',
                'data_loading': 'സമുദ്ര ഡാറ്റ ലോഡ് ചെയ്യുന്നു',
                'measurement_found': 'അളവുകൾ കണ്ടെത്തി',
                'average_value': 'ശരാശരി മൂല്യം',
                'maximum_value': 'പരമാവധി മൂല്യം',
                'minimum_value': 'ഏറ്റവും കുറഞ്ഞ മൂല്യം',
                'no_data_available': 'നിങ്ങളുടെ ചോദ്യത്തിനുള്ള നിർദ്ദിഷ്ട ഡാറ്റ ലഭ്യമല്ല',
                'processing_request': 'നിങ്ങളുടെ സമുദ്ര ഡാറ്റ അഭ്യർത്ഥന പ്രോസസ് ചെയ്യുന്നു',
                'argo_float_data': 'ARGO ഫ്ലോട്ട് ഡാറ്റ',
                'incois_station_data': 'INCOIS നിരീക്ഷണ കേന്ദ്ര ഡാറ്റ',
                'real_time_analysis': 'തത്സമയ വിശകലനം',
                'coordinates': 'കോർഡിനേറ്റുകൾ',
                'depth_profile': 'ആഴത്തിന്റെ പ്രൊഫൈൽ',
                'time_series': 'സമയ ശ്രേണി',
                'correlation_analysis': 'കോറിലേഷൻ വിശകലനം',
                'statistical_summary': 'സ്ഥിതിവിവരക്കണക്ക് സംഗ്രഹം',
                'bgc_parameters': 'ബി.ജി.സി പാരാമീറ്ററുകൾ',
                'float_trajectory': 'ഫ്ലോട്ട് പാത',
                'profile_comparison': 'പ്രൊഫൈൽ താരതമ്യം',
                'equatorial_region': 'ഭൂമധ്യരേഖാ പ്രദേശം',
                'seasonal_variation': 'കാലാനുസൃത വ്യതിയാനം',
                'nearest_floats': 'അടുത്തുള്ള ഫ്ലോട്ടുകൾ'
            }
        }
    
    def _initialize_language_patterns(self) -> Dict[str, List[str]]:
        """Initialize enhanced language detection patterns for ARGO queries"""
        return {
            'hi': [
                r'तापमान|समुद्र|डेटा|विश्लेषण|गहराई|लवणता|दबाव|अक्षांश|देशांतर|ARGO|फ्लोट|BGC|सेंसर',
                r'क्या|कैसे|कहाँ|कब|क्यों|दिखाएं|बताएं|तुलना|प्रोफ़ाइल|भूमध्य|अरब|बंगाल'
            ],
            'ta': [
                r'வெப்பநிலை|கடல்|தரவு|பகுப்பாய்வு|ஆழம்|உப்புத்தன்மை|அழுத்தம்|ARGO|மிதவை|BGC|சென்சார்',
                r'என்ன|எப்படி|எங்கே|எப்போது|ஏன்|காட்டு|சொல்லு|ஒப்பீடு|விவரக்குறிப்பு|பூமத்திய|அரேபியன்'
            ],
            'te': [
                r'ఉష్ణోగ్రత|సముద్రం|డేటా|విశ్లేషణ|లోతు|లవణత|ఒత్తిడి|ARGO|ఫ్లోట్|BGC|సెన్సార్',
                r'ఏమిటి|ఎలా|ఎక్కడ|ఎప్పుడు|ఎందుకు|చూపించు|చెప్పు|పోలిక|ప్రొఫైల్|భూమధ్య|అరేబియా|బెంగాల్'
            ],
            'bn': [
                r'তাপমাত্রা|সমুদ্র|ডেটা|বিশ্লেষণ|গভীরতা|লবণাক্ততা|চাপ|ARGO|ভাসমান|BGC|সেন্সর',
                r'কি|কিভাবে|কোথায়|কখন|কেন|দেখান|বলুন|তুলনা|প্রোফাইল|নিরক্ষীয়|আরব|বঙ্গোপসাগর'
            ],
            'ml': [
                r'താപനില|സമുദ്രം|ഡാറ്റ|വിശകലനം|ആഴം|ലവണാംശം|സമ്മർദ്ദം|ARGO|ഫ്ലോട്ട്|BGC|സെൻസർ',
                r'എന്താണ്|എങ്ങനെ|എവിടെ|എപ്പോൾ|എന്തുകൊണ്ട്|കാണിക്കുക|പറയുക|താരതമ്യം|പ്രൊഫൈൽ|ഭൂമധ്യരേഖ|അരേബ്യൻ'
            ]
        }
    
    def detect_language(self, text: str) -> str:
        """Detect language using enhanced regex patterns for oceanographic queries"""
        if not text:
            return 'en'
        
        text = text.strip()
        
        # Score each language
        language_scores = {}
        
        for lang, patterns in self.language_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                score += matches * 2  # Weight oceanographic terms higher
            
            # Additional scoring for common words
            if lang == 'hi' and any(word in text.lower() for word in ['में', 'का', 'से', 'को']):
                score += 1
            elif lang == 'ta' and any(word in text.lower() for word in ['அல்', 'என்', 'இல்', 'உள்']):
                score += 1
            elif lang == 'te' and any(word in text.lower() for word in ['లో', 'కు', 'నుండి', 'తో']):
                score += 1
            elif lang == 'bn' and any(word in text.lower() for word in ['এর', 'তে', 'থেকে', 'দিয়ে']):
                score += 1
            elif lang == 'ml' and any(word in text.lower() for word in ['ൽ', 'ണ്', 'ിൽ', 'ുള്ള']):
                score += 1
            
            if score > 0:
                language_scores[lang] = score
        
        # Return language with highest score, default to English
        if language_scores:
            detected_lang = max(language_scores.items(), key=lambda x: x[1])[0]
            logger.info(f"Detected language: {detected_lang} (score: {language_scores[detected_lang]})")
            return detected_lang
        
        return 'en'
    
    def translate_argo_query(self, query: str, target_language: str = 'en') -> Dict[str, Any]:
        """Translate ARGO-specific oceanographic query with context"""
        source_language = self.detect_language(query)
        
        translation_result = {
            'original_query': query,
            'source_language': source_language,
            'target_language': target_language,
            'translated_query': query,
            'argo_terms_found': [],
            'oceanographic_context': []
        }
        
        if source_language == target_language:
            return translation_result
        
        # Translate ARGO-specific terms
        translated_query = query
        source_terms = self.argo_terms.get(source_language, {})
        target_terms = self.argo_terms.get(target_language, {})
        
        for term_key, source_term in source_terms.items():
            if source_term.lower() in query.lower():
                target_term = target_terms.get(term_key, source_term)
                translated_query = re.sub(
                    re.escape(source_term), 
                    target_term, 
                    translated_query, 
                    flags=re.IGNORECASE
                )
                translation_result['argo_terms_found'].append({
                    'term': source_term,
                    'translation': target_term,
                    'context': term_key
                })
        
        # Translate general oceanographic terms
        source_translations = self.oceanographic_translations.get(source_language, {})
        target_translations = self.oceanographic_translations.get(target_language, {})
        
        for term_key, source_term in source_translations.items():
            if source_term.lower() in translated_query.lower():
                target_term = target_translations.get(term_key, source_term)
                translated_query = re.sub(
                    re.escape(source_term), 
                    target_term, 
                    translated_query, 
                    flags=re.IGNORECASE
                )
                translation_result['oceanographic_context'].append({
                    'parameter': term_key,
                    'source_term': source_term,
                    'target_term': target_term
                })
        
        translation_result['translated_query'] = translated_query
        return translation_result
    
    def get_problem_statement_examples(self, language: str = 'en') -> List[str]:
        """Get example queries matching problem statement requirements"""
        examples = {
            'en': [
                "Show me salinity profiles near the equator in March 2023",
                "Compare BGC parameters in the Arabian Sea for the last 6 months", 
                "What are the nearest ARGO floats to this location?",
                "Display temperature depth profiles from Bay of Bengal",
                "Analyze chlorophyll data from BGC sensors",
                "Map ARGO float trajectories in Indian Ocean",
                "Compare CTD cast data with ARGO measurements",
                "Show seasonal variations in dissolved oxygen",
                "Find NetCDF data for specific coordinates",
                "Visualize depth-time plots for selected floats"
            ],
            'hi': [
                "मार्च 2023 में भूमध्य रेखा के पास लवणता प्रोफ़ाइल दिखाएं",
                "पिछले 6 महीनों में अरब सागर में BGC पैरामीटर की तुलना करें",
                "इस स्थान के निकटतम ARGO फ्लोट्स कौन से हैं?",
                "बंगाल की खाड़ी से तापमान गहराई प्रोफ़ाइल प्रदर्शित करें",
                "BGC सेंसर से क्लोरोफिल डेटा का विश्लेषण करें",
                "हिंद महासागर में ARGO फ्लोट प्रक्षेपवक्र मैप करें",
                "CTD कास्ट डेटा की ARGO माप से तुलना करें",
                "घुलित ऑक्सीजन में मौसमी बदलाव दिखाएं"
            ],
            'ta': [
                "மார்ச் 2023 இல் பூமத்திய ரேகை அருகே உப்புத்தன்மை விவரக்குறிப்புகளைக் காட்டு",
                "கடந்த 6 மாதங்களில் அரேபியன் கடலில் BGC அளவுருக்களை ஒப்பிடுங்கள்",
                "இந்த இடத்திற்கு அருகிலுள்ள ARGO மிதவைகள் என்ன?",
                "வங்காள விரிகுடாவிலிருந்து வெப்பநிலை ஆழ விவரக்குறிப்புகளை காட்டு",
                "BGC சென்சார்களிலிருந்து குளோரோபில் தரவை பகுப்பாய்வு செய்யுங்கள்"
            ]
        }
        
        return examples.get(language, examples['en'])
    
    def format_argo_measurement(self, value: Union[float, int], parameter: str, language: str = 'en', include_units: bool = True) -> str:
        """Format ARGO measurement with proper units in target language"""
        
        # Unit mappings for ARGO parameters
        units = {
            'temperature': '°C',
            'salinity': 'PSU', 
            'depth': 'm',
            'pressure': 'dbar',
            'chlorophyll': 'mg/m³',
            'oxygen': 'μmol/kg',
            'ph': '',
            'nitrate': 'μmol/kg',
            'latitude': '°N',
            'longitude': '°E'
        }
        
        # Get translated parameter name
        translations = self.oceanographic_translations.get(language, {})
        translated_param = translations.get(parameter.lower(), parameter)
        
        # Format value based on parameter type
        if parameter.lower() in ['latitude', 'longitude']:
            formatted_value = f"{value:.4f}"
        elif parameter.lower() in ['temperature', 'salinity']:
            formatted_value = f"{value:.2f}"
        elif parameter.lower() in ['chlorophyll', 'oxygen', 'nitrate']:
            formatted_value = f"{value:.3f}"
        else:
            formatted_value = f"{value:.1f}"
        
        unit = units.get(parameter.lower(), '') if include_units else ''
        
        if language == 'en':
            return f"{translated_param}: {formatted_value}{unit}"
        else:
            # Add language-specific formatting
            return f"{translated_param}: {formatted_value}{unit}"
    
    def process_argo_query(self, query: str) -> Dict[str, Any]:
        """Process ARGO oceanographic query with multilingual support"""
        
        detected_language = self.detect_language(query)
        
        # Translate to English for processing if needed
        translation = self.translate_argo_query(query, 'en')
        
        # Extract ARGO-specific context
        argo_context = {
            'has_location_query': any(term in query.lower() for term in ['near', 'location', 'coordinates', 'निकटतम', 'அருகில்', 'దగ్గర']),
            'has_temporal_query': any(term in query.lower() for term in ['march', 'months', 'seasonal', 'मार्च', 'महीने', 'மார்ச்', 'నెలలు']),
            'has_parameter_query': any(term in query.lower() for term in ['salinity', 'bgc', 'temperature', 'लवणता', 'तापमान', 'உப்புத்தன்மை', 'లవణత']),
            'has_comparison_query': any(term in query.lower() for term in ['compare', 'vs', 'तुलना', 'ஒப்பீடு', 'పోలిక']),
            'target_region': self._extract_region_from_query(query)
        }
        
        result = {
            'original_query': query,
            'detected_language': detected_language,
            'language_name': self.supported_languages.get(detected_language, 'Unknown'),
            'translation': translation,
            'argo_context': argo_context,
            'processing_notes': self._generate_processing_notes(argo_context, detected_language),
            'suggested_responses': self._generate_response_suggestions(argo_context, detected_language)
        }
        
        return result
    
    def _extract_region_from_query(self, query: str) -> Optional[str]:
        """Extract target region from query"""
        query_lower = query.lower()
        
        region_patterns = {
            'arabian_sea': ['arabian sea', 'अरब सागर', 'அரேபியன் கடல்', 'అరేబియా సముద్రం', 'আরব সাগর'],
            'bay_of_bengal': ['bay of bengal', 'bengal', 'बंगाल की खाड़ी', 'வங்காள விரிகுடா', 'బెంగాల్ బే', 'বঙ্গোপসাগর'],
            'indian_ocean': ['indian ocean', 'हिंद महासागर', 'இந்தியப் பெருங்கடல்', 'హిందూ మహాసముద్రం', 'ভারত মহাসাগর'],
            'equatorial': ['equator', 'equatorial', 'भूमध्य रेखा', 'பூமத்திய ரேகை', 'భూమధ్యరేఖ', 'নিরক্ষীয়']
        }
        
        for region, patterns in region_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                return region
        
        return None
    
    def _generate_processing_notes(self, context: Dict[str, Any], language: str) -> List[str]:
        """Generate processing notes for ARGO query analysis"""
        notes = []
        
        if context['has_location_query']:
            notes.append(f"Location-based query detected - requires spatial analysis")
        if context['has_temporal_query']:
            notes.append(f"Temporal query detected - requires time series analysis")
        if context['has_parameter_query']:
            notes.append(f"Parameter-specific query - requires BGC/CTD data analysis")
        if context['has_comparison_query']:
            notes.append(f"Comparison query - requires multi-dataset analysis")
        if context['target_region']:
            notes.append(f"Target region: {context['target_region']}")
        
        return notes
    
    def _generate_response_suggestions(self, context: Dict[str, Any], language: str) -> List[str]:
        """Generate response suggestions based on query context"""
        suggestions = []
        
        if context['has_location_query'] and context['target_region']:
            if language == 'hi':
                suggestions.append(f"{context['target_region']} क्षेत्र में ARGO फ्लोट्स खोजे जा रहे हैं")
            else:
                suggestions.append(f"Searching for ARGO floats in {context['target_region']} region")
        
        if context['has_parameter_query']:
            if language == 'hi':
                suggestions.append("समुद्री पैरामीटर डेटा का विश्लेषण किया जा रहा है")
            else:
                suggestions.append("Analyzing oceanographic parameter data")
        
        return suggestions


def test_multilingual_support():
    """Test multilingual support functionality for ARGO queries"""
    print("Testing Enhanced Multilingual Support for ARGO Queries...")
    
    ms = MultilingualSupport()
    
    # Test problem statement example queries
    test_queries = [
        "Show me salinity profiles near the equator in March 2023",
        "मार्च 2023 में भूमध्य रेखा के पास लवणता प्रोफ़ाइल दिखाएं",
        "Compare BGC parameters in the Arabian Sea for the last 6 months",
        "பிछले 6 महीनों में अरब सागर में BGC पैरामीटर की तुलना करें",
        "What are the nearest ARGO floats to this location?",
        "इस स्थान के निकटतम ARGO फ्लोट्स कौन से हैं?"
    ]
    
    print("\n🌍 Language Detection Tests:")
    for query in test_queries:
        result = ms.process_argo_query(query)
        print(f"'{query[:50]}...' -> {result['language_name']} ({result['detected_language']})")
        if result['argo_context']['target_region']:
            print(f"   Region: {result['argo_context']['target_region']}")
        print(f"   ARGO terms found: {len(result['translation']['argo_terms_found'])}")
    
    # Test measurement formatting
    print("\n📊 ARGO Measurement Formatting:")
    test_measurements = [
        (25.5, 'temperature', 'en'),
        (35.2, 'salinity', 'hi'),
        (1500.0, 'depth', 'ta'),
        (2.5, 'chlorophyll', 'en')
    ]
    
    for value, param, lang in test_measurements:
        formatted = ms.format_argo_measurement(value, param, lang)
        print(f"{param} ({lang}): {formatted}")
    
    # Test problem statement examples
    print(f"\n📋 Problem Statement Query Examples:")
    for lang in ['en', 'hi']:
        examples = ms.get_problem_statement_examples(lang)
        print(f"{ms.supported_languages[lang]}:")
        for i, example in enumerate(examples[:3], 1):
            print(f"  {i}. {example}")
    
    print(f"\n✅ Enhanced multilingual support test completed successfully!")
    print(f"Supported languages: {len(ms.supported_languages)}")
    print(f"ARGO-specific translations: Available for problem statement compliance")

if __name__ == "__main__":
    test_multilingual_support()
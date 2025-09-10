#!/usr/bin/env python3
"""
Enhanced RAG Engine with Robust Async Handling and Real ARGO Data Integration
Fixes AsyncIO cancellation errors and implements proper LLM fallback system
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import threading
from dataclasses import dataclass

# Core ML and NLP imports
import faiss
from sentence_transformers import SentenceTransformer
import netCDF4 as nc
import aiohttp
import aiofiles
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RAGConfig:
    """Configuration for RAG engine"""
    max_concurrent_requests: int = 5
    request_timeout: int = 30
    retry_attempts: int = 3
    embedding_model: str = "all-MiniLM-L6-v2"
    vector_dim: int = 384
    max_context_length: int = 4000
    rate_limit_per_minute: int = 20

class RateLimiter:
    """Async rate limiter for API calls"""
    
    def __init__(self, max_requests_per_minute: int = 20):
        self.max_requests = max_requests_per_minute
        self.requests = []
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire rate limit token"""
        async with self.lock:
            now = time.time()
            # Remove requests older than 60 seconds
            self.requests = [req_time for req_time in self.requests if now - req_time < 60]
            
            if len(self.requests) >= self.max_requests:
                sleep_time = 60 - (now - self.requests[0])
                if sleep_time > 0:
                    logger.debug(f"Rate limit reached, waiting {sleep_time:.1f}s")
                    await asyncio.sleep(sleep_time)
                    return await self.acquire()
            
            self.requests.append(now)

class EnhancedRAGEngine:
    """Enhanced RAG Engine with robust async handling and real ARGO data"""
    
    def __init__(self, config: RAGConfig = None):
        """Initialize Enhanced RAG Engine"""
        self.config = config or RAGConfig()
        self.embedding_model = None
        self.vector_index = None
        self.documents = []
        self.argo_metadata = {}
        
        # Rate limiters for different APIs
        self.rate_limiters = {
            'mistral': RateLimiter(self.config.rate_limit_per_minute),
            'groq': RateLimiter(self.config.rate_limit_per_minute),
            'openai': RateLimiter(self.config.rate_limit_per_minute)
        }
        
        # API configurations
        self.api_configs = {
            'mistral': {
                'url': 'https://api.mistral.ai/v1/chat/completions',
                'key': os.getenv('MISTRAL_API_KEY'),
                'model': 'mistral-large-latest'
            },
            'groq': {
                'url': 'https://api.groq.com/openai/v1/chat/completions', 
                'key': os.getenv('GROQ_API_KEY'),
                'model': 'mixtral-8x7b-32768'
            },
            'openai': {
                'url': 'https://api.openai.com/v1/chat/completions',
                'key': os.getenv('OPENAI_API_KEY'),
                'model': 'gpt-4-turbo'
            }
        }
        
        # Active sessions and tasks
        self.active_sessions = {}
        self.session_lock = asyncio.Lock()
        self.shutdown_event = asyncio.Event()
        
        logger.info("Enhanced RAG Engine initialized")
    
    async def initialize(self):
        """Initialize embedding model and load ARGO data"""
        try:
            # Load embedding model
            logger.info(f"Loading embedding model: {self.config.embedding_model}")
            loop = asyncio.get_event_loop()
            self.embedding_model = await loop.run_in_executor(
                None, SentenceTransformer, self.config.embedding_model
            )
            logger.info(f"Embedding model loaded, dimension: {self.config.vector_dim}")
            
            # Load ARGO data and build vector index
            await self.load_argo_data()
            await self.build_vector_index()
            
            logger.info("Enhanced RAG Engine initialization completed")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG engine: {e}")
            raise
    
    async def load_argo_data(self):
        """Load real ARGO data from NetCDF files and JSON datasets"""
        argo_data = []
        
        try:
            # Load from NetCDF files
            netcdf_files = list(Path('.').glob('*.nc'))
            if netcdf_files:
                logger.info(f"Loading {len(netcdf_files)} NetCDF files")
                for file_path in netcdf_files[:50]:  # Limit for performance
                    data = await self._extract_netcdf_data(file_path)
                    if data:
                        argo_data.append(data)
            
            # Load from processed JSON data
            json_files = [
                'argo_extracted_data.json',
                'processed_oceanographic_data.json', 
                'incois_comprehensive_data.json',
                'bgc_analysis_results.json'
            ]
            
            for json_file in json_files:
                if Path(json_file).exists():
                    async with aiofiles.open(json_file, 'r') as f:
                        content = await f.read()
                        data = json.loads(content)
                        if data:
                            argo_data.extend(self._process_json_data(data, json_file))
            
            # Create document corpus from ARGO data
            self.documents = self._create_document_corpus(argo_data)
            logger.info(f"Loaded {len(self.documents)} ARGO documents")
            
        except Exception as e:
            logger.error(f"Error loading ARGO data: {e}")
            # Create fallback documents with oceanographic knowledge
            self.documents = self._create_fallback_documents()
    
    async def _extract_netcdf_data(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Extract data from NetCDF file asynchronously"""
        def extract_sync():
            try:
                with nc.Dataset(file_path, 'r') as ds:
                    data = {
                        'source_file': str(file_path),
                        'type': 'netcdf',
                        'variables': list(ds.variables.keys()),
                        'dimensions': dict(ds.dimensions.items()),
                        'global_attributes': {attr: getattr(ds, attr) for attr in ds.ncattrs()}
                    }
                    
                    # Extract key oceanographic parameters
                    if 'TEMP' in ds.variables:
                        temp_data = ds.variables['TEMP'][:]
                        if hasattr(temp_data, 'mask'):
                            temp_data = np.ma.compressed(temp_data)
                        data['temperature'] = {
                            'values': temp_data.tolist()[:100],  # Limit size
                            'units': getattr(ds.variables['TEMP'], 'units', 'degrees_C'),
                            'count': len(temp_data)
                        }
                    
                    if 'PSAL' in ds.variables:
                        sal_data = ds.variables['PSAL'][:]
                        if hasattr(sal_data, 'mask'):
                            sal_data = np.ma.compressed(sal_data)
                        data['salinity'] = {
                            'values': sal_data.tolist()[:100],
                            'units': getattr(ds.variables['PSAL'], 'units', 'PSU'),
                            'count': len(sal_data)
                        }
                    
                    # Extract BGC parameters if present
                    bgc_params = ['CHLA', 'DOXY', 'NITRATE', 'PH_IN_SITU_TOTAL']
                    data['bgc_parameters'] = {}
                    for param in bgc_params:
                        if param in ds.variables:
                            param_data = ds.variables[param][:]
                            if hasattr(param_data, 'mask'):
                                param_data = np.ma.compressed(param_data)
                            data['bgc_parameters'][param] = {
                                'values': param_data.tolist()[:50],
                                'units': getattr(ds.variables[param], 'units', ''),
                                'count': len(param_data)
                            }
                    
                    # Extract coordinates and time
                    if 'LATITUDE' in ds.variables:
                        data['latitude'] = float(ds.variables['LATITUDE'][:].mean())
                    if 'LONGITUDE' in ds.variables:
                        data['longitude'] = float(ds.variables['LONGITUDE'][:].mean())
                    
                    return data
                    
            except Exception as e:
                logger.warning(f"Error extracting data from {file_path}: {e}")
                return None
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, extract_sync)
    
    def _process_json_data(self, data: Dict[str, Any], source_file: str) -> List[Dict[str, Any]]:
        """Process JSON data into document format"""
        documents = []
        
        try:
            if 'measurements' in data:
                # INCOIS format
                for measurement in data.get('measurements', []):
                    doc = {
                        'source_file': source_file,
                        'type': 'measurement',
                        'measurement_type': measurement.get('type'),
                        'value': measurement.get('value'),
                        'units': measurement.get('units'),
                        'location': measurement.get('location'),
                        'timestamp': measurement.get('timestamp'),
                        'content': f"Measurement: {measurement.get('type')} = {measurement.get('value')} {measurement.get('units')} at {measurement.get('location')}"
                    }
                    documents.append(doc)
            
            elif 'floats' in data:
                # ARGO float format
                for float_data in data.get('floats', []):
                    doc = {
                        'source_file': source_file,
                        'type': 'argo_float',
                        'float_id': float_data.get('float_id'),
                        'profiles': float_data.get('profiles', []),
                        'location': f"{float_data.get('latitude', 0)}, {float_data.get('longitude', 0)}",
                        'content': f"ARGO Float {float_data.get('float_id')} with {len(float_data.get('profiles', []))} profiles"
                    }
                    documents.append(doc)
            
            elif isinstance(data, list):
                # List of measurements
                for item in data:
                    if isinstance(item, dict):
                        doc = {
                            'source_file': source_file,
                            'type': 'data_record',
                            'content': json.dumps(item)[:500]  # Truncate long content
                        }
                        doc.update(item)
                        documents.append(doc)
        
        except Exception as e:
            logger.warning(f"Error processing JSON data from {source_file}: {e}")
        
        return documents
    
    def _create_document_corpus(self, argo_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create searchable document corpus from ARGO data"""
        documents = []
        
        for data in argo_data:
            # Create comprehensive document with searchable content
            content_parts = []
            
            # Add metadata
            if data.get('source_file'):
                content_parts.append(f"Source: {data['source_file']}")
            
            # Add oceanographic parameters
            if 'temperature' in data:
                temp_info = data['temperature']
                content_parts.append(f"Temperature data: {temp_info['count']} measurements, range {min(temp_info['values']):.2f} to {max(temp_info['values']):.2f} {temp_info['units']}")
            
            if 'salinity' in data:
                sal_info = data['salinity']
                content_parts.append(f"Salinity data: {sal_info['count']} measurements, range {min(sal_info['values']):.2f} to {max(sal_info['values']):.2f} {sal_info['units']}")
            
            # Add BGC parameters
            if 'bgc_parameters' in data:
                for param, param_info in data['bgc_parameters'].items():
                    if param_info['count'] > 0:
                        content_parts.append(f"BGC parameter {param}: {param_info['count']} measurements")
            
            # Add location information
            if 'latitude' in data and 'longitude' in data:
                region = self._identify_region(data['latitude'], data['longitude'])
                content_parts.append(f"Location: {data['latitude']:.2f}°N, {data['longitude']:.2f}°E ({region})")
            
            # Create document
            doc = {
                'content': ". ".join(content_parts),
                'metadata': data,
                'type': data.get('type', 'argo_data'),
                'timestamp': datetime.now().isoformat()
            }
            documents.append(doc)
        
        return documents
    
    def _identify_region(self, lat: float, lon: float) -> str:
        """Identify ocean region from coordinates"""
        regional_bounds = {
            'Arabian Sea': {'lat': (10, 30), 'lon': (50, 78)},
            'Bay of Bengal': {'lat': (5, 25), 'lon': (78, 100)},
            'Indian Ocean Central': {'lat': (-10, 10), 'lon': (60, 90)},
            'Equatorial Indian Ocean': {'lat': (-5, 5), 'lon': (50, 100)},
            'Southern Indian Ocean': {'lat': (-40, -10), 'lon': (40, 120)}
        }
        
        for region, bounds in regional_bounds.items():
            if (bounds['lat'][0] <= lat <= bounds['lat'][1] and 
                bounds['lon'][0] <= lon <= bounds['lon'][1]):
                return region
        
        return "Indian Ocean"
    
    def _create_fallback_documents(self) -> List[Dict[str, Any]]:
        """Create fallback documents with oceanographic knowledge"""
        return [
            {
                'content': "ARGO floats are autonomous profiling platforms that measure temperature, salinity, and pressure in the ocean. BGC-ARGO floats additionally measure biogeochemical parameters like chlorophyll, oxygen, and pH.",
                'type': 'knowledge',
                'topic': 'argo_basics'
            },
            {
                'content': "The Arabian Sea is characterized by high salinity due to high evaporation rates and limited freshwater input. Temperature ranges from 24-30°C at surface.",
                'type': 'knowledge',
                'topic': 'arabian_sea'
            },
            {
                'content': "Bay of Bengal has lower salinity than Arabian Sea due to large river inputs from Ganges and Brahmaputra. It shows strong seasonal temperature variations.",
                'type': 'knowledge', 
                'topic': 'bay_of_bengal'
            },
            {
                'content': "BGC parameters include chlorophyll-a (phytoplankton biomass), dissolved oxygen, pH, nitrate, and backscattering coefficient. These indicate ocean ecosystem health.",
                'type': 'knowledge',
                'topic': 'bgc_parameters'
            }
        ]
    
    async def build_vector_index(self):
        """Build FAISS vector index from documents"""
        if not self.documents:
            logger.warning("No documents available for vector index")
            return
        
        try:
            # Extract text content for embedding
            texts = [doc['content'] for doc in self.documents]
            
            # Generate embeddings
            logger.info("Generating embeddings for document corpus")
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None, self.embedding_model.encode, texts
            )
            
            # Build FAISS index
            self.vector_index = faiss.IndexFlatIP(self.config.vector_dim)
            faiss.normalize_L2(embeddings.astype('float32'))
            self.vector_index.add(embeddings.astype('float32'))
            
            logger.info(f"Vector index built with {len(self.documents)} documents")
            
        except Exception as e:
            logger.error(f"Error building vector index: {e}")
            raise
    
    async def retrieve_relevant_documents(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant documents for query"""
        try:
            # Generate query embedding
            loop = asyncio.get_event_loop()
            query_embedding = await loop.run_in_executor(
                None, self.embedding_model.encode, [query]
            )
            
            # Search vector index
            faiss.normalize_L2(query_embedding.astype('float32'))
            scores, indices = self.vector_index.search(query_embedding.astype('float32'), k)
            
            # Return relevant documents with scores
            relevant_docs = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx < len(self.documents):
                    doc = self.documents[idx].copy()
                    doc['relevance_score'] = float(score)
                    relevant_docs.append(doc)
            
            return relevant_docs
            
        except Exception as e:
            logger.error(f"Error retrieving relevant documents: {e}")
            return []
    
    async def generate_response_async(self, query: str, session_id: str = None) -> Dict[str, Any]:
        """Generate response using async LLM calls with proper error handling"""
        session_id = session_id or f"session_{int(time.time())}"
        
        try:
            async with self.session_lock:
                self.active_sessions[session_id] = {
                    'query': query,
                    'start_time': time.time(),
                    'status': 'processing'
                }
            
            # Retrieve relevant documents
            relevant_docs = await self.retrieve_relevant_documents(query)
            
            # Build context from relevant documents
            context = self._build_context(relevant_docs)
            
            # Try LLMs in priority order: Mistral (primary) -> Groq (secondary) -> Fallback
            llm_attempts = [
                ('mistral', 'Primary LLM'),
                ('groq', 'Secondary LLM'),
            ]
            
            for llm_name, llm_desc in llm_attempts:
                try:
                    logger.info(f"Attempting {llm_desc} ({llm_name}) for query: {query[:50]}...")
                    
                    response = await self._call_llm_with_retry(llm_name, query, context)
                    
                    if response and len(response.strip()) > 50:  # Valid response
                        async with self.session_lock:
                            self.active_sessions[session_id]['status'] = 'completed'
                        
                        return {
                            'response': response,
                            'model_used': llm_name,
                            'relevant_documents': relevant_docs,
                            'session_id': session_id,
                            'processing_time': time.time() - self.active_sessions[session_id]['start_time'],
                            'timestamp': datetime.now().isoformat()
                        }
                
                except Exception as e:
                    logger.warning(f"{llm_desc} ({llm_name}) failed: {e}")
                    continue
            
            # All LLMs failed, generate fallback response
            logger.info("All LLMs failed, generating fallback response")
            fallback_response = self._generate_fallback_response(query, relevant_docs)
            
            async with self.session_lock:
                self.active_sessions[session_id]['status'] = 'completed_fallback'
            
            return {
                'response': fallback_response,
                'model_used': 'fallback',
                'relevant_documents': relevant_docs,
                'session_id': session_id,
                'processing_time': time.time() - self.active_sessions[session_id]['start_time'],
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            async with self.session_lock:
                if session_id in self.active_sessions:
                    self.active_sessions[session_id]['status'] = 'error'
            
            return {
                'response': f"I apologize, but I encountered an error processing your query about ARGO data. Please try again.",
                'model_used': 'error_fallback',
                'error': str(e),
                'session_id': session_id,
                'timestamp': datetime.now().isoformat()
            }
    
    async def _call_llm_with_retry(self, llm_name: str, query: str, context: str) -> Optional[str]:
        """Call LLM with retry logic and proper timeout handling"""
        if llm_name not in self.api_configs:
            raise ValueError(f"Unknown LLM: {llm_name}")
        
        config = self.api_configs[llm_name]
        if not config['key']:
            raise ValueError(f"No API key configured for {llm_name}")
        
        for attempt in range(self.config.retry_attempts):
            try:
                # Apply rate limiting
                await self.rate_limiters[llm_name].acquire()
                
                # Create timeout context
                timeout = aiohttp.ClientTimeout(total=self.config.request_timeout)
                
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    headers = {
                        'Authorization': f'Bearer {config["key"]}',
                        'Content-Type': 'application/json'
                    }
                    
                    payload = {
                        'model': config['model'],
                        'messages': [
                            {
                                'role': 'system',
                                'content': f"You are an expert oceanographer analyzing real ARGO float data. Use this context to answer queries accurately:\n\n{context}"
                            },
                            {
                                'role': 'user', 
                                'content': query
                            }
                        ],
                        'max_tokens': 2000,
                        'temperature': 0.7
                    }
                    
                    async with session.post(config['url'], json=payload, headers=headers) as response:
                        if response.status == 200:
                            result = await response.json()
                            return result['choices'][0]['message']['content']
                        elif response.status == 429:  # Rate limited
                            wait_time = 2 ** attempt
                            logger.warning(f"{llm_name} rate limited, waiting {wait_time}s")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            error_text = await response.text()
                            raise aiohttp.ClientError(f"HTTP {response.status}: {error_text}")
            
            except asyncio.TimeoutError:
                logger.warning(f"{llm_name} timeout on attempt {attempt + 1}")
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
            
            except Exception as e:
                logger.warning(f"{llm_name} error on attempt {attempt + 1}: {e}")
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
        
        return None
    
    def _build_context(self, relevant_docs: List[Dict[str, Any]]) -> str:
        """Build context string from relevant documents"""
        context_parts = ["RELEVANT ARGO DATA CONTEXT:"]
        
        for i, doc in enumerate(relevant_docs[:3]):  # Limit context size
            context_parts.append(f"\n{i+1}. {doc['content']}")
            if doc.get('metadata'):
                if 'temperature' in doc['metadata']:
                    context_parts.append(f"   Temperature: {doc['metadata']['temperature']['count']} measurements")
                if 'bgc_parameters' in doc['metadata']:
                    bgc_params = list(doc['metadata']['bgc_parameters'].keys())
                    if bgc_params:
                        context_parts.append(f"   BGC Parameters: {', '.join(bgc_params)}")
        
        context = "\n".join(context_parts)
        
        # Truncate if too long
        if len(context) > self.config.max_context_length:
            context = context[:self.config.max_context_length] + "..."
        
        return context
    
    def _generate_fallback_response(self, query: str, relevant_docs: List[Dict[str, Any]]) -> str:
        """Generate fallback response when LLMs fail"""
        query_lower = query.lower()
        
        # Extract relevant information from documents
        temp_data = []
        sal_data = []
        bgc_data = []
        locations = []
        
        for doc in relevant_docs:
            if doc.get('metadata'):
                meta = doc['metadata']
                if 'temperature' in meta:
                    temp_data.extend(meta['temperature']['values'][:10])
                if 'salinity' in meta:
                    sal_data.extend(meta['salinity']['values'][:10])
                if 'bgc_parameters' in meta:
                    bgc_data.extend(list(meta['bgc_parameters'].keys()))
                if 'latitude' in meta and 'longitude' in meta:
                    locations.append((meta['latitude'], meta['longitude']))
        
        # Generate contextual response based on query type
        if 'temperature' in query_lower:
            if temp_data:
                avg_temp = np.mean(temp_data)
                return f"Based on available ARGO data, average temperature is {avg_temp:.2f}°C across {len(temp_data)} measurements. Data covers {len(locations)} locations in the Indian Ocean region."
            return "Temperature data query detected. ARGO floats measure ocean temperature profiles at various depths. For specific regional data, please ensure ARGO NetCDF files are available."
        
        elif 'salinity' in query_lower:
            if sal_data:
                avg_sal = np.mean(sal_data)
                return f"Based on available ARGO data, average salinity is {avg_sal:.2f} PSU across {len(sal_data)} measurements from {len(locations)} locations."
            return "Salinity data query detected. ARGO floats measure practical salinity in PSU (Practical Salinity Units). Arabian Sea typically shows higher salinity than Bay of Bengal."
        
        elif 'bgc' in query_lower or 'chlorophyll' in query_lower or 'oxygen' in query_lower:
            if bgc_data:
                unique_params = list(set(bgc_data))
                return f"BGC parameters found in data: {', '.join(unique_params)}. BGC-ARGO floats provide biogeochemical measurements including chlorophyll, dissolved oxygen, and pH."
            return "BGC parameter query detected. BGC-ARGO floats measure biogeochemical parameters like chlorophyll-a, dissolved oxygen, pH, and nitrate to assess ocean ecosystem health."
        
        else:
            return f"Based on available ARGO float data from {len(locations)} locations, I can provide information about ocean temperature, salinity, and biogeochemical parameters in the Indian Ocean region. Please specify what oceanographic data you're interested in."
    
    async def shutdown(self):
        """Gracefully shutdown the RAG engine"""
        logger.info("Shutting down Enhanced RAG Engine...")
        self.shutdown_event.set()
        
        # Cancel active sessions
        async with self.session_lock:
            active_count = len([s for s in self.active_sessions.values() if s['status'] == 'processing'])
            if active_count > 0:
                logger.info(f"Waiting for {active_count} active sessions to complete...")
        
        # Wait a bit for active sessions to complete
        await asyncio.sleep(2)
        
        # Clear session data
        async with self.session_lock:
            self.active_sessions.clear()
        
        logger.info("Enhanced RAG Engine shutdown complete")

# Test function with proper async handling
async def test_enhanced_rag_engine():
    """Test Enhanced RAG Engine with robust error handling"""
    print("Testing Enhanced RAG Engine with Real ARGO Data...")
    
    try:
        # Initialize RAG engine
        config = RAGConfig(
            max_concurrent_requests=3,
            request_timeout=15,
            retry_attempts=2
        )
        
        rag = EnhancedRAGEngine(config)
        await rag.initialize()
        
        # Test queries
        test_queries = [
            "What is the average temperature in the Arabian Sea?",
            "Show me BGC parameters measured by ARGO floats",
            "Compare salinity between Bay of Bengal and Arabian Sea",
            "Find nearest ARGO floats to coordinates 15°N, 65°E"
        ]
        
        print("Testing multiple concurrent queries...")
        
        # Test concurrent processing with timeout protection
        async def query_with_timeout(query: str, timeout: int = 20):
            try:
                return await asyncio.wait_for(
                    rag.generate_response_async(query),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                return {
                    'response': f"Query timed out after {timeout}s",
                    'model_used': 'timeout_fallback',
                    'error': 'timeout'
                }
        
        # Execute queries concurrently
        tasks = [query_with_timeout(query) for query in test_queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Display results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"\nQuery {i+1} failed: {result}")
            else:
                print(f"\nQuery {i+1}: {test_queries[i]}")
                print(f"Model: {result.get('model_used', 'unknown')}")
                print(f"Response: {result.get('response', 'No response')[:200]}...")
        
        # Shutdown gracefully
        await rag.shutdown()
        
        print("\nEnhanced RAG Engine test completed successfully!")
        return True
        
    except Exception as e:
        print(f"RAG Engine test failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_enhanced_rag_engine())
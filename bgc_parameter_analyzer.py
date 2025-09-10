#!/usr/bin/env python3
"""
BGC Parameter Analyzer - Clean Version
Problem Statement ID: 25040 (MoES/INCOIS)
Focus: Bio-Geo-Chemical parameters analysis for Indian Ocean ecosystem health
"""

import streamlit as st
import requests
import json
import os
import uuid
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import tempfile
import io

# Core imports
import pandas as pd
import numpy as np
import pymongo
from minio import Minio
import chromadb
from sentence_transformers import SentenceTransformer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BGCParameterAnalyzer:
    """BGC Parameter Analyzer for Marine Ecosystem Health Assessment"""
    
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        
        # MongoDB Atlas Connection
        self.mongo_uri = "mongodb+srv://aryan:aryan@cluster0.7iquw6v.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
        self.setup_mongodb()
        
        # MinIO Configuration
        self.setup_minio()
        
        # ChromaDB for RAG
        self.setup_chromadb()
        
        # LLM Configuration
        self.mistral_api_key = "N2bqw2hCeoJFPh7CdGwacLGspAm6PU2x"
        
        # BGC Data Sources
        self.bgc_sources = {
            'bgc_index': 'https://data-argo.ifremer.fr/argo_bio-profile_index.txt',
            'synthetic_profiles': 'https://data-argo.ifremer.fr/argo_synthetic-profile_index.txt'
        }
        
        # Indian Ocean BGC Focus Areas
        self.indian_ocean_regions = {
            'arabian_sea': {'lat': (8, 28), 'lon': (50, 78), 'ecosystem': 'Upwelling system'},
            'bay_of_bengal': {'lat': (5, 25), 'lon': (78, 100), 'ecosystem': 'River-influenced basin'},
            'equatorial_indian': {'lat': (-10, 10), 'lon': (50, 100), 'ecosystem': 'Equatorial upwelling'},
            'southern_indian': {'lat': (-40, -10), 'lon': (30, 120), 'ecosystem': 'Subtropical gyre'}
        }
        
        # BGC Parameters
        self.bgc_parameters = {
            'DOXY': {
                'name': 'Dissolved Oxygen',
                'units': 'µmol/kg',
                'healthy_range': (200, 350),
                'critical_low': 100,
                'ecosystem_role': 'Respiration, hypoxia indicator'
            },
            'CHLA': {
                'name': 'Chlorophyll-a',
                'units': 'mg/m³',
                'healthy_range': (0.1, 2.0),
                'critical_high': 10.0,
                'ecosystem_role': 'Primary productivity, phytoplankton biomass'
            },
            'BBP700': {
                'name': 'Backscattering 700nm',
                'units': 'm⁻¹',
                'healthy_range': (0.0001, 0.01),
                'critical_high': 0.05,
                'ecosystem_role': 'Particle concentration, turbidity'
            },
            'PH_IN_SITU_TOTAL': {
                'name': 'pH (Total Scale)',
                'units': 'pH units',
                'healthy_range': (7.9, 8.2),
                'critical_low': 7.7,
                'ecosystem_role': 'Ocean acidification, carbonate chemistry'
            },
            'NITRATE': {
                'name': 'Nitrate',
                'units': 'µmol/kg',
                'healthy_range': (0, 30),
                'critical_high': 50,
                'ecosystem_role': 'Nutrient availability, eutrophication'
            }
        }
        
        # Health thresholds
        self.health_thresholds = {
            'excellent': 90,
            'good': 70,
            'fair': 50,
            'poor': 30,
            'critical': 10
        }
        
        # Data storage
        self.bgc_profiles = []
        self.ecosystem_assessments = []
        self.processed_files = []
        
    def setup_mongodb(self):
        """Setup MongoDB Atlas connection"""
        try:
            self.mongo_client = pymongo.MongoClient(self.mongo_uri)
            self.db = self.mongo_client.floatchat_bgc
            
            # Create collections
            self.profiles_collection = self.db.bgc_profiles
            self.assessments_collection = self.db.ecosystem_assessments
            
            # Test connection
            self.mongo_client.server_info()
            logger.info("✅ MongoDB Atlas connected successfully")
            
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            self.db = None
    
    def setup_minio(self):
        """Setup MinIO connection"""
        try:
            self.minio_client = Minio(
                "127.0.0.1:9000",
                access_key="minioadmin",
                secret_key="minioadmin",
                secure=False
            )
            
            # Create bucket for BGC data
            self.bucket_name = "bgc1"
            if not self.minio_client.bucket_exists(self.bucket_name):
                self.minio_client.make_bucket(self.bucket_name)
            
            logger.info("✅ MinIO connected successfully")
            
        except Exception as e:
            logger.error(f"❌ MinIO connection failed: {e}")
            self.minio_client = None
    
    def setup_chromadb(self):
        """Setup ChromaDB for RAG"""
        try:
            self.chroma_client = chromadb.PersistentClient(path="data/chroma_bgc")
            self.rag_collection_db = self.chroma_client.get_or_create_collection("bgc_data")
            
            # Load embedding model
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            logger.info("✅ ChromaDB initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ ChromaDB setup failed: {e}")
            self.rag_collection_db = None
    
    def extract_bgc_index_data(self) -> Dict[str, Any]:
        """Extract BGC data from ARGO BGC index"""
        logger.info("Extracting BGC data from ARGO BGC index...")
        
        extraction_results = {
            'bgc_profiles_found': 0,
            'indian_ocean_bgc': 0,
            'bgc_parameters_detected': set(),
            'regions_covered': set(),
            'float_ids': set()
        }
        
        try:
            # Download ARGO BGC index
            response = requests.get(self.bgc_sources['bgc_index'], timeout=60)
            if response.status_code != 200:
                logger.error("Failed to download ARGO BGC index")
                return extraction_results
            
            # Parse BGC index file
            lines = response.text.strip().split('\n')
            if len(lines) < 2:
                logger.error("Invalid ARGO BGC index format")
                return extraction_results
            
            # Process BGC profiles (limit for development)
            for line in lines[1:21]:  # Process first 20 for development
                try:
                    data = line.split(',')
                    if len(data) < 8:
                        continue
                    
                    extraction_results['bgc_profiles_found'] += 1
                    
                    # Extract coordinates
                    lat = float(data[2])
                    lon = float(data[3])
                    
                    # Check if in Indian Ocean
                    if self.is_indian_ocean_location(lat, lon):
                        extraction_results['indian_ocean_bgc'] += 1
                        
                        # Extract BGC parameters
                        parameters_str = data[7] if len(data) > 7 else ''
                        bgc_params = self.extract_bgc_parameters_from_string(parameters_str)
                        extraction_results['bgc_parameters_detected'].update(bgc_params)
                        
                        # Create BGC profile record
                        bgc_profile = {
                            'file_path': data[0],
                            'date_str': data[1],
                            'latitude': lat,
                            'longitude': lon,
                            'ocean': data[4] if len(data) > 4 else 'Unknown',
                            'profiler_type': data[5] if len(data) > 5 else 'Unknown',
                            'institution': data[6] if len(data) > 6 else 'Unknown',
                            'parameters': parameters_str,
                            'bgc_parameters': bgc_params,
                            'region': self.identify_region(lat, lon),
                            'ecosystem_type': self.indian_ocean_regions.get(
                                self.identify_region(lat, lon).lower().replace(' ', '_'), {}
                            ).get('ecosystem', 'Unknown'),
                            'data_source': 'argo_bgc_index',
                            'extraction_time': datetime.now(),
                            'profile_date': self.parse_argo_date(data[1]),
                            'float_id': self.extract_float_id(data[0])
                        }
                        
                        self.bgc_profiles.append(bgc_profile)
                        extraction_results['regions_covered'].add(bgc_profile['region'])
                        extraction_results['float_ids'].add(bgc_profile['float_id'])
                        
                except Exception as e:
                    logger.debug(f"Error processing BGC profile line: {e}")
                    continue
            
            # Store data if any profiles found
            if self.bgc_profiles:
                self.store_bgc_data_in_mongodb()
                self.upload_bgc_data_to_minio()
                self.create_rag_embeddings()
            
            logger.info(f"BGC extraction complete: {extraction_results['indian_ocean_bgc']} Indian Ocean BGC profiles")
            return extraction_results
            
        except Exception as e:
            logger.error(f"BGC index extraction failed: {e}")
            return extraction_results
    
    def extract_bgc_parameters_from_string(self, params_str: str) -> List[str]:
        """Extract BGC parameters from parameter string"""
        bgc_params = []
        for param in self.bgc_parameters.keys():
            if param in params_str or param.replace('_', '') in params_str:
                bgc_params.append(param)
        return bgc_params
    
    def create_sample_ecosystem_assessments(self):
        """Create sample ecosystem assessments for demonstration"""
        logger.info("Creating sample ecosystem assessments...")
        
        regions = ['Arabian Sea', 'Bay Of Bengal', 'Equatorial Indian', 'Southern Indian']
        
        for region in regions:
            # Generate sample BGC measurements
            sample_measurements = {}
            
            for param, param_info in self.bgc_parameters.items():
                min_val, max_val = param_info['healthy_range']
                
                # Generate realistic values based on region
                if region == 'Arabian Sea':
                    if param == 'DOXY':
                        value = np.random.uniform(150, 300)  # Lower oxygen due to upwelling
                    elif param == 'CHLA':
                        value = np.random.uniform(0.5, 3.0)  # Higher productivity
                    else:
                        value = np.random.uniform(min_val, max_val)
                elif region == 'Bay Of Bengal':
                    if param == 'DOXY':
                        value = np.random.uniform(100, 250)  # Lower due to stratification
                    elif param == 'CHLA':
                        value = np.random.uniform(0.2, 1.5)  # Moderate productivity
                    else:
                        value = np.random.uniform(min_val, max_val)
                else:
                    value = np.random.uniform(min_val, max_val)
                
                health_assessment = self.assess_parameter_health(param, value, param_info)
                
                sample_measurements[param] = {
                    'values': [value] * 10,  # Sample data
                    'count': 10,
                    'mean': float(value),
                    'std': float(value * 0.1),
                    'min': float(value * 0.9),
                    'max': float(value * 1.1),
                    'units': param_info['units'],
                    'health_assessment': health_assessment
                }
            
            # Create ecosystem health assessment
            lat = np.random.uniform(-10, 25)
            lon = np.random.uniform(50, 100)
            ecosystem_health = self.assess_ecosystem_health(sample_measurements, lat, lon)
            
            # Create assessment record
            assessment = {
                'assessment_id': f"bgc_{self.session_id}_{len(self.ecosystem_assessments)}",
                'float_id': f"SAMPLE_{region.replace(' ', '_').upper()}",
                'region': region,
                'ecosystem_type': self.indian_ocean_regions.get(
                    region.lower().replace(' ', '_'), {}
                ).get('ecosystem', 'Unknown'),
                'location': {'lat': lat, 'lon': lon},
                'assessment_time': datetime.now(),
                'health_score': ecosystem_health['overall_score'],
                'health_status': ecosystem_health['status'],
                'parameter_scores': ecosystem_health['parameter_scores'],
                'recommendations': ecosystem_health['recommendations'],
                'assessment_location': f"{lat:.2f}°N, {lon:.2f}°E",
                'parameters_assessed': len(ecosystem_health['parameter_scores'])
            }
            
            self.ecosystem_assessments.append(assessment)
        
        logger.info(f"Created {len(self.ecosystem_assessments)} sample ecosystem assessments")
    
    def assess_parameter_health(self, param: str, value: float, param_info: Dict) -> Dict:
        """Assess health of individual BGC parameter"""
        min_healthy, max_healthy = param_info['healthy_range']
        
        if min_healthy <= value <= max_healthy:
            score = 100
            status = "Excellent"
        elif param == 'DOXY' and value < param_info.get('critical_low', 0):
            score = 10
            status = "Critical - Hypoxic"
        elif param in ['CHLA', 'BBP700', 'NITRATE'] and value > param_info.get('critical_high', float('inf')):
            score = 20
            status = "Poor - Elevated"
        elif param == 'PH_IN_SITU_TOTAL' and value < param_info.get('critical_low', 0):
            score = 15
            status = "Critical - Acidified"
        else:
            # Calculate score based on distance from healthy range
            if value < min_healthy:
                score = max(30, 100 - (min_healthy - value) / min_healthy * 100)
            else:
                score = max(30, 100 - (value - max_healthy) / max_healthy * 100)
            
            if score >= 70:
                status = "Good"
            elif score >= 50:
                status = "Fair"
            else:
                status = "Poor"
        
        return {
            'score': round(score, 1),
            'status': status,
            'value': value,
            'healthy_range': param_info['healthy_range'],
            'ecosystem_role': param_info['ecosystem_role']
        }
    
    def assess_ecosystem_health(self, bgc_measurements: Dict, lat: float, lon: float) -> Dict:
        """Assess overall ecosystem health from BGC measurements"""
        parameter_scores = {}
        total_score = 0
        param_count = 0
        
        # Calculate individual parameter scores
        for param, measurement in bgc_measurements.items():
            if param in self.bgc_parameters:
                health_assessment = measurement.get('health_assessment', {})
                
                if 'score' in health_assessment:
                    parameter_scores[param] = health_assessment
                    total_score += health_assessment['score']
                    param_count += 1
        
        # Calculate overall score
        overall_score = total_score / param_count if param_count > 0 else 0
        
        # Determine health status
        if overall_score >= self.health_thresholds['excellent']:
            status = "Excellent"
            color = "green"
        elif overall_score >= self.health_thresholds['good']:
            status = "Good"
            color = "lightgreen"
        elif overall_score >= self.health_thresholds['fair']:
            status = "Fair"
            color = "yellow"
        elif overall_score >= self.health_thresholds['poor']:
            status = "Poor"
            color = "orange"
        else:
            status = "Critical"
            color = "red"
        
        # Generate recommendations
        recommendations = self.generate_ecosystem_recommendations(parameter_scores, overall_score)
        
        return {
            'overall_score': round(overall_score, 1),
            'status': status,
            'color': color,
            'parameter_scores': parameter_scores,
            'recommendations': recommendations,
            'assessment_location': f"{lat:.2f}°N, {lon:.2f}°E",
            'parameters_assessed': len(parameter_scores)
        }
    
    def generate_ecosystem_recommendations(self, parameter_scores: Dict, overall_score: float) -> List[str]:
        """Generate ecosystem management recommendations"""
        recommendations = []
        
        # Check for specific parameter issues
        for param, assessment in parameter_scores.items():
            if assessment['score'] < 50:
                if param == 'DOXY':
                    recommendations.append("Monitor for hypoxic conditions and potential dead zones")
                elif param == 'CHLA':
                    if assessment['value'] > self.bgc_parameters[param]['healthy_range'][1]:
                        recommendations.append("High chlorophyll indicates potential eutrophication")
                    else:
                        recommendations.append("Low chlorophyll suggests limited primary productivity")
                elif param == 'PH_IN_SITU_TOTAL':
                    recommendations.append("Ocean acidification monitoring and carbonate system assessment needed")
                elif param == 'NITRATE':
                    recommendations.append("Nutrient management and pollution source control required")
        
        # Overall recommendations based on health score
        if overall_score < 30:
            recommendations.append("Immediate ecosystem intervention and monitoring required")
        elif overall_score < 50:
            recommendations.append("Enhanced monitoring and precautionary measures recommended")
        elif overall_score < 70:
            recommendations.append("Regular monitoring to prevent degradation")
        else:
            recommendations.append("Maintain current conservation efforts")
        
        return recommendations
    
    def is_indian_ocean_location(self, lat: float, lon: float) -> bool:
        """Check if coordinates are in Indian Ocean"""
        return (-50 <= lat <= 30) and (20 <= lon <= 120)
    
    def identify_region(self, lat: float, lon: float) -> str:
        """Identify specific Indian Ocean region"""
        for region, bounds in self.indian_ocean_regions.items():
            if (bounds['lat'][0] <= lat <= bounds['lat'][1] and 
                bounds['lon'][0] <= lon <= bounds['lon'][1]):
                return region.replace('_', ' ').title()
        return 'Indian Ocean General'
    
    def parse_argo_date(self, date_str: str) -> Optional[datetime]:
        """Parse ARGO date string"""
        try:
            return datetime.strptime(date_str, '%Y%m%d%H%M%S')
        except:
            return None
    
    def extract_float_id(self, file_path: str) -> str:
        """Extract float ID from file path"""
        try:
            return file_path.split('/')[-1].split('_')[0]
        except:
            return 'Unknown'
    
    def store_bgc_data_in_mongodb(self):
        """Store BGC data in MongoDB Atlas"""
        if not self.db:
            return
        
        try:
            # Store BGC profiles
            profile_docs = []
            for profile in self.bgc_profiles:
                doc = {
                    'session_id': self.session_id,
                    'float_id': profile.get('float_id', 'unknown'),
                    'region': profile.get('region', 'Unknown'),
                    'ecosystem_type': profile.get('ecosystem_type', 'Unknown'),
                    'data_source': profile.get('data_source', 'bgc'),
                    'bgc_parameters': ', '.join(profile.get('bgc_parameters', [])),
                    'institution': profile.get('institution', ''),
                    'location_summary': f"{profile.get('latitude', 0):.2f}N {profile.get('longitude', 0):.2f}E",
                    'extraction_time': profile.get('extraction_time', datetime.now()),
                    'text_summary': self.create_bgc_profile_summary(profile)
                }
                profile_docs.append(doc)
            
            # Store ecosystem assessments
            assessment_docs = []
            for assessment in self.ecosystem_assessments:
                doc = {
                    'session_id': self.session_id,
                    'assessment_id': assessment['assessment_id'],
                    'float_id': assessment['float_id'],
                    'region': assessment['region'],
                    'ecosystem_type': assessment['ecosystem_type'],
                    'health_score': assessment['health_score'],
                    'health_status': assessment['health_status'],
                    'assessment_time': assessment['assessment_time'],
                    'location_summary': assessment['assessment_location'],
                    'recommendations_summary': '; '.join(assessment['recommendations'][:3])
                }
                assessment_docs.append(doc)
            
            # Insert into MongoDB
            if profile_docs:
                self.profiles_collection.insert_many(profile_docs)
                logger.info(f"Stored {len(profile_docs)} BGC profiles in MongoDB")
            
            if assessment_docs:
                self.assessments_collection.insert_many(assessment_docs)
                logger.info(f"Stored {len(assessment_docs)} ecosystem assessments in MongoDB")
                
        except Exception as e:
            logger.error(f"MongoDB storage failed: {e}")
    
    def create_bgc_profile_summary(self, profile: Dict) -> str:
        """Create text summary for BGC profile"""
        summary = f"BGC Profile: {profile.get('region', 'Indian Ocean')} "
        summary += f"Ecosystem: {profile.get('ecosystem_type', 'Marine')} "
        summary += f"Location: {profile.get('latitude', 0):.2f}N {profile.get('longitude', 0):.2f}E "
        summary += f"Institution: {profile.get('institution', 'ARGO')} "
        summary += f"BGC Parameters: {', '.join(profile.get('bgc_parameters', []))} "
        if profile.get('profile_date'):
            summary += f"Date: {profile['profile_date'].strftime('%Y-%m-%d')} "
        summary += f"Source: {profile.get('data_source', 'BGC Float')}"
        return summary
    
    def upload_bgc_data_to_minio(self):
        """Upload BGC data to MinIO"""
        if not self.minio_client:
            return
        
        try:
            # Create comprehensive BGC data file
            upload_data = {
                'extraction_session': self.session_id,
                'extraction_time': datetime.now().isoformat(),
                'summary': {
                    'total_bgc_profiles': len(self.bgc_profiles),
                    'processed_files': len(self.processed_files),
                    'ecosystem_assessments': len(self.ecosystem_assessments),
                    'regions_covered': list(set(p.get('region', 'Unknown') for p in self.bgc_profiles))
                },
                'bgc_profiles': self.bgc_profiles,
                'processed_files': self.processed_files,
                'ecosystem_assessments': self.ecosystem_assessments
            }
            
            # Upload main BGC data file
            json_bytes = json.dumps(upload_data, default=str).encode('utf-8')
            self.minio_client.put_object(
                self.bucket_name,
                f"bgc_extracted_{self.session_id}.json",
                io.BytesIO(json_bytes),
                len(json_bytes),
                content_type="application/json"
            )
            
            logger.info("BGC data uploaded to MinIO successfully")
            
        except Exception as e:
            logger.error(f"MinIO upload failed: {e}")
    
    def create_rag_embeddings(self):
        """Create RAG embeddings for BGC data"""
        if not self.rag_collection_db:
            return
        
        try:
            documents = []
            metadatas = []
            ids = []
            
            # Create embeddings for BGC profiles
            for i, profile in enumerate(self.bgc_profiles):
                doc_text = f"""
                BGC Float Profile from {profile.get('region', 'Indian Ocean')}
                Ecosystem Type: {profile.get('ecosystem_type', 'Marine ecosystem')}
                Location: {profile.get('latitude', 0):.2f}°N, {profile.get('longitude', 0):.2f}°E
                Institution: {profile.get('institution', 'ARGO Network')}
                BGC Parameters: {', '.join(profile.get('bgc_parameters', []))}
                Float ID: {profile.get('float_id', 'Unknown')}
                Date: {profile.get('profile_date', datetime.now()).strftime('%Y-%m-%d') if profile.get('profile_date') else 'Recent'}
                
                This BGC profile provides essential measurements for assessing marine ecosystem health.
                """
                
                documents.append(doc_text.strip())
                metadatas.append({
                    'type': 'bgc_profile',
                    'region': str(profile.get('region', 'Indian Ocean')),
                    'ecosystem_type': str(profile.get('ecosystem_type', 'Marine')),
                    'float_id': str(profile.get('float_id', 'Unknown')),
                    'bgc_parameters': ', '.join(profile.get('bgc_parameters', []))
                })
                ids.append(f"bgc_profile_{self.session_id}_{i}")
            
            # Create embeddings for ecosystem assessments
            for i, assessment in enumerate(self.ecosystem_assessments):
                doc_text = f"""
                Ecosystem Health Assessment for {assessment['region']}
                Location: {assessment['assessment_location']}
                Overall Health Score: {assessment['health_score']}/100
                Health Status: {assessment['health_status']}
                
                This assessment provides ecosystem health evaluation based on BGC measurements.
                """
                
                documents.append(doc_text.strip())
                metadatas.append({
                    'type': 'ecosystem_assessment',
                    'region': str(assessment['region']),
                    'health_score': assessment['health_score'],
                    'health_status': str(assessment['health_status']),
                    'assessment_id': str(assessment['assessment_id'])
                })
                ids.append(f"ecosystem_assessment_{self.session_id}_{i}")
            
            # Add to ChromaDB
            if documents:
                self.rag_collection_db.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                
                logger.info(f"Created {len(documents)} BGC RAG embeddings")
                
        except Exception as e:
            logger.error(f"RAG embedding creation failed: {e}")
    
    def extract_all_bgc_data(self) -> Dict[str, Any]:
        """Extract all BGC data sources"""
        logger.info("Starting comprehensive BGC data extraction...")
        
        total_results = {
            'total_bgc_profiles': 0,
            'total_assessments': 0,
            'total_processed_files': 0,
            'sources_processed': [],
            'extraction_errors': []
        }
        
        try:
            # Extract from BGC index
            index_results = self.extract_bgc_index_data()
            total_results['total_bgc_profiles'] += index_results['indian_ocean_bgc']
            total_results['sources_processed'].append('ARGO BGC Index')
            
            # Create sample ecosystem assessments for demo
            self.create_sample_ecosystem_assessments()
            total_results['total_assessments'] = len(self.ecosystem_assessments)
            total_results['sources_processed'].append('Sample Ecosystem Assessments')
            
            logger.info(f"BGC extraction complete: {total_results['total_bgc_profiles']} profiles, {total_results['total_assessments']} assessments")
            return total_results
            
        except Exception as e:
            logger.error(f"BGC data extraction failed: {e}")
            total_results['extraction_errors'].append(str(e))
            return total_results
    
    def query_with_rag(self, user_query: str) -> Dict[str, Any]:
        """Query BGC data using RAG system"""
        try:
            if not self.rag_collection_db:
                return {
                    'success': False,
                    'response': "RAG system not available."
                }
            
            # Query ChromaDB
            results = self.rag_collection_db.query(
                query_texts=[user_query],
                n_results=5
            )
            
            if not results['documents'][0]:
                return {
                    'success': False,
                    'response': "No relevant BGC data found for your query.",
                    'suggestion': "Try extracting more BGC data or use web search."
                }
            
            # Generate response using Mistral LLM
            context = "\n\n".join(results['documents'][0])
            response = self.generate_llm_response(user_query, context, 'bgc_data')
            
            return {
                'success': True,
                'response': response,
                'data_sources': len(results['documents'][0]),
                'metadata': results['metadatas'][0]
            }
            
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            return {
                'success': False,
                'response': f"Query processing failed: {str(e)}"
            }
    
    def generate_llm_response(self, query: str, context: str, task_type: str) -> str:
        """Generate LLM response using Mistral API"""
        try:
            # Task-specific prompts
            if task_type == 'bgc_data':
                system_prompt = """You are an expert marine ecologist analyzing BGC (Bio-Geo-Chemical) data from ARGO floats.
                
                Instructions:
                - Provide scientific analysis based on authentic BGC measurements
                - Focus on ecosystem health assessments and marine biogeochemistry
                - Include specific parameter values and health scores when available
                - Explain the ecological significance of BGC parameters
                - Discuss ecosystem health status and management implications
                - Reference ARGO BGC float capabilities and limitations"""
                
                user_prompt = f"""Query: {query}
                
                Real BGC Data Context:
                {context}
                
                Provide detailed marine ecosystem analysis based on this authentic BGC data."""
            
            elif task_type == 'web_search':
                system_prompt = """You are a marine biogeochemistry expert providing comprehensive web-based information.
                
                Instructions:
                - Use current marine biogeochemistry knowledge
                - Focus on Indian Ocean ecosystems when relevant
                - Include information about BGC parameters and their ecological roles
                - Discuss ecosystem health indicators and assessment methods
                - Provide context about ARGO BGC float observations"""
                
                user_prompt = f"""Provide comprehensive marine biogeochemistry information about: {query}
                
                Include current research on ecosystem health, BGC parameters, and monitoring methods."""
            
            # Call Mistral API
            headers = {
                'Authorization': f'Bearer {self.mistral_api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': 'mistral-medium',
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ],
                'max_tokens': 800,
                'temperature': 0.3
            }
            
            response = requests.post(
                'https://api.mistral.ai/v1/chat/completions',
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                return "LLM service temporarily unavailable. Please try again."
                
        except Exception as e:
            logger.error(f"LLM response generation failed: {e}")
            return "Unable to generate response at this time."
    
    def web_search_response(self, query: str) -> str:
        """Generate web search response"""
        return self.generate_llm_response(query, "", 'web_search')


def create_bgc_interface():
    """Create Streamlit interface for BGC parameter analyzer"""
    st.title("🧬 BGC Parameter Analyzer")
    st.markdown("**Marine Ecosystem Health Assessment - Indian Ocean Focus**")
    
    # Initialize system
    if 'bgc_system' not in st.session_state:
        st.session_state.bgc_system = BGCParameterAnalyzer()
    
    system = st.session_state.bgc_system
    
    # Sidebar
    with st.sidebar:
        st.header("📊 BGC System Status")
        
        # Connection status
        mongo_status = "✅ Connected" if system.db else "❌ Disconnected"
        minio_status = "✅ Connected" if system.minio_client else "❌ Disconnected"
        rag_status = "✅ Ready" if system.rag_collection_db else "❌ Not Ready"
        
        st.write(f"MongoDB: {mongo_status}")
        st.write(f"MinIO: {minio_status}")
        st.write(f"RAG System: {rag_status}")
        
        # Data extraction options
        st.header("🔄 BGC Data Extraction")
        
        if st.button("🧬 Extract All BGC Data"):
            with st.spinner("Extracting BGC data and assessing ecosystem health..."):
                results = system.extract_all_bgc_data()
                st.success(f"Extracted {results['total_bgc_profiles']} BGC profiles")
                st.success(f"Created {results['total_assessments']} ecosystem assessments")
                st.info(f"Sources: {', '.join(results['sources_processed'])}")
        
        # Individual extractions
        if st.button("📋 BGC Index Only"):
            with st.spinner("Extracting from ARGO BGC index..."):
                results = system.extract_bgc_index_data()
                st.success(f"Found {results['indian_ocean_bgc']} Indian Ocean BGC profiles")
                st.info(f"Parameters: {', '.join(results['bgc_parameters_detected'])}")
        
        # BGC parameters info
        st.header("🧪 BGC Parameters")
        for param, info in system.bgc_parameters.items():
            with st.expander(f"{param} - {info['name']}"):
                st.write(f"**Units:** {info['units']}")
                st.write(f"**Healthy Range:** {info['healthy_range']}")
                st.write(f"**Role:** {info['ecosystem_role']}")
        
        # Quick stats
        if system.bgc_profiles or system.ecosystem_assessments:
            st.header("📈 Quick Stats")
            st.metric("BGC Profiles", len(system.bgc_profiles))
            st.metric("Assessments", len(system.ecosystem_assessments))
            st.metric("Processed Files", len(system.processed_files))
    
    # Main interface
    st.header("🤖 BGC Data Query & Ecosystem Health Analysis")
    
    # Query input
    query = st.text_area(
        "Ask about BGC parameters and ecosystem health:",
        placeholder="What is the ecosystem health in Arabian Sea?\nShow me dissolved oxygen levels from BGC floats\nHow are chlorophyll levels affecting marine productivity?\nAssess ocean acidification in Bay of Bengal",
        height=100
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔍 Query BGC Data", type="primary"):
            if query:
                with st.spinner("Analyzing BGC data and ecosystem health..."):
                    result = system.query_with_rag(query)
                    
                    if result['success']:
                        st.subheader("📊 BGC Analysis Response")
                        st.markdown(result['response'])
                        st.caption(f"Sources: {result.get('data_sources', 0)} BGC profiles/assessments")
                        
                        # Show metadata if available
                        if 'metadata' in result and result['metadata']:
                            with st.expander("📋 Data Details"):
                                for i, meta in enumerate(result['metadata']):
                                    st.write(f"**Source {i+1}:** {meta.get('type', 'BGC')} - {meta.get('region', 'Indian Ocean')}")
                                    if 'health_score' in meta:
                                        st.write(f"Health Score: {meta['health_score']}/100")
                    else:
                        st.warning(result['response'])
                        if 'suggestion' in result:
                            st.info(result['suggestion'])
    
    with col2:
        if st.button("🌐 Web Search"):
            if query:
                with st.spinner("Searching marine biogeochemistry knowledge..."):
                    web_response = system.web_search_response(query)
                    
                    st.subheader("🌐 Web Search Results")
                    st.info("Based on broader marine biogeochemistry knowledge")
                    st.markdown(web_response)
    
    # Ecosystem Health Dashboard
    if system.ecosystem_assessments:
        st.subheader("🌊 Ecosystem Health Dashboard")
        
        # Overall health metrics
        all_scores = [a['health_score'] for a in system.ecosystem_assessments]
        avg_health = np.mean(all_scores)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Average Health Score", f"{avg_health:.1f}/100")
        with col2:
            excellent_count = sum(1 for score in all_scores if score >= 90)
            st.metric("Excellent Health", excellent_count)
        with col3:
            poor_count = sum(1 for score in all_scores if score < 50)
            st.metric("Poor Health", poor_count)
        with col4:
            st.metric("Total Assessments", len(system.ecosystem_assessments))
        
        # Health status distribution
        health_status_counts = {}
        for assessment in system.ecosystem_assessments:
            status = assessment['health_status']
            health_status_counts[status] = health_status_counts.get(status, 0) + 1
        
        if health_status_counts:
            st.subheader("Health Status Distribution")
            status_df = pd.DataFrame(list(health_status_counts.items()), columns=['Status', 'Count'])
            st.bar_chart(status_df.set_index('Status'))
        
        # Individual assessments
        st.subheader("Individual Ecosystem Assessments")
        for assessment in system.ecosystem_assessments:
            with st.expander(f"🏝️ {assessment['region']} - {assessment['health_status']} ({assessment['health_score']}/100)"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Ecosystem Type:** {assessment['ecosystem_type']}")
                    st.write(f"**Location:** {assessment['assessment_location']}")
                    st.write(f"**Assessment Time:** {assessment['assessment_time'].strftime('%Y-%m-%d %H:%M')}")
                    st.write(f"**Float ID:** {assessment['float_id']}")
                
                with col2:
                    # Parameter scores
                    st.write("**Parameter Health Scores:**")
                    for param, score_data in assessment['parameter_scores'].items():
                        color = "🟢" if score_data['score'] >= 70 else "🟡" if score_data['score'] >= 50 else "🔴"
                        st.write(f"{color} {param}: {score_data['score']}/100 ({score_data['status']})")
                
                # Recommendations
                if assessment['recommendations']:
                    st.write("**Management Recommendations:**")
                    for rec in assessment['recommendations']:
                        st.write(f"• {rec}")
    
    # BGC Profiles Overview
    if system.bgc_profiles:
        st.subheader("📈 BGC Profiles Overview")
        
        # Create summary
        profile_summary = []
        for profile in system.bgc_profiles:
            profile_summary.append({
                'Float ID': profile.get('float_id', 'Unknown'),
                'Region': profile.get('region', 'Unknown'),
                'Ecosystem Type': profile.get('ecosystem_type', 'Unknown'),
                'BGC Parameters': ', '.join(profile.get('bgc_parameters', [])),
                'Institution': profile.get('institution', 'Unknown')
            })
        
        if profile_summary:
            df = pd.DataFrame(profile_summary)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total BGC Profiles", len(df))
            with col2:
                unique_regions = df['Region'].nunique()
                st.metric("Regions", unique_regions)
            with col3:
                unique_ecosystems = df['Ecosystem Type'].nunique()
                st.metric("Ecosystem Types", unique_ecosystems)
            
            # Regional distribution
            if st.checkbox("Show BGC Regional Distribution"):
                region_counts = df['Region'].value_counts()
                st.bar_chart(region_counts)
            
            # BGC profiles table
            if st.checkbox("Show BGC Profile Details"):
                st.dataframe(df)
    
    # Instructions
    st.markdown("""
    **🎯 BGC Parameter Analyzer Features:**
    - Real BGC float data from ARGO network
    - Ecosystem health assessment algorithms
    - Marine biogeochemistry parameter analysis
    - Indian Ocean regional focus
    - RAG-based intelligent query system
    - Automatic health scoring and recommendations
    - MinIO storage and MongoDB persistence
    - LLM-powered ecological analysis
    """)


if __name__ == "__main__":
    create_bgc_interface()
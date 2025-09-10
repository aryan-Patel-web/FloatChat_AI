#!/usr/bin/env python3
"""
Improved Advanced FTP Handler - Fixed BGC Detection and Enhanced Functionality
"""

import ftplib
import os
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import netCDF4 as nc
import numpy as np
from pathlib import Path
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImprovedAdvancedFTPHandler:
    """Advanced FTP Handler with improved BGC detection and local data integration"""
    
    def __init__(self, 
                 host: str = "ftp.ifremer.fr",
                 max_size_gb: float = 1.0,
                 max_files: int = 100,
                 target_regions: List[str] = None,
                 bgc_enabled: bool = True,
                 download_dir: str = "argo_data"):
        
        self.host = host
        self.max_size_bytes = int(max_size_gb * 1024 * 1024 * 1024)
        self.max_files = max_files
        self.target_regions = target_regions or ['arabian_sea', 'bay_of_bengal', 'indian_ocean_equatorial']
        self.bgc_enabled = bgc_enabled
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        
        # Local data directories to check for existing BGC files
        self.local_data_dirs = [
            Path("D:/FloatChat ARGO/MINIO/data/argo"),
            Path("D:/FloatChat ARGO/MINIO/data/argo_large"),
            Path("D:/FloatChat ARGO/MINIO/data/argo_regional"),
            Path("D:/FloatChat ARGO/MINIO/data/incois"),
            Path("D:/FloatChat ARGO/MINIO/data/processed"),
            Path("data/argo"),
            Path("data/argo_large"),
            Path("data/argo_regional"),
            Path("data/incois"),
            Path("data/processed")
        ]
        
        # Results directories
        self.results_dirs = [
            Path("D:/FloatChat ARGO/MINIO/processed_data"),
            Path("D:/FloatChat ARGO/MINIO/metadata/argo"),
            Path("processed_data"),
            Path("metadata/argo")
        ]
        
        self.regional_bounds = {
            'arabian_sea': {'lat': (10, 30), 'lon': (50, 78)},
            'bay_of_bengal': {'lat': (5, 25), 'lon': (78, 100)},
            'indian_ocean_central': {'lat': (-10, 10), 'lon': (60, 90)},
            'indian_ocean_equatorial': {'lat': (-5, 5), 'lon': (50, 100)},
            'southern_indian_ocean': {'lat': (-40, -10), 'lon': (40, 120)}
        }
        
        # Enhanced BGC parameters with more comprehensive detection
        self.bgc_parameters = {
            'CHLA': {'name': 'Chlorophyll-a', 'units': 'mg/m³'},
            'DOXY': {'name': 'Dissolved Oxygen', 'units': 'µmol/kg'},
            'PH_IN_SITU_TOTAL': {'name': 'pH', 'units': 'pH units'},
            'NITRATE': {'name': 'Nitrate', 'units': 'µmol/kg'},
            'BBP700': {'name': 'Backscattering', 'units': 'm⁻¹'},
            'TPHASE_DOXY': {'name': 'Oxygen Phase', 'units': 'microsec'},
            'FLUORESCENCE_CHLA': {'name': 'Chlorophyll Fluorescence', 'units': 'count'},
            'TEMP_CPU_CHLA': {'name': 'CPU Temperature', 'units': 'degC'},
            'CDOM': {'name': 'Colored Dissolved Organic Matter', 'units': 'ppb'},
            'DOWNWELLING_PAR': {'name': 'Photosynthetic Radiation', 'units': 'µmol/m²/s'}
        }
        
        self.ftp_connection = None
        self.download_stats = {
            'files_downloaded': 0,
            'total_size': 0,
            'bgc_floats_found': 0,
            'local_bgc_files_found': 0,
            'ftp_bgc_files_found': 0,
            'regions_covered': set(),
            'errors': []
        }
    
    def scan_local_bgc_files(self) -> List[Dict[str, Any]]:
        """Scan local directories for existing BGC files first"""
        logger.info("Scanning local directories for existing BGC files...")
        
        local_bgc_files = []
        
        for data_dir in self.local_data_dirs:
            if data_dir.exists():
                logger.info(f"Checking local directory: {data_dir}")
                nc_files = list(data_dir.glob('*.nc'))
                
                for nc_file in nc_files:
                    if self._is_bgc_file(nc_file.name):
                        try:
                            bgc_info = self._analyze_local_bgc_file(nc_file)
                            if bgc_info:
                                local_bgc_files.append(bgc_info)
                                logger.info(f"Local BGC file: {nc_file.name}")
                        except Exception as e:
                            logger.warning(f"Error analyzing local file {nc_file}: {e}")
        
        self.download_stats['local_bgc_files_found'] = len(local_bgc_files)
        logger.info(f"Found {len(local_bgc_files)} local BGC files")
        return local_bgc_files
    
    def _analyze_local_bgc_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Analyze local BGC NetCDF file"""
        try:
            with nc.Dataset(file_path, 'r') as ds:
                variables = list(ds.variables.keys())
                
                # Check for BGC variables
                bgc_vars_found = []
                for var in variables:
                    for bgc_param in self.bgc_parameters.keys():
                        if bgc_param in var:
                            bgc_vars_found.append(var)
                
                if not bgc_vars_found:
                    return None
                
                # Extract metadata
                float_id = getattr(ds, 'platform_number', file_path.stem).strip()
                
                # Extract location
                location_info = {'latitude': None, 'longitude': None, 'region': None}
                
                if 'LATITUDE' in variables and 'LONGITUDE' in variables:
                    try:
                        lats = ds.variables['LATITUDE'][:]
                        lons = ds.variables['LONGITUDE'][:]
                        
                        if hasattr(lats, 'mask'):
                            lats = lats[~lats.mask] if lats.mask.any() else lats.data
                            lons = lons[~lons.mask] if lons.mask.any() else lons.data
                        
                        if len(lats) > 0:
                            location_info['latitude'] = float(np.mean(lats))
                            location_info['longitude'] = float(np.mean(lons))
                            location_info['region'] = self._identify_region(
                                location_info['latitude'], location_info['longitude']
                            )
                    except Exception as e:
                        logger.warning(f"Error extracting location from {file_path}: {e}")
                
                return {
                    'source': 'local',
                    'file_path': str(file_path),
                    'file_name': file_path.name,
                    'float_id': float_id,
                    'bgc_variables': bgc_vars_found,
                    'total_variables': len(variables),
                    **location_info
                }
                
        except Exception as e:
            logger.warning(f"Error reading local BGC file {file_path}: {e}")
            return None
    
    def connect(self) -> bool:
        """Connect to FTP server with timeout"""
        try:
            self.ftp_connection = ftplib.FTP(self.host, timeout=45)
            self.ftp_connection.login()
            self.ftp_connection.set_pasv(True)
            logger.info(f"Connected to {self.host}")
            return True
        except Exception as e:
            logger.error(f"FTP connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close FTP connection"""
        if self.ftp_connection:
            try:
                self.ftp_connection.quit()
            except:
                pass
            self.ftp_connection = None
    
    def scan_ftp_bgc_floats(self, max_scan: int = 15) -> List[Dict[str, Any]]:
        """Enhanced FTP BGC float scanning with better detection"""
        logger.info("Starting enhanced FTP BGC float scan...")
        
        if not self.connect():
            return []
        
        bgc_floats = []
        
        try:
            # Check multiple DACs for better coverage
            dacs_to_scan = ['incois', 'coriolis', 'aoml']
            
            for dac in dacs_to_scan:
                logger.info(f"Scanning DAC: {dac}")
                
                try:
                    self.ftp_connection.cwd(f'/ifremer/argo/dac/{dac}')
                    float_dirs = self.ftp_connection.nlst()
                    
                    # Target specific float series known to have BGC capability
                    bgc_candidates = []
                    
                    # Look for floats with BGC patterns in their IDs
                    for float_id in float_dirs:
                        # Known BGC float series patterns
                        if any(pattern in float_id for pattern in ['590', '591', '592', '593', '594', '595', '596', '2902', '2903', '5906', '6903']):
                            bgc_candidates.append(float_id)
                    
                    # If no specific patterns, check recent floats
                    if not bgc_candidates:
                        try:
                            recent_floats = sorted([f for f in float_dirs if f.isdigit()], reverse=True)
                            bgc_candidates = recent_floats[:max_scan//len(dacs_to_scan)]
                        except:
                            bgc_candidates = float_dirs[:max_scan//len(dacs_to_scan)]
                    
                    logger.info(f"Checking {min(len(bgc_candidates), max_scan//len(dacs_to_scan))} candidate floats in {dac}")
                    
                    for float_id in bgc_candidates[:max_scan//len(dacs_to_scan)]:
                        try:
                            bgc_info = self._detailed_ftp_bgc_check(dac, float_id)
                            if bgc_info:
                                bgc_floats.append(bgc_info)
                                logger.info(f"Found FTP BGC float: {dac}/{float_id}")
                                
                                # Limit total BGC floats found
                                if len(bgc_floats) >= 5:
                                    break
                        
                        except Exception as e:
                            logger.warning(f"Error checking {dac}/{float_id}: {e}")
                            continue
                    
                    if len(bgc_floats) >= 5:
                        break
                
                except Exception as e:
                    logger.warning(f"Error scanning DAC {dac}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"FTP scan error: {e}")
        
        finally:
            self.disconnect()
        
        self.download_stats['ftp_bgc_files_found'] = len(bgc_floats)
        logger.info(f"FTP BGC scan found {len(bgc_floats)} floats")
        return bgc_floats
    
    def _detailed_ftp_bgc_check(self, dac: str, float_id: str) -> Optional[Dict[str, Any]]:
        """Detailed BGC check of individual float via FTP"""
        try:
            self.ftp_connection.cwd(float_id)
            files = self.ftp_connection.nlst()
            
            # Enhanced BGC file detection
            bgc_files = [f for f in files if self._is_bgc_file(f)]
            
            if bgc_files:
                # Try to get location from meta file or profile file
                location_info = self._extract_ftp_location_info(files, float_id)
                
                if location_info and location_info.get('region'):
                    # Quick BGC parameter verification
                    bgc_params = self._quick_ftp_bgc_verification(bgc_files[:2])
                    
                    self.ftp_connection.cwd('..')
                    
                    return {
                        'source': 'ftp',
                        'float_id': float_id,
                        'dac': dac,
                        'bgc_files': bgc_files[:5],  # Limit files
                        'bgc_parameters': bgc_params,
                        'ftp_path': f'/ifremer/argo/dac/{dac}/{float_id}',
                        **location_info
                    }
            
            self.ftp_connection.cwd('..')
            return None
        
        except Exception as e:
            logger.warning(f"Error in detailed FTP BGC check for {float_id}: {e}")
            try:
                self.ftp_connection.cwd('..')
            except:
                pass
            return None
    
    def _extract_ftp_location_info(self, files: List[str], float_id: str) -> Dict[str, Any]:
        """Extract location info from FTP files"""
        location_info = {'latitude': None, 'longitude': None, 'region': None}
        
        # Try meta file first
        meta_file = f"{float_id}_meta.nc"
        test_files = [meta_file] + [f for f in files if f.endswith('.nc') and ('D' in f or 'R' in f)][:2]
        
        for test_file in test_files:
            if test_file in files:
                try:
                    temp_file = self.download_dir / f"temp_loc_{test_file}"
                    
                    with open(temp_file, 'wb') as f:
                        self.ftp_connection.retrbinary(f'RETR {test_file}', f.write, blocksize=102400)  # 100KB chunks
                    
                    # Quick location extraction
                    with nc.Dataset(temp_file, 'r') as ds:
                        lat_vars = ['LAUNCH_LATITUDE', 'LATITUDE', 'latitude']
                        lon_vars = ['LAUNCH_LONGITUDE', 'LONGITUDE', 'longitude']
                        
                        for lat_var in lat_vars:
                            if lat_var in ds.variables:
                                try:
                                    lat_data = ds.variables[lat_var][:]
                                    if hasattr(lat_data, 'mask'):
                                        lat_data = lat_data[~lat_data.mask] if lat_data.mask.any() else lat_data.data
                                    
                                    if len(lat_data) > 0:
                                        location_info['latitude'] = float(np.mean(lat_data))
                                        break
                                except:
                                    continue
                        
                        for lon_var in lon_vars:
                            if lon_var in ds.variables:
                                try:
                                    lon_data = ds.variables[lon_var][:]
                                    if hasattr(lon_data, 'mask'):
                                        lon_data = lon_data[~lon_data.mask] if lon_data.mask.any() else lon_data.data
                                    
                                    if len(lon_data) > 0:
                                        location_info['longitude'] = float(np.mean(lon_data))
                                        break
                                except:
                                    continue
                    
                    temp_file.unlink()  # Clean up
                    
                    # If we got coordinates, identify region and break
                    if location_info['latitude'] is not None and location_info['longitude'] is not None:
                        location_info['region'] = self._identify_region(
                            location_info['latitude'], location_info['longitude']
                        )
                        break
                        
                except Exception as e:
                    logger.warning(f"Error extracting location from {test_file}: {e}")
                    try:
                        temp_file.unlink()
                    except:
                        pass
                    continue
        
        return location_info
    
    def _quick_ftp_bgc_verification(self, bgc_files: List[str]) -> List[str]:
        """Quick verification of BGC parameters in FTP files"""
        verified_params = []
        
        for bgc_file in bgc_files[:1]:  # Check only first file for speed
            try:
                file_size = self.ftp_connection.size(bgc_file)
                if file_size > 10000:  # Skip very small files
                    temp_file = self.download_dir / f"temp_bgc_{bgc_file}"
                    
                    # Download first portion of file
                    with open(temp_file, 'wb') as f:
                        self.ftp_connection.retrbinary(f'RETR {bgc_file}', f.write, blocksize=204800)  # 200KB
                    
                    # Quick parameter check
                    with nc.Dataset(temp_file, 'r') as ds:
                        variables = list(ds.variables.keys())
                        for bgc_param in self.bgc_parameters.keys():
                            if any(bgc_param in var for var in variables):
                                verified_params.append(bgc_param)
                    
                    temp_file.unlink()
                    break
                    
            except Exception as e:
                logger.warning(f"Error verifying BGC params in {bgc_file}: {e}")
                try:
                    temp_file.unlink()
                except:
                    pass
                continue
        
        return list(set(verified_params))
    
    def _is_bgc_file(self, filename: str) -> bool:
        """Enhanced BGC file detection - fixed to recognize BD* patterns"""
        bgc_patterns = [
            'BD',          # BGC Data files (like your BD2902276 files) - CRITICAL FIX
            'BR',          # BGC Realtime  
            'BS',          # BGC Synthetic
            'B_',          # BGC prefix pattern
            '_B',          # BGC suffix pattern
            'bio',         # Biogeochemical
            'bgc',         # BGC acronym (lowercase)
            'BGC',         # BGC acronym (uppercase) 
            'synthetic',   # Synthetic profiles
            'CHLA',        # Chlorophyll files
            'DOXY',        # Oxygen files
        ]
        
        # Check if filename starts with or contains BGC patterns
        filename_upper = filename.upper()
        for pattern in bgc_patterns:
            if pattern.upper() in filename_upper:
                return True
                
        return False
    
    def _identify_region(self, lat: float, lon: float) -> Optional[str]:
        """Identify ocean region from coordinates"""
        for region, bounds in self.regional_bounds.items():
            if (bounds['lat'][0] <= lat <= bounds['lat'][1] and 
                bounds['lon'][0] <= lon <= bounds['lon'][1]):
                return region.replace('_', ' ').title()
        return 'Indian Ocean'  # Default for other Indian Ocean areas
    
    def generate_comprehensive_bgc_report(self, local_bgc: List[Dict], ftp_bgc: List[Dict]) -> Dict[str, Any]:
        """Generate comprehensive report combining local and FTP BGC data"""
        all_bgc_data = local_bgc + ftp_bgc
        
        # Load existing analysis results if available
        existing_analysis = {}
        for results_dir in self.results_dirs:
            results_dir.mkdir(parents=True, exist_ok=True)
            
            # Check for existing analysis files
            analysis_files = [
                'working_bgc_analysis_results.json',
                'argo_extracted_data.json', 
                'processed_oceanographic_data.json',
                'argo_download_summary.json'
            ]
            
            for analysis_file in analysis_files:
                file_path = results_dir / analysis_file
                if file_path.exists():
                    try:
                        with open(file_path, 'r') as f:
                            existing_analysis[analysis_file] = json.load(f)
                        logger.info(f"Loaded existing analysis: {file_path}")
                    except Exception as e:
                        logger.warning(f"Error loading {file_path}: {e}")
        
        # Regional and parameter analysis
        regional_counts = {}
        parameter_counts = {}
        source_counts = {'local': 0, 'ftp': 0}
        
        for bgc_data in all_bgc_data:
            region = bgc_data.get('region', 'Unknown')
            regional_counts[region] = regional_counts.get(region, 0) + 1
            
            source = bgc_data.get('source', 'unknown')
            source_counts[source] = source_counts.get(source, 0) + 1
            
            for var in bgc_data.get('bgc_variables', []):
                parameter_counts[var] = parameter_counts.get(var, 0) + 1
        
        # Comprehensive report
        report = {
            'comprehensive_bgc_analysis': {
                'analysis_timestamp': datetime.now().isoformat(),
                'data_sources': {
                    'local_bgc_files': len(local_bgc),
                    'ftp_bgc_files': len(ftp_bgc), 
                    'total_bgc_datasets': len(all_bgc_data),
                    'source_breakdown': source_counts
                },
                'regional_coverage': regional_counts,
                'bgc_parameters_detected': len(parameter_counts),
                'parameter_frequency': dict(sorted(parameter_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
                'target_regions_covered': [r for r in regional_counts.keys() if r.lower().replace(' ', '_') in self.target_regions]
            },
            'existing_analysis_integration': {
                'files_found': list(existing_analysis.keys()),
                'analysis_available': len(existing_analysis) > 0
            },
            'download_statistics': self.download_stats,
            'bgc_floats_summary': all_bgc_data[:5],  # Sample of first 5 floats
            'recommendations': self._generate_recommendations(regional_counts, parameter_counts, existing_analysis)
        }
        
        return report
    
    def _generate_recommendations(self, regional_counts: Dict, parameter_counts: Dict, existing_analysis: Dict) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []
        
        # Regional coverage recommendations
        target_regions_found = [r for r in regional_counts.keys() if r.lower().replace(' ', '_') in self.target_regions]
        if len(target_regions_found) >= 2:
            recommendations.append(f"Good regional coverage: {len(target_regions_found)} target regions with BGC data")
        else:
            recommendations.append("Limited regional coverage - consider expanding data collection")
        
        # Parameter coverage recommendations
        key_bgc_params = ['CHLA', 'DOXY', 'BBP700', 'PH_IN_SITU_TOTAL']
        found_key_params = [p for p in parameter_counts.keys() if any(key in p for key in key_bgc_params)]
        if len(found_key_params) >= 3:
            recommendations.append("Excellent BGC parameter coverage for ecosystem analysis")
        else:
            recommendations.append("Basic BGC parameters available - suitable for preliminary analysis")
        
        # Integration recommendations
        if existing_analysis:
            recommendations.append("Existing analysis files found - system ready for comprehensive BGC assessment")
        else:
            recommendations.append("Run bgc_parameter_analyzer.py to generate ecosystem health analysis")
        
        return recommendations
    
    async def run_comprehensive_bgc_analysis(self) -> Dict[str, Any]:
        """Run comprehensive BGC analysis combining local and FTP sources"""
        print("Starting Comprehensive BGC Analysis...")
        
        # Step 1: Scan local BGC files
        print("Step 1: Scanning local BGC files...")
        local_bgc = self.scan_local_bgc_files()
        print(f"✓ Found {len(local_bgc)} local BGC files")
        
        # Step 2: Scan FTP for additional BGC floats
        print("Step 2: Scanning FTP for BGC floats...")
        start_time = time.time()
        ftp_bgc = self.scan_ftp_bgc_floats(max_scan=10)
        scan_duration = time.time() - start_time
        print(f"✓ FTP scan completed in {scan_duration:.1f}s, found {len(ftp_bgc)} BGC floats")
        
        # Step 3: Generate comprehensive report
        print("Step 3: Generating comprehensive report...")
        report = self.generate_comprehensive_bgc_report(local_bgc, ftp_bgc)
        
        # Save report
        report_file = "improved_bgc_comprehensive_analysis.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"✓ Report saved to {report_file}")
        
        # Display summary
        analysis = report['comprehensive_bgc_analysis']
        print(f"\nComprehensive BGC Analysis Results:")
        print(f"  Total BGC datasets: {analysis['data_sources']['total_bgc_datasets']}")
        print(f"  Local files: {analysis['data_sources']['local_bgc_files']}")  
        print(f"  FTP files: {analysis['data_sources']['ftp_bgc_files']}")
        print(f"  Regional coverage: {list(analysis['regional_coverage'].keys())}")
        print(f"  BGC parameters detected: {analysis['bgc_parameters_detected']}")
        print(f"  Target regions covered: {analysis['target_regions_covered']}")
        
        print(f"\nRecommendations:")
        for rec in report['recommendations']:
            print(f"  • {rec}")
        
        return report

# Test function
async def test_improved_advanced_ftp_handler():
    """Test the improved FTP handler"""
    handler = ImprovedAdvancedFTPHandler(
        max_size_gb=0.1,
        max_files=10,
        target_regions=['arabian_sea', 'bay_of_bengal', 'indian_ocean_equatorial']
    )
    
    results = await handler.run_comprehensive_bgc_analysis()
    
    # Show if BGC detection is now working
    total_bgc = results['comprehensive_bgc_analysis']['data_sources']['total_bgc_datasets']
    if total_bgc > 0:
        print(f"\n🎉 SUCCESS: BGC detection is now working! Found {total_bgc} BGC datasets")
        return True
    else:
        print(f"\n❌ BGC detection still needs work")
        return False

if __name__ == "__main__":
    asyncio.run(test_improved_advanced_ftp_handler())
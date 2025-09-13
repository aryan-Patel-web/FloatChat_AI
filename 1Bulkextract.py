#!/usr/bin/env python3
"""
Compact Enhanced ARGO Processor - SIH 2025 FloatChat
All Advanced Features in <1200 lines using Indian Ocean URL structure
URL Pattern: https://data-argo.ifremer.fr/geo/indian_ocean/YYYY/MM/
"""
import os, json, numpy as np, xarray as xr, pandas as pd, requests, asyncio, aiohttp, hashlib, time, warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from scipy import stats
import re
warnings.filterwarnings('ignore')

class CompactEnhancedArgoProcessor:
    def __init__(self, base_path: str = "Dataset", json_path: str = "Datasetjson"):
        self.base_path = Path(base_path)
        self.json_path = Path(json_path)
        self.base_path.mkdir(exist_ok=True)
        self.json_path.mkdir(exist_ok=True)
        
        # Complete BGC Variables with all parameters
        self.bgc_vars = {
            'DOXY': {'desc': 'Dissolved oxygen', 'unit': 'micromol/kg'}, 'CHLA': {'desc': 'Chlorophyll-a', 'unit': 'mg/m^3'},
            'NITRATE': {'desc': 'Nitrate', 'unit': 'micromol/kg'}, 'PH_IN_SITU_TOTAL': {'desc': 'pH in situ', 'unit': 'pH_units'},
            'CDOM': {'desc': 'CDOM', 'unit': 'ppb'}, 'BBP700': {'desc': 'Backscatter 700nm', 'unit': 'm^-1'},
            'BBP532': {'desc': 'Backscatter 532nm', 'unit': 'm^-1'}, 'DOWNWELLING_PAR': {'desc': 'PAR', 'unit': 'microMoleQuanta/m^2/s'},
            'DOWN_IRRADIANCE380': {'desc': 'Irradiance 380nm', 'unit': 'W/m^2/nm'}, 'TURBIDITY': {'desc': 'Turbidity', 'unit': 'ntu'},
            'ALKALINITY': {'desc': 'Alkalinity', 'unit': 'micromol/kg'}, 'DIC': {'desc': 'DIC', 'unit': 'micromol/kg'},
            'PHOSPHATE': {'desc': 'Phosphate', 'unit': 'micromol/kg'}, 'SILICATE': {'desc': 'Silicate', 'unit': 'micromol/kg'}
        }
        
        # Regional boundaries for geospatial classification
        self.regions = {
            'Arabian_Sea': {'lat': [8, 30], 'lon': [50, 80]}, 'Bay_of_Bengal': {'lat': [5, 25], 'lon': [80, 100]},
            'Equatorial_Indian': {'lat': [-10, 10], 'lon': [40, 110]}, 'Southern_Ocean': {'lat': [-70, -40], 'lon': [0, 360]},
            'Tropical_Indian': {'lat': [-23.5, 23.5], 'lon': [40, 120]}, 'Monsoon_Region': {'lat': [0, 30], 'lon': [50, 100]}
        }
        
        # Water mass definitions for advanced analysis
        self.water_masses = {
            'Surface_Water': {'temp': [25, 30], 'sal': [34, 36], 'depth': [0, 100]},
            'Central_Water': {'temp': [8, 20], 'sal': [34.5, 35.5], 'depth': [100, 1000]},
            'Intermediate_Water': {'temp': [3, 8], 'sal': [34.2, 34.6], 'depth': [500, 1500]},
            'Deep_Water': {'temp': [1, 3], 'sal': [34.7, 34.8], 'depth': [1500, 4000]}
        }

    def get_indian_ocean_urls(self, year: int, month: Optional[int] = None) -> List[str]:
        """Get file URLs from Indian Ocean directory structure"""
        urls = []
        base_url = "https://data-argo.ifremer.fr/geo/indian_ocean/"
        
        try:
            if month:
                # Direct month access: /YYYY/MM/
                dir_url = f"{base_url}{year}/{month:02d}/"
                print(f"Scanning: {dir_url}")
                response = requests.get(dir_url, timeout=30)
                if response.status_code == 200:
                    nc_files = re.findall(r'href="([^"]*\.nc)"', response.text)
                    urls.extend([dir_url + f for f in nc_files])
                    print(f"Found {len(nc_files)} files in {year}/{month:02d}/")
            else:
                # Scan all months for the year: /YYYY/
                year_url = f"{base_url}{year}/"
                print(f"Scanning year: {year_url}")
                response = requests.get(year_url, timeout=30)
                if response.status_code == 200:
                    months = re.findall(r'href="(\d{2}/)"', response.text)
                    for m in months:
                        month_url = f"{year_url}{m}"
                        try:
                            month_resp = requests.get(month_url, timeout=20)
                            if month_resp.status_code == 200:
                                nc_files = re.findall(r'href="([^"]*\.nc)"', month_resp.text)
                                urls.extend([month_url + f for f in nc_files])
                                print(f"Found {len(nc_files)} files in {year}/{m}")
                        except Exception as e:
                            print(f"Error accessing {month_url}: {e}")
        except Exception as e:
            print(f"Error accessing Indian Ocean directory: {e}")
        
        print(f"Total URLs found: {len(urls)}")
        return urls

    def get_existing_files(self, year: int, month: Optional[int] = None) -> set:
        """Get existing downloaded files"""
        existing = set()
        search_path = self.base_path / str(year) / (f"{month:02d}" if month else "")
        if search_path.exists():
            existing = {f.name for f in search_path.rglob("*.nc")}
        return existing

    async def download_file(self, session: aiohttp.ClientSession, url: str, local_path: Path, retries: int = 3) -> bool:
        """Download single file with retry logic"""
        for attempt in range(retries):
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=300)) as response:
                    if response.status == 200:
                        local_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(local_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                        print(f"Downloaded: {local_path.name}")
                        return True
                    else:
                        print(f"HTTP {response.status}: {url}")
            except Exception as e:
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    print(f"Failed: {local_path.name} - {e}")
        return False

    async def download_files(self, urls: List[str], year: int, month: Optional[int] = None, force: bool = False):
        """Download files with smart existing file detection"""
        existing_files = set() if force else self.get_existing_files(year, month)
        print(f"Existing files: {len(existing_files)} {'(will overwrite)' if force else '(will skip)'}")
        
        download_urls = []
        for url in urls:
            filename = os.path.basename(url)
            if not force and filename in existing_files:
                continue
            download_urls.append(url)
        
        print(f"Files to download: {len(download_urls)}")
        if not download_urls:
            print("All files already exist!")
            return
        
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=3)) as session:
            tasks = []
            for url in download_urls:
                filename = os.path.basename(url)
                # Extract date and create path structure
                date_match = re.search(r'(\d{8})', filename)
                if date_match and month:
                    local_path = self.base_path / str(year) / f"{month:02d}" / filename
                elif date_match:
                    date_str = date_match.group(1)
                    file_month = int(date_str[4:6])
                    local_path = self.base_path / str(year) / f"{file_month:02d}" / filename
                else:
                    local_path = self.base_path / str(year) / filename
                
                task = self.download_file(session, url, local_path)
                tasks.append(task)
                
                if len(tasks) >= 5:  # Process in batches
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    success = sum(1 for r in results if r is True)
                    print(f"Batch: {success}/{len(tasks)} successful")
                    tasks = []
                    await asyncio.sleep(1)
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                success = sum(1 for r in results if r is True)
                print(f"Final batch: {success}/{len(tasks)} successful")

    def extract_data(self, ds: xr.Dataset, var: str) -> np.ndarray:
        """Extract and clean variable data"""
        try:
            if var not in ds:
                return np.array([])
            data = ds[var].values
            if data.ndim > 1:
                data = data.flatten()
            fill_val = ds[var].attrs.get('_FillValue', np.nan)
            return data[~np.isnan(data) & (data != fill_val)]
        except:
            return np.array([])

    def safe_scalar(self, ds: xr.Dataset, var: str, default: float = 0.0) -> float:
        """Safely extract scalar value"""
        try:
            if var in ds:
                data = ds[var].values
                return float(data[0] if hasattr(data, '__len__') else data)
            return default
        except:
            return default

    def calculate_stats(self, data: np.ndarray) -> Dict:
        """Calculate comprehensive statistics"""
        if len(data) == 0:
            return {}
        valid = data[~np.isnan(data)]
        if len(valid) == 0:
            return {}
        
        return {
            'count': int(len(valid)), 'min': float(np.min(valid)), 'max': float(np.max(valid)),
            'mean': float(np.mean(valid)), 'median': float(np.median(valid)), 'std': float(np.std(valid)),
            'p25': float(np.percentile(valid, 25)), 'p75': float(np.percentile(valid, 75)),
            'skewness': float(stats.skew(valid)) if len(valid) > 2 else 0,
            'kurtosis': float(stats.kurtosis(valid)) if len(valid) > 3 else 0
        }

    def classify_region(self, lat: float, lon: float) -> Dict:
        """Advanced geospatial classification"""
        regions_found = []
        for region, bounds in self.regions.items():
            if (bounds['lat'][0] <= lat <= bounds['lat'][1] and 
                bounds['lon'][0] <= lon <= bounds['lon'][1]):
                regions_found.append(region)
        
        # Ocean basin classification
        basin = "Indian"
        if lon < 20:
            basin = "Atlantic"
        elif lon > 147:
            basin = "Pacific"
        
        # Geographic zone
        zone = "Tropical" if abs(lat) < 23.5 else "Subtropical" if abs(lat) < 40 else "Temperate"
        
        return {
            'regional_seas': regions_found, 'ocean_basin': basin, 'geographic_zone': zone,
            'grid_1deg': f"{'S' if lat < 0 else 'N'}{abs(int(lat)):02d}{'W' if lon < 0 else 'E'}{abs(int(lon)):03d}",
            'biogeographic_province': self.get_bgc_province(lat, lon)
        }

    def get_bgc_province(self, lat: float, lon: float) -> str:
        """Determine biogeochemical province"""
        if 8 <= lat <= 30 and 50 <= lon <= 80:
            return "Arabian_Sea_Province"
        elif 5 <= lat <= 25 and 80 <= lon <= 100:
            return "Bay_of_Bengal_Province"
        elif -10 <= lat <= 10:
            return "Equatorial_Province"
        else:
            return "Subtropical_Province"

    def get_temporal_info(self, juld: float) -> Dict:
        """Extract temporal information"""
        try:
            ref_date = datetime(1950, 1, 1)
            profile_date = ref_date + timedelta(days=float(juld))
            month = profile_date.month
            
            # Seasonal classification
            if month in [12, 1, 2]:
                season_nh, season_sh = "winter", "summer"
            elif month in [3, 4, 5]:
                season_nh, season_sh = "spring", "autumn"
            elif month in [6, 7, 8]:
                season_nh, season_sh = "summer", "winter"
            else:
                season_nh, season_sh = "autumn", "spring"
            
            # Monsoon classification
            if month in [6, 7, 8, 9]:
                monsoon = "southwest_monsoon"
            elif month in [12, 1, 2, 3]:
                monsoon = "northeast_monsoon"
            else:
                monsoon = "pre_monsoon" if month in [4, 5] else "post_monsoon"
            
            return {
                'datetime': profile_date.isoformat(), 'year': profile_date.year, 'month': month,
                'season_nh': season_nh, 'season_sh': season_sh, 'monsoon_season': monsoon,
                'decade': f"{profile_date.year//10*10}s", 'quarter': f"Q{(month-1)//3 + 1}"
            }
        except:
            return {'datetime': None, 'year': None, 'month': None}

    def identify_water_masses(self, temp: np.ndarray, sal: np.ndarray, pres: np.ndarray) -> List[Dict]:
        """Advanced water mass identification"""
        found = []
        try:
            valid_mask = ~(np.isnan(temp) | np.isnan(sal) | np.isnan(pres))
            if not np.any(valid_mask):
                return found
            
            t, s, p = temp[valid_mask], sal[valid_mask], pres[valid_mask]
            sort_idx = np.argsort(p)
            t_sort, s_sort, p_sort = t[sort_idx], s[sort_idx], p[sort_idx]
            
            for wm_name, props in self.water_masses.items():
                mask = ((t_sort >= props['temp'][0]) & (t_sort <= props['temp'][1]) &
                       (s_sort >= props['sal'][0]) & (s_sort <= props['sal'][1]) &
                       (p_sort >= props['depth'][0]) & (p_sort <= props['depth'][1]))
                
                if np.any(mask):
                    found.append({
                        'name': wm_name, 'core_temp': float(np.mean(t_sort[mask])),
                        'core_sal': float(np.mean(s_sort[mask])),
                        'depth_range': [float(np.min(p_sort[mask])), float(np.max(p_sort[mask]))],
                        'strength': float(np.sum(mask) / len(t_sort))
                    })
        except Exception as e:
            print(f"Water mass error: {e}")
        return found

    def analyze_bgc_variable(self, ds: xr.Dataset, var: str, pressure: np.ndarray, temp: np.ndarray) -> Dict:
        """Advanced BGC variable analysis"""
        if var not in ds.variables:
            return {'present': False, 'reason': 'Not available'}
        
        data = self.extract_data(ds, var)
        if len(data) == 0:
            return {'present': False, 'reason': 'No valid data'}
        
        # Basic statistics
        stats = self.calculate_stats(data)
        
        # Variable-specific analysis
        advanced = {}
        if var == 'DOXY' and len(data) > 5:
            # Oxygen analysis
            min_o2 = np.min(data)
            advanced['omz_present'] = min_o2 < 20
            advanced['hypoxic'] = min_o2 < 60
            advanced['min_oxygen'] = float(min_o2)
            
        elif var == 'CHLA' and len(data) > 5:
            # Chlorophyll analysis
            surface_chl = data[0] if len(data) > 0 else np.nan
            max_chl = np.max(data)
            advanced['surface_chl'] = float(surface_chl)
            advanced['dcm_present'] = max_chl > 1.5 * surface_chl
            advanced['trophic_status'] = ('oligotrophic' if surface_chl < 0.3 else 
                                        'mesotrophic' if surface_chl < 1.0 else 'eutrophic')
        
        return {
            'present': True, 'description': self.bgc_vars[var]['desc'],
            'unit': self.bgc_vars[var]['unit'], 'statistics': stats, 'advanced': advanced
        }

    def detect_features(self, temp: np.ndarray, sal: np.ndarray, pres: np.ndarray) -> Dict:
        """Detect oceanographic features"""
        features = {'inversions': [], 'extrema': [], 'gradients': {}}
        
        try:
            valid_mask = ~(np.isnan(temp) | np.isnan(sal) | np.isnan(pres))
            if not np.any(valid_mask) or len(temp[valid_mask]) < 5:
                return features
            
            t, s, p = temp[valid_mask], sal[valid_mask], pres[valid_mask]
            sort_idx = np.argsort(p)
            t_sort, s_sort, p_sort = t[sort_idx], s[sort_idx], p[sort_idx]
            
            # Temperature inversions
            temp_diff = np.diff(t_sort)
            inversions = np.where(temp_diff > 0.1)[0]
            for idx in inversions:
                features['inversions'].append({
                    'depth': float(p_sort[idx]), 'strength': float(temp_diff[idx]), 'type': 'temperature'
                })
            
            # Gradient analysis
            features['gradients'] = {
                'temp_max_grad': float(np.max(np.abs(np.gradient(t_sort, p_sort)))),
                'sal_max_grad': float(np.max(np.abs(np.gradient(s_sort, p_sort))))
            }
        except Exception as e:
            print(f"Feature detection error: {e}")
        
        return features

    def calculate_derived_params(self, temp: np.ndarray, sal: np.ndarray, pres: np.ndarray) -> Dict:
        """Calculate derived oceanographic parameters"""
        derived = {}
        try:
            if len(temp) > 0 and len(sal) > 0 and len(pres) > 0:
                # Simplified density calculation
                valid_mask = ~(np.isnan(temp) | np.isnan(sal) | np.isnan(pres))
                if np.any(valid_mask):
                    t, s, p = temp[valid_mask], sal[valid_mask], pres[valid_mask]
                    # Simplified density approximation
                    density = 1000 + 0.8 * (s - 35) - 0.2 * (t - 15)
                    derived['density_stats'] = self.calculate_stats(density)
                    derived['potential_temp'] = float(np.mean(t - 0.0001 * p))
        except Exception as e:
            print(f"Derived params error: {e}")
        return derived

    def generate_rag_data(self, temporal: Dict, spatial: Dict, core_vars: Dict, bgc_vars: Dict) -> Dict:
        """Generate RAG optimization data"""
        # Search terms
        terms = []
        if temporal.get('year'):
            terms.extend([str(temporal['year']), temporal.get('monsoon_season', '')])
        if spatial.get('ocean_basin'):
            terms.extend([spatial['ocean_basin'], spatial.get('geographic_zone', '')])
        
        present_bgc = [var for var, data in bgc_vars.items() if data.get('present')]
        terms.extend([f"{var.lower()}_measurements" for var in present_bgc])
        
        # Natural language summary
        date_str = temporal.get('datetime', 'unknown')[:10]
        region_str = ', '.join(spatial.get('regional_seas', ['Unknown region']))
        bgc_str = f" with {len(present_bgc)} BGC parameters" if present_bgc else ""
        
        summary = (f"ARGO profile from {spatial.get('ocean_basin', 'Unknown')} Ocean "
                  f"({region_str}) on {date_str}{bgc_str}")
        
        return {
            'search_terms': [t for t in terms if t], 'summary': summary,
            'keywords': terms + [f"{var}_profile" for var in core_vars.keys() if core_vars[var].get('present')]
        }

    def process_nc_file(self, file_path: Path) -> Optional[Dict]:
        """Complete NetCDF processing with all features"""
        try:
            print(f"Processing: {file_path.name}")
            
            with xr.open_dataset(file_path, decode_times=False) as ds:
                # Extract basic data
                juld = self.safe_scalar(ds, 'JULD')
                lat = self.safe_scalar(ds, 'LATITUDE')
                lon = self.safe_scalar(ds, 'LONGITUDE')
                
                # Extract core variables
                pressure = self.extract_data(ds, 'PRES')
                temp = self.extract_data(ds, 'TEMP')
                sal = self.extract_data(ds, 'PSAL')
                
                # Temporal and spatial analysis
                temporal_info = self.get_temporal_info(juld)
                spatial_info = self.classify_region(lat, lon)
                
                # Core variable analysis
                core_vars = {}
                for var, data in [('TEMP', temp), ('PSAL', sal), ('PRES', pressure)]:
                    if len(data) > 0:
                        core_vars[var] = {
                            'present': True, 'statistics': self.calculate_stats(data),
                            'unit': {'TEMP': 'degrees_C', 'PSAL': 'PSU', 'PRES': 'dbar'}[var]
                        }
                    else:
                        core_vars[var] = {'present': False}
                
                # BGC analysis
                bgc_vars = {}
                for var in self.bgc_vars.keys():
                    bgc_vars[var] = self.analyze_bgc_variable(ds, var, pressure, temp)
                
                # Water mass analysis
                water_masses = self.identify_water_masses(temp, sal, pressure)
                
                # Oceanographic features
                features = self.detect_features(temp, sal, pressure)
                
                # Derived parameters
                derived = self.calculate_derived_params(temp, sal, pressure)
                
                # Platform info
                platform_info = {
                    'platform_number': self.safe_decode(ds.get('PLATFORM_NUMBER', b'unknown')),
                    'cycle_number': int(self.safe_scalar(ds, 'CYCLE_NUMBER')),
                    'data_mode': self.safe_decode(ds.get('DATA_MODE', b'R'))
                }
                
                # Quality assessment
                quality = {
                    'data_completeness': len([v for v in core_vars.values() if v.get('present')]) / 3 * 100,
                    'bgc_completeness': len([v for v in bgc_vars.values() if v.get('present')]) / len(self.bgc_vars) * 100
                }
                
                # RAG optimization
                rag_data = self.generate_rag_data(temporal_info, spatial_info, core_vars, bgc_vars)
                
                # Complete JSON structure
                return {
                    "metadata": {
                        "file_id": file_path.stem, "processing_time": datetime.now().isoformat(),
                        "processor_version": "SIH2025_Compact_v1.0", "file_size": file_path.stat().st_size
                    },
                    "platform": platform_info, "temporal": temporal_info, "geospatial": spatial_info,
                    "measurements": {"core": core_vars, "bgc": bgc_vars, "derived": derived},
                    "oceanography": {"water_masses": water_masses, "features": features},
                    "quality": quality, "rag_optimization": rag_data
                }
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return None

    def safe_decode(self, data) -> str:
        """Safely decode byte strings"""
        try:
            if hasattr(data, 'values'):
                data = data.values
            if hasattr(data, '__iter__') and not isinstance(data, (str, bytes)):
                data = data[0] if len(data) > 0 else b'unknown'
            if hasattr(data, 'decode'):
                return data.decode('utf-8').strip()
            return str(data).strip().replace("b'", "").replace("'", "")
        except:
            return "unknown"

    def process_files(self, year: int, month: Optional[int] = None):
        """Process existing files to JSON"""
        # Determine paths
        if month:
            search_path = self.base_path / str(year) / f"{month:02d}"
            json_path = self.json_path / str(year) / f"{month:02d}"
        else:
            search_path = self.base_path / str(year)
            json_path = self.json_path / str(year)
        
        if not search_path.exists():
            print(f"No files found in: {search_path}")
            return
        
        nc_files = list(search_path.rglob("*.nc"))
        print(f"Found {len(nc_files)} NetCDF files")
        
        if not nc_files:
            return
        
        json_path.mkdir(parents=True, exist_ok=True)
        processed, errors = 0, 0
        
        for i, nc_file in enumerate(nc_files):
            try:
                # Create JSON path maintaining structure
                rel_path = nc_file.relative_to(search_path)
                json_file = json_path / rel_path.with_suffix('.json')
                
                # Skip if newer
                if json_file.exists() and json_file.stat().st_mtime > nc_file.stat().st_mtime:
                    continue
                
                # Process
                json_data = self.process_nc_file(nc_file)
                if json_data:
                    json_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(json_file, 'w', encoding='utf-8') as f:
                        json.dump(json_data, f, indent=2, default=str)
                    print(f"JSON saved: {json_file.name}")
                    processed += 1
                else:
                    errors += 1
                    
            except Exception as e:
                print(f"Error: {nc_file.name} - {e}")
                errors += 1
        
        print(f"Processed: {processed}, Errors: {errors}")

    def download_and_process(self, year: int, month: Optional[int] = None, force: bool = False):
        """Complete pipeline: download then process"""
        print(f"Starting Indian Ocean ARGO processing for {year}" + (f"-{month:02d}" if month else ""))
        
        # Get URLs and download
        urls = self.get_indian_ocean_urls(year, month)
        if not urls:
            print("No files found in Indian Ocean directory")
            return
        
        # Download files
        start_time = time.time()
        asyncio.run(self.download_files(urls, year, month, force))
        print(f"Download completed in {time.time() - start_time:.1f}s")
        
        # Process to JSON
        print("Starting JSON conversion...")
        start_time = time.time()
        self.process_files(year, month)
        print(f"Processing completed in {time.time() - start_time:.1f}s")

def main():
    """Main interface"""
    processor = CompactEnhancedArgoProcessor()
    
    print("=" * 60)
    print("COMPACT ENHANCED ARGO PROCESSOR - SIH 2025")
    print("Indian Ocean Focus: https://data-argo.ifremer.fr/geo/indian_ocean/")
    print("All Advanced Features in <1200 lines")
    print("=" * 60)
    
    print("\nOptions:")
    print("1. Download + Process: Full Year")
    print("2. Download + Process: Year/Month") 
    print("3. Process existing files: Year")
    print("4. Process existing files: Year/Month")
    print("5. Force re-download + Process")
    print("0. Exit")
    
    choice = input("\nChoice (0-5): ").strip()
    
    if choice == "1":
        year = int(input("Year (YYYY): "))
        processor.download_and_process(year)
        
    elif choice == "2":
        year = int(input("Year (YYYY): "))
        month = int(input("Month (1-12): "))
        processor.download_and_process(year, month)
        
    elif choice == "3":
        year = int(input("Year (YYYY): "))
        processor.process_files(year)
        
    elif choice == "4":
        year = int(input("Year (YYYY): "))
        month = int(input("Month (1-12): "))
        processor.process_files(year, month)
        
    elif choice == "5":
        year = int(input("Year (YYYY): "))
        month_input = input("Month (1-12, or Enter for full year): ")
        month = int(month_input) if month_input else None
        processor.download_and_process(year, month, force=True)
        
    elif choice == "0":
        print("Complete! Your enhanced JSON files are ready for SIH 2025 RAG system.")
        return
    
    else:
        print("Invalid choice")
        return
    
    print("\nProcessing Complete!")
    print("JSON files organized in: Datasetjson/")
    print("Ready for RAG system integration!")

if __name__ == "__main__":
    main()
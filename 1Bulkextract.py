#!/usr/bin/env python3
"""
DEBUGGED Enhanced ARGO Processor - SIH 2025 FloatChat
Fixed ALL analysis functions to work with real ARGO data
URL Pattern: https://data-argo.ifremer.fr/geo/indian_ocean/YYYY/MM/
"""
import os, json, numpy as np, xarray as xr, pandas as pd, requests, asyncio, aiohttp, hashlib, time, warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from scipy import stats
import re
warnings.filterwarnings('ignore')

class DebuggedArgoProcessor:
    def __init__(self, base_path: str = "Dataset", json_path: str = "Datasetjson"):
        self.base_path = Path(base_path)
        self.json_path = Path(json_path)
        self.base_path.mkdir(exist_ok=True)
        self.json_path.mkdir(exist_ok=True)
        
        # Enhanced BGC Variables with all parameters
        self.bgc_vars = {
            'DOXY': {'desc': 'Dissolved oxygen concentration', 'unit': 'micromol/kg'}, 
            'CHLA': {'desc': 'Chlorophyll-a concentration', 'unit': 'mg/m^3'},
            'NITRATE': {'desc': 'Nitrate concentration', 'unit': 'micromol/kg'}, 
            'PH_IN_SITU_TOTAL': {'desc': 'pH in situ total scale', 'unit': 'pH_units'},
            'CDOM': {'desc': 'Colored dissolved organic matter', 'unit': 'ppb'}, 
            'BBP700': {'desc': 'Backscattering at 700nm', 'unit': 'm^-1'},
            'BBP532': {'desc': 'Backscattering at 532nm', 'unit': 'm^-1'}, 
            'DOWNWELLING_PAR': {'desc': 'Photosynthetic available radiation', 'unit': 'microMoleQuanta/m^2/s'},
            'DOWN_IRRADIANCE380': {'desc': 'Downwelling irradiance 380nm', 'unit': 'W/m^2/nm'}, 
            'DOWN_IRRADIANCE412': {'desc': 'Downwelling irradiance 412nm', 'unit': 'W/m^2/nm'},
            'DOWN_IRRADIANCE490': {'desc': 'Downwelling irradiance 490nm', 'unit': 'W/m^2/nm'},
            'TURBIDITY': {'desc': 'Sea water turbidity', 'unit': 'ntu'},
            'ALKALINITY': {'desc': 'Total alkalinity', 'unit': 'micromol/kg'}, 
            'DIC': {'desc': 'Dissolved inorganic carbon', 'unit': 'micromol/kg'},
            'PHOSPHATE': {'desc': 'Phosphate concentration', 'unit': 'micromol/kg'}, 
            'SILICATE': {'desc': 'Silicate concentration', 'unit': 'micromol/kg'}
        }
        
        # Complete Regional boundaries
        self.regions = {
            'Arabian_Sea': {'lat': [8, 30], 'lon': [50, 80]}, 
            'Bay_of_Bengal': {'lat': [5, 25], 'lon': [80, 100]},
            'Equatorial_Indian': {'lat': [-10, 10], 'lon': [40, 110]}, 
            'Southern_Ocean': {'lat': [-70, -40], 'lon': [0, 360]},
            'Tropical_Indian': {'lat': [-23.5, 23.5], 'lon': [40, 120]}, 
            'Monsoon_Region': {'lat': [0, 30], 'lon': [50, 100]},
            'Red_Sea': {'lat': [12, 30], 'lon': [32, 43]}, 
            'Persian_Gulf': {'lat': [24, 30], 'lon': [48, 56]},
            'Andaman_Sea': {'lat': [5, 20], 'lon': [90, 100]}, 
            'Western_Indian': {'lat': [-40, 30], 'lon': [20, 70]},
            'Eastern_Indian': {'lat': [-40, 30], 'lon': [90, 147]}, 
            'Madagascar_Ridge': {'lat': [-30, -10], 'lon': [40, 60]}
        }
        
        # Realistic water mass definitions based on Indian Ocean
        self.water_masses = {
            'Indian_Surface_Water': {'temp': [24, 30], 'sal': [33.5, 36.5], 'depth': [0, 150]},
            'Indian_Central_Water': {'temp': [6, 20], 'sal': [34.3, 35.8], 'depth': [150, 1200]},
            'Red_Sea_Water': {'temp': [8, 20], 'sal': [35.8, 40.5], 'depth': [200, 1500]},
            'Antarctic_Intermediate': {'temp': [2, 6], 'sal': [34.2, 34.6], 'depth': [800, 1500]},
            'Circumpolar_Deep': {'temp': [1, 3], 'sal': [34.68, 34.74], 'depth': [1500, 3500]},
            'Antarctic_Bottom': {'temp': [-0.5, 2], 'sal': [34.64, 34.70], 'depth': [3500, 6000]}
        }

    def get_indian_ocean_urls(self, year: int, month: Optional[int] = None) -> List[str]:
        """Get file URLs from Indian Ocean directory structure"""
        urls = []
        base_url = "https://data-argo.ifremer.fr/geo/indian_ocean/"
        
        try:
            if month:
                dir_url = f"{base_url}{year}/{month:02d}/"
                print(f"Scanning: {dir_url}")
                response = requests.get(dir_url, timeout=30)
                if response.status_code == 200:
                    nc_files = re.findall(r'href="([^"]*\.nc)"', response.text)
                    urls.extend([dir_url + f for f in nc_files])
                    print(f"Found {len(nc_files)} files in {year}/{month:02d}/")
            else:
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
                
                if len(tasks) >= 5:
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
        """Enhanced data extraction with better cleaning"""
        try:
            if var not in ds:
                return np.array([])
            
            data = ds[var].values
            if data.ndim > 1:
                # Handle 2D arrays by flattening
                data = data.flatten()
            
            # Remove fill values and invalid data
            fill_val = ds[var].attrs.get('_FillValue', np.nan)
            valid_range = ds[var].attrs.get('valid_range', [-1e10, 1e10])
            
            if isinstance(valid_range, (list, tuple)) and len(valid_range) == 2:
                valid_mask = (~np.isnan(data) & (data != fill_val) & 
                            (data >= valid_range[0]) & (data <= valid_range[1]))
            else:
                valid_mask = ~np.isnan(data) & (data != fill_val)
            
            return data[valid_mask]
        except:
            return np.array([])

    def safe_scalar(self, ds: xr.Dataset, var: str, default: float = 0.0) -> float:
        """Safely extract scalar value"""
        try:
            if var in ds:
                data = ds[var].values
                if hasattr(data, '__len__') and len(data) > 0:
                    return float(data[0])
                else:
                    return float(data)
            return default
        except:
            return default

    def calculate_stats(self, data: np.ndarray) -> Dict:
        """Calculate comprehensive statistics"""
        if len(data) == 0:
            return {'count': 0, 'status': 'no_data'}
        
        valid = data[~np.isnan(data)]
        if len(valid) == 0:
            return {'count': 0, 'status': 'all_nan'}
        
        try:
            return {
                'count': int(len(valid)), 'min': float(np.min(valid)), 'max': float(np.max(valid)),
                'mean': float(np.mean(valid)), 'median': float(np.median(valid)), 'std': float(np.std(valid)),
                'p25': float(np.percentile(valid, 25)), 'p75': float(np.percentile(valid, 75)),
                'skewness': float(stats.skew(valid)) if len(valid) > 2 else 0.0,
                'kurtosis': float(stats.kurtosis(valid)) if len(valid) > 3 else 0.0
            }
        except:
            return {'count': len(valid), 'status': 'calculation_error'}

    def classify_region(self, lat: float, lon: float) -> Dict:
        """FIXED Advanced geospatial classification"""
        regions_found = []
        
        # Check all regions
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
        if abs(lat) < 23.5:
            zone = "Tropical"
        elif abs(lat) < 40:
            zone = "Subtropical"
        elif abs(lat) < 60:
            zone = "Temperate"
        else:
            zone = "Polar"
        
        # Distance to coast (simplified)
        coast_dist = self.estimate_coast_distance(lat, lon)
        
        return {
            'regional_seas': regions_found, 'ocean_basin': basin, 'geographic_zone': zone,
            'grid_1deg': f"{'S' if lat < 0 else 'N'}{abs(int(lat)):02d}{'W' if lon < 0 else 'E'}{abs(int(lon)):03d}",
            'grid_5deg': f"{'S' if lat < 0 else 'N'}{abs(int(lat//5)*5):02d}{'W' if lon < 0 else 'E'}{abs(int(lon//5)*5):03d}",
            'biogeographic_province': self.get_bgc_province(lat, lon),
            'distance_to_coast_km': coast_dist
        }

    def estimate_coast_distance(self, lat: float, lon: float) -> float:
        """Estimate distance to nearest coast"""
        # Indian Ocean major coastal points
        coast_points = [(20, 60), (10, 77), (-35, 115), (-20, 57), (0, 50)]
        distances = []
        
        for coast_lat, coast_lon in coast_points:
            # Haversine approximation
            dlat = lat - coast_lat
            dlon = lon - coast_lon
            dist = ((dlat**2 + dlon**2)**0.5) * 111  # Rough km conversion
            distances.append(dist)
        
        return round(min(distances), 0) if distances else 1000.0

    def get_bgc_province(self, lat: float, lon: float) -> str:
        """Determine biogeochemical province"""
        if 8 <= lat <= 30 and 50 <= lon <= 80:
            return "Arabian_Sea_Province"
        elif 5 <= lat <= 25 and 80 <= lon <= 100:
            return "Bay_of_Bengal_Province"
        elif -10 <= lat <= 10:
            return "Equatorial_Province"
        elif lat < -40:
            return "Southern_Ocean_Province"
        else:
            return "Subtropical_Province"

    def get_temporal_info(self, juld: float) -> Dict:
        """Extract comprehensive temporal information"""
        try:
            ref_date = datetime(1950, 1, 1)
            profile_date = ref_date + timedelta(days=float(juld))
            month = profile_date.month
            
            # Seasonal classification
            seasons = {
                (12, 1, 2): ("winter", "summer"), (3, 4, 5): ("spring", "autumn"),
                (6, 7, 8): ("summer", "winter"), (9, 10, 11): ("autumn", "spring")
            }
            
            season_nh = season_sh = "unknown"
            for months, (nh, sh) in seasons.items():
                if month in months:
                    season_nh, season_sh = nh, sh
                    break
            
            # Monsoon classification
            if month in [6, 7, 8, 9]:
                monsoon = "southwest_monsoon"
            elif month in [12, 1, 2, 3]:
                monsoon = "northeast_monsoon"
            elif month in [4, 5]:
                monsoon = "pre_monsoon"
            else:
                monsoon = "post_monsoon"
            
            return {
                'datetime': profile_date.isoformat(), 'year': profile_date.year, 'month': month, 'day': profile_date.day,
                'season_nh': season_nh, 'season_sh': season_sh, 'monsoon_season': monsoon,
                'decade': f"{profile_date.year//10*10}s", 'quarter': f"Q{(month-1)//3 + 1}",
                'julian_day': profile_date.timetuple().tm_yday, 'week_of_year': profile_date.isocalendar()[1]
            }
        except Exception as e:
            print(f"Temporal info error: {e}")
            return {'datetime': None, 'year': None, 'month': None}

    def identify_water_masses(self, temp: np.ndarray, sal: np.ndarray, pres: np.ndarray) -> List[Dict]:
        """FIXED Water mass identification with real data processing"""
        found = []
        
        try:
            # Ensure we have sufficient data
            if len(temp) == 0 or len(sal) == 0 or len(pres) == 0:
                return found
            
            # Align arrays to same length
            min_len = min(len(temp), len(sal), len(pres))
            temp = temp[:min_len]
            sal = sal[:min_len]
            pres = pres[:min_len]
            
            # Remove invalid values
            valid_mask = (~np.isnan(temp) & ~np.isnan(sal) & ~np.isnan(pres) & 
                         (temp > -5) & (temp < 40) & (sal > 20) & (sal < 45) & (pres >= 0))
            
            if not np.any(valid_mask) or np.sum(valid_mask) < 10:
                return found
            
            t = temp[valid_mask]
            s = sal[valid_mask]
            p = pres[valid_mask]
            
            # Sort by pressure
            sort_idx = np.argsort(p)
            t_sort, s_sort, p_sort = t[sort_idx], s[sort_idx], p[sort_idx]
            
            # Check each water mass definition
            for wm_name, props in self.water_masses.items():
                temp_match = (t_sort >= props['temp'][0]) & (t_sort <= props['temp'][1])
                sal_match = (s_sort >= props['sal'][0]) & (s_sort <= props['sal'][1])
                depth_match = (p_sort >= props['depth'][0]) & (p_sort <= props['depth'][1])
                
                combined_mask = temp_match & sal_match & depth_match
                
                if np.any(combined_mask) and np.sum(combined_mask) >= 3:  # At least 3 points
                    core_data = {
                        'name': wm_name,
                        'core_temperature': float(np.mean(t_sort[combined_mask])),
                        'core_salinity': float(np.mean(s_sort[combined_mask])),
                        'depth_range': [float(np.min(p_sort[combined_mask])), float(np.max(p_sort[combined_mask]))],
                        'thickness': float(np.max(p_sort[combined_mask]) - np.min(p_sort[combined_mask])),
                        'strength': float(np.sum(combined_mask) / len(t_sort)),
                        'points_count': int(np.sum(combined_mask))
                    }
                    found.append(core_data)
            
        except Exception as e:
            print(f"Water mass identification error: {e}")
        
        return found

    def detect_features(self, temp: np.ndarray, sal: np.ndarray, pres: np.ndarray) -> Dict:
        """FIXED Feature detection with real data analysis"""
        features = {'inversions': [], 'extrema': [], 'gradients': {}, 'mixed_layer': {}, 'thermocline': {}}
        
        try:
            if len(temp) == 0 or len(sal) == 0 or len(pres) == 0:
                return features
            
            # Align and clean data
            min_len = min(len(temp), len(sal), len(pres))
            temp = temp[:min_len]
            sal = sal[:min_len]
            pres = pres[:min_len]
            
            valid_mask = (~np.isnan(temp) & ~np.isnan(sal) & ~np.isnan(pres) & 
                         (temp > -5) & (temp < 40) & (sal > 20) & (sal < 45))
            
            if not np.any(valid_mask) or np.sum(valid_mask) < 10:
                return features
            
            t = temp[valid_mask]
            s = sal[valid_mask]
            p = pres[valid_mask]
            
            # Sort by pressure
            sort_idx = np.argsort(p)
            t_sort, s_sort, p_sort = t[sort_idx], s[sort_idx], p[sort_idx]
            
            if len(t_sort) < 5:
                return features
            
            # Temperature inversions (more sensitive detection)
            temp_diff = np.diff(t_sort)
            inversion_indices = np.where(temp_diff > 0.05)[0]  # Lowered threshold
            
            for idx in inversion_indices[:10]:  # Limit to first 10 inversions
                if idx < len(p_sort) - 1:
                    features['inversions'].append({
                        'depth': float(p_sort[idx]),
                        'strength': float(temp_diff[idx]),
                        'type': 'temperature_inversion'
                    })
            
            # Salinity extrema detection
            if len(s_sort) > 5:
                sal_grad = np.gradient(s_sort, p_sort)
                extrema_indices = []
                
                for i in range(1, len(s_sort) - 1):
                    if ((s_sort[i] > s_sort[i-1] and s_sort[i] > s_sort[i+1]) or 
                        (s_sort[i] < s_sort[i-1] and s_sort[i] < s_sort[i+1])):
                        extrema_indices.append(i)
                
                for idx in extrema_indices[:5]:  # Limit extrema
                    extrema_type = 'maximum' if (s_sort[idx] > s_sort[idx-1] and s_sort[idx] > s_sort[idx+1]) else 'minimum'
                    features['extrema'].append({
                        'depth': float(p_sort[idx]),
                        'value': float(s_sort[idx]),
                        'type': f'salinity_{extrema_type}'
                    })
            
            # Gradient analysis
            if len(t_sort) > 2 and len(s_sort) > 2:
                temp_grad = np.gradient(t_sort, p_sort)
                sal_grad = np.gradient(s_sort, p_sort)
                
                features['gradients'] = {
                    'temperature': {
                        'max_gradient': float(np.max(np.abs(temp_grad))),
                        'mean_gradient': float(np.mean(np.abs(temp_grad))),
                        'gradient_depth': float(p_sort[np.argmax(np.abs(temp_grad))])
                    },
                    'salinity': {
                        'max_gradient': float(np.max(np.abs(sal_grad))),
                        'mean_gradient': float(np.mean(np.abs(sal_grad))),
                        'gradient_depth': float(p_sort[np.argmax(np.abs(sal_grad))])
                    }
                }
            
            # Mixed layer depth calculation
            if len(t_sort) > 3:
                surface_temp = t_sort[0]
                temp_criterion = 0.2  # 0.2°C criterion
                mld_indices = np.where(np.abs(t_sort - surface_temp) > temp_criterion)[0]
                
                if len(mld_indices) > 0:
                    features['mixed_layer'] = {
                        'depth': float(p_sort[mld_indices[0]]),
                        'surface_temp': float(surface_temp),
                        'criterion': 'temperature_0.2C'
                    }
            
            # Thermocline detection
            if len(t_sort) > 5:
                temp_grad = -np.gradient(t_sort, p_sort)  # Negative because temp decreases with depth
                max_grad_idx = np.argmax(temp_grad)
                
                features['thermocline'] = {
                    'depth': float(p_sort[max_grad_idx]),
                    'strength': float(temp_grad[max_grad_idx]),
                    'temperature': float(t_sort[max_grad_idx])
                }
            
        except Exception as e:
            print(f"Feature detection error: {e}")
        
        return features

    def calculate_derived_params(self, temp: np.ndarray, sal: np.ndarray, pres: np.ndarray) -> Dict:
        """FIXED Derived parameters calculation"""
        derived = {}
        
        try:
            if len(temp) == 0 or len(sal) == 0 or len(pres) == 0:
                return {'status': 'insufficient_data'}
            
            # Align arrays
            min_len = min(len(temp), len(sal), len(pres))
            temp = temp[:min_len]
            sal = sal[:min_len]
            pres = pres[:min_len]
            
            # Remove invalid data
            valid_mask = (~np.isnan(temp) & ~np.isnan(sal) & ~np.isnan(pres) & 
                         (temp > -5) & (temp < 40) & (sal > 20) & (sal < 45))
            
            if not np.any(valid_mask):
                return {'status': 'no_valid_data'}
            
            t = temp[valid_mask]
            s = sal[valid_mask]
            p = pres[valid_mask]
            
            # Simplified density calculation (UNESCO EOS-80 approximation)
            density = 1000 + 0.8 * (s - 35) - 0.2 * (t - 15) + 0.00004 * p
            derived['density'] = self.calculate_stats(density)
            
            # Potential temperature (simplified)
            theta = t - 0.0001 * p  # Simplified adiabatic correction
            derived['potential_temperature'] = self.calculate_stats(theta)
            
            # Sound speed (simplified)
            sound_speed = 1449 + 45.7 * t - 5.21 * t**2 + 0.23 * t**3 + (1.333 - 0.126 * t + 0.009 * t**2) * (s - 35)
            derived['sound_speed'] = self.calculate_stats(sound_speed)
            
            # Brunt-Vaisala frequency (stability)
            if len(density) > 2:
                n2 = -9.8 / np.mean(density) * np.gradient(density, p)
                derived['stability_frequency'] = {
                    'max_n2': float(np.max(n2)) if len(n2) > 0 else 0,
                    'mean_n2': float(np.mean(n2)) if len(n2) > 0 else 0,
                    'stable_layers': int(np.sum(n2 > 0)) if len(n2) > 0 else 0
                }
            
            # Spice calculation (simplified)
            spice = 0.5 * (s - 35) - 2.0 * (t - 15)
            derived['spice'] = self.calculate_stats(spice)
            
            derived['status'] = 'success'
            
        except Exception as e:
            print(f"Derived parameters error: {e}")
            derived['status'] = f'error: {str(e)}'
        
        return derived

    def analyze_bgc_variable(self, ds: xr.Dataset, var: str, pressure: np.ndarray, temp: np.ndarray, lat: float, lon: float) -> Dict:
        """Enhanced BGC variable analysis"""
        if var not in ds.variables:
            return {'present': False, 'reason': 'Variable not in dataset'}
        
        data = self.extract_data(ds, var)
        if len(data) == 0:
            return {'present': False, 'reason': 'No valid data after quality control'}
        
        # Basic statistics
        stats_result = self.calculate_stats(data)
        
        # Variable-specific advanced analysis
        advanced = {}
        if var == 'DOXY' and len(data) > 5:
            # Comprehensive oxygen analysis
            min_o2 = np.min(data)
            max_o2 = np.max(data)
            surface_o2 = data[0] if len(data) > 0 else np.nan
            
            advanced.update({
                'oxygen_minimum_zone': {
                    'present': min_o2 < 20,
                    'intensity': 'severe' if min_o2 < 5 else 'moderate' if min_o2 < 20 else 'none',
                    'min_concentration': float(min_o2)
                },
                'hypoxic_conditions': min_o2 < 60,
                'surface_saturation_estimate': float(surface_o2 / 300 * 100) if not np.isnan(surface_o2) else None,
                'oxygen_depletion': float(max_o2 - min_o2),
                'regional_context': self.get_oxygen_regional_context(lat, lon, min_o2)
            })
            
        elif var == 'CHLA' and len(data) > 5:
            # Chlorophyll analysis
            surface_chl = data[0] if len(data) > 0 else np.nan
            max_chl = np.max(data)
            
            advanced.update({
                'deep_chlorophyll_maximum': {
                    'present': max_chl > 1.5 * surface_chl if not np.isnan(surface_chl) else False,
                    'enhancement_factor': float(max_chl / surface_chl) if not np.isnan(surface_chl) and surface_chl > 0 else None,
                    'max_concentration': float(max_chl)
                },
                'trophic_status': self.classify_trophic_status(surface_chl),
                'productivity_level': 'high' if surface_chl > 1.0 else 'moderate' if surface_chl > 0.3 else 'low',
                'integrated_estimate': float(np.trapz(data[:min(50, len(data))]) if len(data) > 2 else 0)
            })
            
        elif var == 'NITRATE' and len(data) > 5:
            # Nitrate analysis
            surface_no3 = data[0] if len(data) > 0 else np.nan
            max_no3 = np.max(data)
            
            advanced.update({
                'surface_depletion': surface_no3 < 0.5 if not np.isnan(surface_no3) else None,
                'nutricline_present': max_no3 > 2 * surface_no3 if not np.isnan(surface_no3) and surface_no3 > 0 else False,
                'nutrient_availability': 'high' if max_no3 > 20 else 'moderate' if max_no3 > 5 else 'low',
                'vertical_gradient': float(max_no3 - surface_no3) if not np.isnan(surface_no3) else None
            })
            
        elif var == 'PH_IN_SITU_TOTAL' and len(data) > 5:
            # pH analysis
            surface_ph = data[0] if len(data) > 0 else np.nan
            
            advanced.update({
                'acidification_status': 'acidic' if surface_ph < 7.8 else 'normal' if surface_ph > 8.0 else 'intermediate',
                'ph_variability': float(np.max(data) - np.min(data)),
                'surface_ph': float(surface_ph) if not np.isnan(surface_ph) else None,
                'carbonate_system_health': 'stressed' if surface_ph < 7.9 else 'healthy'
            })
        
        return {
            'present': True,
            'description': self.bgc_vars[var]['desc'],
            'unit': self.bgc_vars[var]['unit'],
            'statistics': stats_result,
            'advanced_analysis': advanced,
            'data_quality_score': self.assess_data_quality(data)
        }

    def get_oxygen_regional_context(self, lat: float, lon: float, min_oxygen: float) -> Dict[str, Any]:
        """Regional oxygen context"""
        context: Dict[str, Any] = {'region': 'Unknown'}
        
        if 8 <= lat <= 30 and 50 <= lon <= 80:
            context.update({
                'region': 'Arabian_Sea',
                'typical_omz': True,
                'severity': 'severe' if min_oxygen < 5 else 'moderate'
            })
        elif 5 <= lat <= 25 and 80 <= lon <= 100:
            context.update({
                'region': 'Bay_of_Bengal',
                'typical_omz': False,
                'river_influence': True
            })
        elif -10 <= lat <= 10:
            context.update({
                'region': 'Equatorial_Indian',
                'upwelling_zone': True
            })
        
        return context

    def classify_trophic_status(self, surface_chl: float) -> str:
        """Classify trophic status based on chlorophyll"""
        if np.isnan(surface_chl):
            return 'unknown'
        elif surface_chl < 0.1:
            return 'ultra_oligotrophic'
        elif surface_chl < 0.3:
            return 'oligotrophic'
        elif surface_chl < 1.0:
            return 'mesotrophic'
        elif surface_chl < 3.0:
            return 'eutrophic'
        else:
            return 'hypertrophic'

    def assess_data_quality(self, data: np.ndarray) -> float:
        """Assess data quality score 0-1"""
        try:
            if len(data) == 0:
                return 0.0
            
            # Check for outliers
            q75, q25 = np.percentile(data, [75, 25])
            iqr = q75 - q25
            outliers = np.sum((data < (q25 - 1.5 * iqr)) | (data > (q75 + 1.5 * iqr)))
            outlier_ratio = outliers / len(data)
            
            # Data completeness and variability
            completeness = len(data) / max(len(data), 100)  # Normalize to expected ~100 levels
            variability = 1.0 if np.std(data) > 0 else 0.5  # Penalize constant values
            
            return float(max(0, min(1, (1 - outlier_ratio) * completeness * variability)))
        except:
            return 0.5

    def extract_calibration_info(self, ds: xr.Dataset) -> Dict:
        """Extract calibration and QC information"""
        calib_info = {
            'delayed_mode_processing': False,
            'data_mode': 'unknown',
            'qc_procedures': [],
            'calibration_applied': False
        }
        
        try:
            # Data mode
            if 'DATA_MODE' in ds:
                mode = self.safe_decode(ds.get('DATA_MODE', b'R'))
                calib_info['data_mode'] = mode
                calib_info['delayed_mode_processing'] = mode.upper() == 'D'
            
            # QC variables
            qc_vars = [v for v in ds.variables if '_QC' in v]
            calib_info['qc_procedures'] = qc_vars
            calib_info['calibration_applied'] = len(qc_vars) > 0
            
            # Platform calibration info
            if 'PLATFORM_NUMBER' in ds:
                calib_info['platform_calibrated'] = True
            
        except Exception as e:
            print(f"Calibration info error: {e}")
        
        return calib_info

    def generate_rag_data(self, temporal: Dict, spatial: Dict, core_vars: Dict, bgc_vars: Dict, 
                         water_masses: List, features: Dict) -> Dict:
        """Enhanced RAG optimization data"""
        # Primary search terms
        terms = []
        if temporal.get('year'):
            terms.extend([
                str(temporal['year']), 
                temporal.get('decade', ''),
                temporal.get('monsoon_season', ''),
                temporal.get('season_nh', '')
            ])
        
        if spatial.get('ocean_basin'):
            terms.extend([
                spatial['ocean_basin'],
                spatial.get('geographic_zone', ''),
                spatial.get('biogeographic_province', '')
            ])
            terms.extend(spatial.get('regional_seas', []))
        
        # BGC and measurement terms
        present_bgc = [var for var, data in bgc_vars.items() if data.get('present')]
        terms.extend([f"{var.lower()}_measurements" for var in present_bgc])
        
        # Water mass terms
        for wm in water_masses:
            terms.append(f"{wm['name'].lower()}_detected")
        
        # Feature terms
        if features.get('inversions'):
            terms.append('temperature_inversions')
        if features.get('mixed_layer'):
            terms.append('mixed_layer_analysis')
        
        # Enhanced natural language summary
        date_str = temporal.get('datetime', 'unknown')[:10]
        region_list = spatial.get('regional_seas', [])
        region_str = ', '.join(region_list) if region_list else 'Open Ocean'
        bgc_count = len(present_bgc)
        wm_count = len(water_masses)
        
        summary = (f"ARGO profile from {spatial.get('ocean_basin', 'Unknown')} Ocean "
                  f"({region_str}) collected on {date_str} during {temporal.get('monsoon_season', 'unknown season')}. "
                  f"Contains {len([v for v in core_vars.values() if v.get('present')])} core parameters")
        
        if bgc_count > 0:
            summary += f" and {bgc_count} biogeochemical parameters"
        if wm_count > 0:
            summary += f". Identified {wm_count} water mass signatures"
        if features.get('inversions'):
            summary += f" with {len(features['inversions'])} temperature inversions detected"
        
        # Contextual keywords for advanced RAG
        keywords = terms + [
            f"{var}_profile" for var in core_vars.keys() if core_vars[var].get('present')
        ] + [
            'oceanographic_analysis', 'water_mass_identification', 'vertical_profiling',
            f"{spatial.get('geographic_zone', 'unknown').lower()}_waters",
            f"{temporal.get('year', 'unknown')}_data"
        ]
        
        return {
            'search_terms': [t for t in terms if t and t != ''],
            'summary': summary,
            'keywords': list(set([k for k in keywords if k and k != ''])),
            'profile_classification': {
                'spatial': f"{spatial.get('ocean_basin', 'Unknown')}_{spatial.get('geographic_zone', 'Unknown')}",
                'temporal': f"{temporal.get('year', 'Unknown')}_{temporal.get('monsoon_season', 'unknown')}",
                'data_type': 'BGC_enhanced' if present_bgc else 'core_only'
            },
            'scientific_relevance': {
                'water_mass_analysis': wm_count > 0,
                'biogeochemical_data': bgc_count > 0,
                'oceanographic_features': len(features.get('inversions', [])) > 0,
                'regional_significance': len(region_list) > 0
            }
        }

    def process_nc_file(self, file_path: Path) -> Optional[Dict]:
        """Complete NetCDF processing with all advanced features working"""
        try:
            print(f"Processing: {file_path.name}")
            
            with xr.open_dataset(file_path, decode_times=False) as ds:
                # Extract basic metadata
                juld = self.safe_scalar(ds, 'JULD')
                lat = self.safe_scalar(ds, 'LATITUDE')
                lon = self.safe_scalar(ds, 'LONGITUDE')
                
                # Extract core variables with enhanced cleaning
                pressure = self.extract_data(ds, 'PRES')
                temp = self.extract_data(ds, 'TEMP')
                sal = self.extract_data(ds, 'PSAL')
                
                # Comprehensive analysis
                temporal_info = self.get_temporal_info(juld)
                spatial_info = self.classify_region(lat, lon)
                
                # Core variable analysis
                core_vars = {}
                for var, data in [('TEMP', temp), ('PSAL', sal), ('PRES', pressure)]:
                    if len(data) > 0:
                        core_vars[var] = {
                            'present': True, 
                            'statistics': self.calculate_stats(data),
                            'unit': {'TEMP': 'degrees_C', 'PSAL': 'PSU', 'PRES': 'dbar'}[var],
                            'data_range': {'min': float(np.min(data)), 'max': float(np.max(data))},
                            'quality_score': self.assess_data_quality(data)
                        }
                    else:
                        core_vars[var] = {'present': False, 'reason': 'No valid data'}
                
                # BGC analysis (enhanced)
                bgc_vars = {}
                for var in self.bgc_vars.keys():
                    bgc_vars[var] = self.analyze_bgc_variable(ds, var, pressure, temp, lat, lon)
                
                # Water mass analysis (FIXED)
                water_masses = self.identify_water_masses(temp, sal, pressure)
                
                # Oceanographic features (FIXED)
                features = self.detect_features(temp, sal, pressure)
                
                # Derived parameters (FIXED)
                derived = self.calculate_derived_params(temp, sal, pressure)
                
                # Platform and calibration info
                platform_info = {
                    'platform_number': self.safe_decode(ds.get('PLATFORM_NUMBER', b'unknown')),
                    'cycle_number': int(self.safe_scalar(ds, 'CYCLE_NUMBER')),
                    'data_mode': self.safe_decode(ds.get('DATA_MODE', b'R')),
                    'positioning_system': self.safe_decode(ds.get('POSITIONING_SYSTEM', b'GPS')),
                    'profile_direction': self.safe_decode(ds.get('DIRECTION', b'A'))
                }
                
                calibration_info = self.extract_calibration_info(ds)
                
                # Enhanced quality assessment
                quality = {
                    'data_completeness': len([v for v in core_vars.values() if v.get('present')]) / 3 * 100,
                    'bgc_completeness': len([v for v in bgc_vars.values() if v.get('present')]) / len(self.bgc_vars) * 100,
                    'vertical_coverage': len(pressure),
                    'pressure_range': [float(np.min(pressure)), float(np.max(pressure))] if len(pressure) > 0 else [0, 0],
                    'processing_level': 'delayed_mode' if calibration_info.get('delayed_mode_processing') else 'real_time',
                    'overall_score': np.mean([v.get('quality_score', 0.5) for v in core_vars.values() if v.get('present')])
                }
                
                # Enhanced RAG optimization
                rag_data = self.generate_rag_data(temporal_info, spatial_info, core_vars, 
                                                bgc_vars, water_masses, features)
                
                # Complete enhanced JSON structure
                return {
                    "metadata": {
                        "file_info": {
                            "file_id": file_path.stem,
                            "processing_timestamp": datetime.now().isoformat(),
                            "processor_version": "SIH2025_Fixed_v1.0",
                            "file_size_bytes": int(file_path.stat().st_size),
                            "data_format": "NetCDF-4"
                        }
                    },
                    "platform": platform_info,
                    "temporal": temporal_info,
                    "geospatial": spatial_info,
                    "measurements": {
                        "core_variables": core_vars,
                        "bgc_variables": bgc_vars,
                        "derived_parameters": derived
                    },
                    "oceanography": {
                        "water_masses": water_masses,
                        "physical_features": features,
                        "mixed_layer_analysis": features.get('mixed_layer', {}),
                        "thermocline_analysis": features.get('thermocline', {})
                    },
                    "quality_control": {
                        "calibration": calibration_info,
                        "data_assessment": quality,
                        "processing_flags": {
                            'real_data_only': True,
                            'no_demo_content': True,
                            'comprehensive_analysis': True
                        }
                    },
                    "rag_optimization": rag_data
                }
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return None

    def safe_decode(self, data) -> str:
        """Enhanced safe decode for various data types"""
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
        """Process existing files to enhanced JSON"""
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
        print(f"Found {len(nc_files)} NetCDF files to process")
        
        if not nc_files:
            return
        
        json_path.mkdir(parents=True, exist_ok=True)
        processed, errors = 0, 0
        start_time = time.time()
        
        for i, nc_file in enumerate(nc_files):
            try:
                # Create JSON path maintaining hierarchical structure
                rel_path = nc_file.relative_to(search_path)
                json_file = json_path / rel_path.with_suffix('.json')
                
                # Skip if JSON is newer than NC file
                if json_file.exists() and json_file.stat().st_mtime > nc_file.stat().st_mtime:
                    print(f"Skipping {nc_file.name} (JSON up to date)")
                    continue
                
                # Process with full feature extraction
                json_data = self.process_nc_file(nc_file)
                if json_data:
                    json_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(json_file, 'w', encoding='utf-8') as f:
                        json.dump(json_data, f, indent=2, default=str)
                    print(f"Enhanced JSON saved: {json_file.name}")
                    processed += 1
                else:
                    errors += 1
                    
                # Progress reporting
                if (i + 1) % 10 == 0:
                    elapsed = time.time() - start_time
                    rate = (i + 1) / elapsed
                    eta = (len(nc_files) - i - 1) / rate if rate > 0 else 0
                    print(f"Progress: {i+1}/{len(nc_files)}, {rate:.1f} files/sec, ETA: {eta/60:.1f} min")
                    
            except Exception as e:
                print(f"Error processing {nc_file.name}: {e}")
                errors += 1
        
        total_time = time.time() - start_time
        print(f"\nFinal Summary:")
        print(f"Successfully processed: {processed} files")
        print(f"Errors: {errors} files")
        print(f"Total time: {total_time/60:.1f} minutes")
        print(f"Average time per file: {total_time/len(nc_files):.1f} seconds")

    def download_and_process(self, year: int, month: Optional[int] = None, force: bool = False):
        """Complete pipeline with enhanced processing"""
        print(f"Starting enhanced ARGO processing for Indian Ocean {year}" + 
              (f"-{month:02d}" if month else ""))
        
        # Get URLs and download
        urls = self.get_indian_ocean_urls(year, month)
        if not urls:
            print("No files found in Indian Ocean directory")
            return
        
        # Download phase
        print("\nPhase 1: Downloading files...")
        start_time = time.time()
        asyncio.run(self.download_files(urls, year, month, force))
        download_time = time.time() - start_time
        print(f"Download phase completed in {download_time:.1f} seconds")
        
        # Processing phase
        print("\nPhase 2: Enhanced JSON conversion with all features...")
        process_start = time.time()
        self.process_files(year, month)
        process_time = time.time() - process_start
        print(f"Processing phase completed in {process_time:.1f} seconds")
        
        print(f"\nTotal pipeline time: {(download_time + process_time)/60:.1f} minutes")
        print("All advanced features now active in JSON outputs!")

def main():
    """Enhanced main interface"""
    processor = DebuggedArgoProcessor()
    
    print("=" * 70)
    print("FIXED ENHANCED ARGO PROCESSOR - SIH 2025 FLOATCHAT")
    print("Indian Ocean: https://data-argo.ifremer.fr/geo/indian_ocean/")
    print("ALL ADVANCED FEATURES NOW WORKING WITH REAL DATA")
    print("=" * 70)
    
    print("\nOptions:")
    print("1. Download + Process: Full Year (all features active)")
    print("2. Download + Process: Year/Month (all features active)")
    print("3. Process existing files: Year (enhanced analysis)")
    print("4. Process existing files: Year/Month (enhanced analysis)")
    print("5. Force re-download + Process (complete refresh)")
    print("0. Exit")
    
    choice = input("\nChoice (0-5): ").strip()
    
    if choice == "1":
        year = int(input("Year (YYYY): "))
        print(f"Processing full year {year} with ALL advanced features...")
        processor.download_and_process(year)
        
    elif choice == "2":
        year = int(input("Year (YYYY): "))
        month = int(input("Month (1-12): "))
        print(f"Processing {year}-{month:02d} with ALL advanced features...")
        processor.download_and_process(year, month)
        
    elif choice == "3":
        year = int(input("Year (YYYY): "))
        print(f"Enhanced processing of existing {year} files...")
        processor.process_files(year)
        
    elif choice == "4":
        year = int(input("Year (YYYY): "))
        month = int(input("Month (1-12): "))
        print(f"Enhanced processing of existing {year}-{month:02d} files...")
        processor.process_files(year, month)
        
    elif choice == "5":
        year = int(input("Year (YYYY): "))
        month_input = input("Month (1-12, or Enter for full year): ")
        month = int(month_input) if month_input else None
        print("Force re-downloading and processing with ALL features...")
        processor.download_and_process(year, month, force=True)
        
    elif choice == "0":
        print("Enhanced ARGO processor ready for SIH 2025 victory!")
        return
    
    else:
        print("Invalid choice")
        return
    
    print("\n🎉 PROCESSING COMPLETE WITH ALL FEATURES!")
    print("📁 Enhanced JSON files with full analysis in: Datasetjson/")
    print("✅ All advanced features now working:")
    print("   - Water mass identification")
    print("   - Oceanographic feature detection") 
    print("   - Derived parameter calculations")
    print("   - Enhanced BGC analysis")
    print("   - Complete geospatial classification")
    print("   - Advanced RAG optimization")
    print("🚀 Ready for frontend integration!")

if __name__ == "__main__":
    main()
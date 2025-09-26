import netCDF4 as nc
import numpy as np
import json
from datetime import datetime
import tempfile
import os

class NCConverter:
    """Convert NetCDF ARGO files to JSON format"""
    
    def __init__(self):
        self.supported_vars = {
            'TEMP': 'temperature',
            'PSAL': 'salinity',
            'PRES': 'pressure',
            'DOXY': 'oxygen',
            'LATITUDE': 'latitude',
            'LONGITUDE': 'longitude',
            'JULD': 'time'
        }
    
    def convert_uploaded_file(self, uploaded_file):
        """Convert Streamlit uploaded file to JSON"""
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.nc') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        try:
            # Convert the temporary file
            result = self.convert_nc_file(tmp_path)
            return result
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    def convert_nc_file(self, nc_file_path):
        """Convert NC file to JSON format"""
        try:
            dataset = nc.Dataset(nc_file_path, 'r')
            
            # Initialize data structure
            data = {
                'temporal': {},
                'geospatial': {},
                'measurements': {
                    'core_variables': {}
                },
                'platform': {},
                'oceanography': {
                    'water_masses': []
                },
                'quality_control': {
                    'data_assessment': {}
                },
                '_source': 'uploaded_nc_file'
            }
            
            # Extract temporal data
            data['temporal'] = self._extract_temporal(dataset)
            
            # Extract geospatial data
            data['geospatial'] = self._extract_geospatial(dataset)
            
            # Extract measurements
            data['measurements']['core_variables'] = self._extract_measurements(dataset)
            
            # Extract platform info
            data['platform'] = self._extract_platform(dataset)
            
            # Add basic quality assessment
            data['quality_control']['data_assessment'] = {
                'overall_score': 7.5,
                'status': 'uploaded'
            }
            
            dataset.close()
            return data
            
        except Exception as e:
            raise Exception(f"NC conversion error: {str(e)}")
    
    def _extract_temporal(self, dataset):
        """Extract temporal information"""
        temporal = {}
        
        try:
            # Get time variable (JULD in ARGO files)
            if 'JULD' in dataset.variables:
                juld = dataset.variables['JULD'][:]
                if len(juld) > 0 and not np.ma.is_masked(juld[0]):
                    # Convert JULD (days since 1950-01-01) to datetime
                    ref_date = datetime(1950, 1, 1)
                    date_obj = ref_date + pd.Timedelta(days=float(juld[0]))
                    temporal['datetime'] = date_obj.isoformat()
                    temporal['year'] = date_obj.year
                    temporal['month'] = date_obj.month
                    temporal['day'] = date_obj.day
            
            # Fallback to current date if no time found
            if not temporal:
                now = datetime.now()
                temporal['datetime'] = now.isoformat()
                temporal['year'] = now.year
                temporal['month'] = now.month
                temporal['day'] = now.day
            
            # Add season
            month = temporal.get('month', 1)
            if month in [12, 1, 2]:
                temporal['season_nh'] = 'winter'
            elif month in [3, 4, 5]:
                temporal['season_nh'] = 'spring'
            elif month in [6, 7, 8]:
                temporal['season_nh'] = 'summer'
            else:
                temporal['season_nh'] = 'autumn'
                
        except Exception as e:
            print(f"Temporal extraction error: {e}")
            now = datetime.now()
            temporal = {
                'datetime': now.isoformat(),
                'year': now.year,
                'month': now.month,
                'day': now.day
            }
        
        return temporal
    
    def _extract_geospatial(self, dataset):
        """Extract geospatial information"""
        geospatial = {
            'regional_seas': ['Uploaded Data'],
            'ocean_basin': 'Unknown'
        }
        
        try:
            # Extract latitude
            if 'LATITUDE' in dataset.variables:
                lat = dataset.variables['LATITUDE'][:]
                if len(lat) > 0 and not np.ma.is_masked(lat[0]):
                    geospatial['latitude'] = float(lat[0])
            
            # Extract longitude
            if 'LONGITUDE' in dataset.variables:
                lon = dataset.variables['LONGITUDE'][:]
                if len(lon) > 0 and not np.ma.is_masked(lon[0]):
                    geospatial['longitude'] = float(lon[0])
            
            # Determine region based on coordinates
            if 'latitude' in geospatial and 'longitude' in geospatial:
                lat = geospatial['latitude']
                lon = geospatial['longitude']
                
                # Indian Ocean regions
                if 10 <= lat <= 25 and 50 <= lon <= 75:
                    geospatial['regional_seas'] = ['Arabian_Sea']
                    geospatial['ocean_basin'] = 'Indian_Ocean'
                elif 5 <= lat <= 25 and 80 <= lon <= 100:
                    geospatial['regional_seas'] = ['Bay_of_Bengal']
                    geospatial['ocean_basin'] = 'Indian_Ocean'
                elif lat < -40:
                    geospatial['regional_seas'] = ['Southern_Ocean']
                    geospatial['ocean_basin'] = 'Southern_Ocean'
                elif -10 <= lat <= 10 and 50 <= lon <= 100:
                    geospatial['regional_seas'] = ['Equatorial_Indian']
                    geospatial['ocean_basin'] = 'Indian_Ocean'
                
                # Add grid reference
                lat_dir = 'N' if lat >= 0 else 'S'
                lon_dir = 'E' if lon >= 0 else 'W'
                geospatial['grid_1deg'] = f"{lat_dir}{abs(int(lat)):02d}{lon_dir}{abs(int(lon)):03d}"
                
        except Exception as e:
            print(f"Geospatial extraction error: {e}")
        
        return geospatial
    
    def _extract_measurements(self, dataset):
        """Extract measurement data"""
        measurements = {}
        
        # Core variables to extract
        core_vars = {
            'TEMP': 'temperature',
            'PSAL': 'salinity', 
            'PRES': 'pressure',
            'DOXY': 'oxygen'
        }
        
        for var_name, description in core_vars.items():
            try:
                if var_name in dataset.variables:
                    var_data = dataset.variables[var_name][:]
                    
                    # Handle masked arrays
                    if np.ma.is_masked(var_data):
                        var_data = var_data.compressed()
                    
                    if len(var_data) > 0:
                        # Remove invalid values
                        valid_data = var_data[(var_data > -990) & (var_data < 9999)]
                        
                        if len(valid_data) > 0:
                            measurements[var_name] = {
                                'present': True,
                                'statistics': {
                                    'min': float(np.min(valid_data)),
                                    'max': float(np.max(valid_data)),
                                    'mean': float(np.mean(valid_data)),
                                    'std': float(np.std(valid_data)),
                                    'count': int(len(valid_data))
                                }
                            }
            except Exception as e:
                print(f"Error extracting {var_name}: {e}")
                continue
        
        return measurements
    
    def _extract_platform(self, dataset):
        """Extract platform information"""
        platform = {}
        
        try:
            # Try to get platform number
            if 'PLATFORM_NUMBER' in dataset.variables:
                platform_num = dataset.variables['PLATFORM_NUMBER'][:]
                if len(platform_num) > 0:
                    platform['platform_number'] = str(platform_num[0])
            
            # Try global attributes
            if hasattr(dataset, 'platform_number'):
                platform['platform_number'] = str(dataset.platform_number)
            
            # Fallback
            if 'platform_number' not in platform:
                platform['platform_number'] = 'UPLOADED'
                
        except Exception as e:
            print(f"Platform extraction error: {e}")
            platform['platform_number'] = 'UPLOADED'
        
        return platform

# For easy import
def convert_nc_to_json(uploaded_file):
    """Quick function to convert uploaded NC file"""
    converter = NCConverter()
    return converter.convert_uploaded_file(uploaded_file)
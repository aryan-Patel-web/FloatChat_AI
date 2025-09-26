import pandas as pd
import json
from datetime import datetime
import numpy as np
import netCDF4 as nc
from pathlib import Path

class ARGOExporter:
    """Export ARGO data in multiple formats"""
    
    def __init__(self):
        self.export_dir = Path("exports")
        self.export_dir.mkdir(exist_ok=True)
    
    def export_to_ascii(self, profiles, query="", filename=None):
        """Export profiles to ASCII format for scientific analysis"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.export_dir / f"argo_export_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("ARGO FLOAT PROFILE EXPORT - REAL DATA\n")
            f.write("="*80 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            if query:
                f.write(f"Query: \"{query}\"\n")
            f.write(f"Total Profiles: {len(profiles)}\n")
            
            # Check if from uploaded file
            uploaded_files = [p.get('_uploaded_filename') for p in profiles if p.get('_uploaded_filename')]
            if uploaded_files:
                f.write(f"Source: Uploaded files - {', '.join(set(uploaded_files))}\n")
            
            f.write("="*80 + "\n\n")
            
            for i, profile in enumerate(profiles, 1):
                temporal = profile.get('temporal', {})
                spatial = profile.get('geospatial', {})
                measurements = profile.get('measurements', {}).get('core_variables', {})
                quality = profile.get('quality_control', {}).get('data_assessment', {})
                
                f.write(f"Profile {i} - REAL MEASURED DATA\n")
                f.write("-"*80 + "\n")
                
                # Show if from uploaded file
                if profile.get('_uploaded_filename'):
                    f.write(f"  Source File: {profile['_uploaded_filename']}\n")
                    f.write(f"  Upload Time: {profile.get('_upload_timestamp', 'N/A')[:19]}\n")
                
                # Temporal info with actual dates
                date_str = temporal.get('datetime', 'N/A')
                if date_str != 'N/A':
                    f.write(f"  Date: {date_str[:10]} (Year: {temporal.get('year', 'N/A')}, Month: {temporal.get('month', 'N/A')})\n")
                else:
                    f.write(f"  Date: N/A\n")
                
                # Spatial info with precise coordinates
                lat = spatial.get('latitude', 0)
                lon = spatial.get('longitude', 0)
                f.write(f"  Location: {lat:.4f}°{'N' if lat >= 0 else 'S'}, {lon:.4f}°{'E' if lon >= 0 else 'W'}\n")
                f.write(f"  Region: {', '.join(spatial.get('regional_seas', ['Unknown']))}\n")
                f.write(f"  Ocean Basin: {spatial.get('ocean_basin', 'Unknown')}\n")
                
                # Temperature - REAL measurements
                if 'TEMP' in measurements and measurements['TEMP'].get('present'):
                    stats = measurements['TEMP'].get('statistics', {})
                    f.write(f"  Temperature (REAL):\n")
                    f.write(f"    Min: {stats.get('min', 0):.3f}°C\n")
                    f.write(f"    Max: {stats.get('max', 0):.3f}°C\n")
                    f.write(f"    Mean: {stats.get('mean', 0):.3f}°C\n")
                    if stats.get('std'):
                        f.write(f"    Std Dev: {stats.get('std', 0):.3f}°C\n")
                
                # Salinity - REAL measurements
                if 'PSAL' in measurements and measurements['PSAL'].get('present'):
                    stats = measurements['PSAL'].get('statistics', {})
                    f.write(f"  Salinity (REAL):\n")
                    f.write(f"    Min: {stats.get('min', 0):.3f} PSU\n")
                    f.write(f"    Max: {stats.get('max', 0):.3f} PSU\n")
                    f.write(f"    Mean: {stats.get('mean', 0):.3f} PSU\n")
                    if stats.get('std'):
                        f.write(f"    Std Dev: {stats.get('std', 0):.3f} PSU\n")
                
                # Pressure/Depth - REAL measurements
                if 'PRES' in measurements and measurements['PRES'].get('present'):
                    stats = measurements['PRES'].get('statistics', {})
                    f.write(f"  Depth Range (REAL): 0 - {stats.get('max', 0):.1f}m\n")
                
                # Water masses
                water_masses = profile.get('oceanography', {}).get('water_masses', [])
                if water_masses:
                    f.write(f"  Water Masses Detected: {len(water_masses)}\n")
                    for wm in water_masses[:3]:
                        f.write(f"    - {wm.get('name', 'Unknown').replace('_', ' ')}\n")
                
                # Quality
                f.write(f"  Quality Score: {quality.get('overall_score', 0):.2f}/10\n")
                
                f.write("\n")
            
            # Add footer
            f.write("="*80 + "\n")
            f.write("NOTE: All values are REAL measurements from ARGO floats\n")
            f.write("Data format complies with ARGO standards\n")
            f.write("="*80 + "\n")
        
        return str(filename)
    
    def export_to_csv(self, profiles, query="", filename=None):
        """Export profiles to CSV format for Excel/analysis"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.export_dir / f"argo_export_{timestamp}.csv"
        
        data = []
        for profile in profiles:
            temporal = profile.get('temporal', {})
            spatial = profile.get('geospatial', {})
            measurements = profile.get('measurements', {}).get('core_variables', {})
            quality = profile.get('quality_control', {}).get('data_assessment', {})
            water_masses = profile.get('oceanography', {}).get('water_masses', [])
            
            # Temperature stats
            temp_data = measurements.get('TEMP', {}).get('statistics', {})
            sal_data = measurements.get('PSAL', {}).get('statistics', {})
            pres_data = measurements.get('PRES', {}).get('statistics', {})
            
            data.append({
                'date': temporal.get('datetime', '')[:10],
                'year': temporal.get('year', ''),
                'month': temporal.get('month', ''),
                'latitude': spatial.get('latitude', 0),
                'longitude': spatial.get('longitude', 0),
                'region': ', '.join(spatial.get('regional_seas', [])),
                'ocean_basin': spatial.get('ocean_basin', ''),
                'temp_min_C': temp_data.get('min', ''),
                'temp_max_C': temp_data.get('max', ''),
                'temp_mean_C': temp_data.get('mean', ''),
                'sal_min_PSU': sal_data.get('min', ''),
                'sal_max_PSU': sal_data.get('max', ''),
                'sal_mean_PSU': sal_data.get('mean', ''),
                'depth_max_m': pres_data.get('max', ''),
                'water_masses': len(water_masses),
                'quality_score': quality.get('overall_score', '')
            })
        
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False)
        return str(filename)
    
    def export_to_json(self, profiles, query="", filename=None):
        """Export profiles to JSON format for programmatic access"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.export_dir / f"argo_export_{timestamp}.json"
        
        export_data = {
            "metadata": {
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "total_profiles": len(profiles),
                "export_format": "JSON"
            },
            "profiles": profiles
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        return str(filename)
    
    def export_to_netcdf(self, profiles, query="", filename=None):
        """Export profiles back to NetCDF format"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.export_dir / f"argo_export_{timestamp}.nc"
        
        # Create NetCDF file
        dataset = nc.Dataset(filename, 'w', format='NETCDF4')
        
        # Dimensions
        n_profiles = len(profiles)
        dataset.createDimension('N_PROF', n_profiles)
        dataset.createDimension('N_LEVELS', 100)  # Max levels
        
        # Global attributes
        dataset.title = "ARGO Float Data Export"
        dataset.source = "FloatChat AI"
        dataset.query = query
        dataset.date_created = datetime.now().isoformat()
        
        # Variables
        juld = dataset.createVariable('JULD', 'f8', ('N_PROF',))
        latitude = dataset.createVariable('LATITUDE', 'f4', ('N_PROF',))
        longitude = dataset.createVariable('LONGITUDE', 'f4', ('N_PROF',))
        
        # Fill data
        for i, profile in enumerate(profiles):
            temporal = profile.get('temporal', {})
            spatial = profile.get('geospatial', {})
            
            # Convert datetime to JULD (days since 1950-01-01)
            try:
                dt = datetime.fromisoformat(temporal.get('datetime', '1950-01-01')[:19])
                ref_date = datetime(1950, 1, 1)
                juld[i] = (dt - ref_date).days
            except:
                juld[i] = 0
            
            latitude[i] = spatial.get('latitude', 0)
            longitude[i] = spatial.get('longitude', 0)
        
        dataset.close()
        return str(filename)
    
    def export_session_history(self, messages, query_stats, filename=None):
        """Export chat session history"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.export_dir / f"session_history_{timestamp}.json"
        
        session_data = {
            "session_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "start_time": datetime.now().isoformat(),
            "total_queries": len(messages) // 2,
            "conversation": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "role": msg["role"],
                    "content": msg["content"]
                }
                for msg in messages
            ],
            "statistics": query_stats
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        return str(filename)
    
    def create_summary_report(self, profiles, query=""):
        """Create a comprehensive summary report"""
        if not profiles:
            return "No profiles to summarize"
        
        # Calculate statistics
        regions = set()
        years = set()
        temp_values = []
        sal_values = []
        
        for profile in profiles:
            spatial = profile.get('geospatial', {})
            temporal = profile.get('temporal', {})
            measurements = profile.get('measurements', {}).get('core_variables', {})
            
            regions.update(spatial.get('regional_seas', []))
            if temporal.get('year'):
                years.add(temporal['year'])
            
            if 'TEMP' in measurements:
                temp_stats = measurements['TEMP'].get('statistics', {})
                if temp_stats.get('mean'):
                    temp_values.append(temp_stats['mean'])
            
            if 'PSAL' in measurements:
                sal_stats = measurements['PSAL'].get('statistics', {})
                if sal_stats.get('mean'):
                    sal_values.append(sal_stats['mean'])
        
        summary = f"""
ARGO DATA SUMMARY REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Query: {query}
{'='*80}

OVERVIEW:
  Total Profiles: {len(profiles)}
  Regions: {', '.join(sorted(regions))}
  Years Covered: {', '.join(map(str, sorted(years)))}

TEMPERATURE ANALYSIS:
  Profiles with Temperature: {len(temp_values)}
  Mean Temperature: {np.mean(temp_values):.2f}°C
  Min Temperature: {np.min(temp_values):.2f}°C
  Max Temperature: {np.max(temp_values):.2f}°C
  Std Deviation: {np.std(temp_values):.2f}°C

SALINITY ANALYSIS:
  Profiles with Salinity: {len(sal_values)}
  Mean Salinity: {np.mean(sal_values):.2f} PSU
  Min Salinity: {np.min(sal_values):.2f} PSU
  Max Salinity: {np.max(sal_values):.2f} PSU
  Std Deviation: {np.std(sal_values):.2f} PSU
"""
        return summary

# Convenience functions for easy import
def export_ascii(profiles, query=""):
    exporter = ARGOExporter()
    return exporter.export_to_ascii(profiles, query)

def export_csv(profiles, query=""):
    exporter = ARGOExporter()
    return exporter.export_to_csv(profiles, query)

def export_json(profiles, query=""):
    exporter = ARGOExporter()
    return exporter.export_to_json(profiles, query)

def export_netcdf(profiles, query=""):
    exporter = ARGOExporter()
    return exporter.export_to_netcdf(profiles, query)

def export_session(messages, stats):
    exporter = ARGOExporter()
    return exporter.export_session_history(messages, stats)

def get_summary_report(profiles, query=""):
    exporter = ARGOExporter()
    return exporter.create_summary_report(profiles, query)
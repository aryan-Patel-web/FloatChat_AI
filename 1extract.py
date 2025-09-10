#!/usr/bin/env python3
"""
Enhanced ARGO Data Downloader for Indian Ocean
Organized folder structure: Dataset/YEAR/MONTH/
Supports multiple years and months
"""

import os
import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin
from pathlib import Path
from datetime import datetime

class EnhancedArgoDownloader:
    def __init__(self, base_folder="Dataset"):
        self.base_folder = Path(base_folder)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Create base folder structure
        self.create_folder_structure()
        
        print("🌊 Enhanced ARGO Downloader initialized")
        print(f"📂 Base folder: {self.base_folder}")
        print("=" * 60)

    def create_folder_structure(self):
        """Create the organized folder structure"""
        print("📁 Creating folder structure...")
        
        # Create main folders
        folders_to_create = [
            self.base_folder,
            self.base_folder / "Processed",
            self.base_folder / "Logs",
            self.base_folder / "Scripts",
            self.base_folder / "Models"
        ]
        
        # Create year and month folders
        years = ["2022", "2023", "2024", "2025"]
        months = [f"{i:02d}" for i in range(1, 13)]  # 01 to 12
        
        for year in years:
            year_folder = self.base_folder / year
            folders_to_create.append(year_folder)
            
            for month in months:
                month_folder = year_folder / month
                folders_to_create.append(month_folder)
        
        # Create all folders
        for folder in folders_to_create:
            folder.mkdir(parents=True, exist_ok=True)
        
        print(f"✅ Created folder structure with {len(folders_to_create)} folders")

    def get_download_folder(self, year, month):
        """Get the appropriate download folder for given year/month"""
        return self.base_folder / str(year) / f"{month:02d}"

    def list_netcdf_files(self, url):
        """Scrape directory listing to find all .nc files"""
        print(f"🔍 Scanning: {url}")
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all links ending with .nc
            nc_files = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.endswith('.nc'):
                    file_url = urljoin(url, href)
                    nc_files.append({
                        'url': file_url,
                        'filename': href,
                        'size': self._extract_size_from_row(link)
                    })
            
            print(f"✅ Found {len(nc_files)} NetCDF files")
            return nc_files
            
        except Exception as e:
            print(f"❌ Error scanning directory: {e}")
            return []

    def _extract_size_from_row(self, link):
        """Extract file size from HTML table row"""
        try:
            row = link.find_parent('tr')
            if row:
                cells = row.find_all('td')
                if len(cells) >= 3:
                    size_text = cells[2].get_text().strip()
                    return size_text
        except:
            pass
        return "Unknown"

    def download_single_file(self, file_info, download_folder):
        """Download a single NetCDF file with progress bar"""
        url = file_info['url']
        filename = file_info['filename']
        local_path = download_folder / filename
        
        # Skip if file already exists
        if local_path.exists():
            file_size = local_path.stat().st_size
            print(f"⏭️  Skipping {filename} (already exists, {file_size:,} bytes)")
            return str(local_path)
        
        try:
            response = self.session.get(url, stream=True, timeout=60)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            
            with open(local_path, 'wb') as f:
                with tqdm(
                    total=total_size,
                    unit='B',
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=f"{filename}",
                    ncols=80,
                    leave=False
                ) as pbar:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
            
            print(f"✅ Downloaded {filename} → {download_folder.name}")
            return str(local_path)
            
        except Exception as e:
            print(f"❌ Error downloading {filename}: {e}")
            if local_path.exists():
                local_path.unlink()
            return None

    def download_month_data(self, year, month, max_workers=3):
        """Download all data for a specific year/month"""
        # Construct URL
        base_url = f"https://data-argo.ifremer.fr/geo/indian_ocean/{year}/{month:02d}/"
        
        # Get download folder
        download_folder = self.get_download_folder(year, month)
        
        print(f"\n📅 Downloading {year}/{month:02d} data")
        print(f"🌐 URL: {base_url}")
        print(f"📂 Folder: {download_folder}")
        print("-" * 50)
        
        # Get file list
        files = self.list_netcdf_files(base_url)
        
        if not files:
            print(f"❌ No files found for {year}/{month:02d}")
            return []
        
        start_time = time.time()
        downloaded_files = []
        
        # Download files in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {
                executor.submit(self.download_single_file, file_info, download_folder): file_info 
                for file_info in files
            }
            
            for future in as_completed(future_to_file):
                file_info = future_to_file[future]
                try:
                    result = future.result()
                    if result:
                        downloaded_files.append(result)
                except Exception as e:
                    print(f"❌ Exception downloading {file_info['filename']}: {e}")
        
        # Summary for this month
        duration = time.time() - start_time
        total_size = sum(Path(f).stat().st_size for f in downloaded_files if Path(f).exists())
        
        print(f"\n📊 {year}/{month:02d} Summary:")
        print(f"✅ Downloaded: {len(downloaded_files)}/{len(files)} files")
        print(f"💾 Size: {total_size / (1024*1024):.1f} MB")
        print(f"⏱️  Time: {duration:.1f} seconds")
        
        return downloaded_files

    def download_year_data(self, year, months=None, max_workers=3):
        """Download data for entire year or specific months"""
        if months is None:
            months = list(range(1, 13))  # All months
        
        print(f"\n🗓️ Downloading {year} data for months: {months}")
        print("=" * 60)
        
        all_downloaded = []
        year_start_time = time.time()
        
        for month in months:
            try:
                downloaded = self.download_month_data(year, month, max_workers)
                all_downloaded.extend(downloaded)
                time.sleep(1)  # Brief pause between months
            except Exception as e:
                print(f"❌ Error downloading {year}/{month:02d}: {e}")
        
        # Year summary
        duration = time.time() - year_start_time
        total_size = sum(Path(f).stat().st_size for f in all_downloaded if Path(f).exists())
        
        print(f"\n🎉 {year} YEAR SUMMARY:")
        print(f"✅ Total files downloaded: {len(all_downloaded)}")
        print(f"💾 Total size: {total_size / (1024*1024*1024):.2f} GB")
        print(f"⏱️  Total time: {duration/60:.1f} minutes")
        
        return all_downloaded

    def download_recent_data(self, days=7):
        """Download most recent data (last N days)"""
        print(f"📅 Downloading last {days} days of data...")
        
        # For now, download current month
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        return self.download_month_data(current_year, current_month)

    def list_available_data(self, year):
        """List all available months for a given year"""
        print(f"📋 Checking available data for {year}...")
        
        available_months = []
        for month in range(1, 13):
            url = f"https://data-argo.ifremer.fr/geo/indian_ocean/{year}/{month:02d}/"
            try:
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    files = self.list_netcdf_files(url)
                    if files:
                        available_months.append({
                            'month': month,
                            'files_count': len(files),
                            'url': url
                        })
            except:
                pass
        
        print(f"\n📊 Available data for {year}:")
        for month_info in available_months:
            print(f"  {month_info['month']:2d}/2024: {month_info['files_count']:3d} files")
        
        return available_months


def main():
    """Main function with menu options"""
    print("🌊 ENHANCED ARGO INDIAN OCEAN DATA DOWNLOADER")
    print("📁 Organized folder structure: Dataset/YEAR/MONTH/")
    print("=" * 60)
    
    downloader = EnhancedArgoDownloader()
    
    while True:
        print("""
📋 DOWNLOAD OPTIONS:
1. Download specific month (e.g., 2025/09)
2. Download entire year (e.g., 2024)
3. Download multiple months (e.g., 2024: June-September)
4. Download recent data (last 7 days)
5. List available data for a year
6. Download test data (2025/09 - small dataset)
7. Exit

""")
        
        choice = input("Enter your choice (1-7): ").strip()
        
        if choice == "1":
            year = int(input("Enter year (e.g., 2024): "))
            month = int(input("Enter month (1-12): "))
            downloader.download_month_data(year, month)
            
        elif choice == "2":
            year = int(input("Enter year (e.g., 2024): "))
            downloader.download_year_data(year)
            
        elif choice == "3":
            year = int(input("Enter year (e.g., 2024): "))
            start_month = int(input("Enter start month (1-12): "))
            end_month = int(input("Enter end month (1-12): "))
            months = list(range(start_month, end_month + 1))
            downloader.download_year_data(year, months)
            
        elif choice == "4":
            downloader.download_recent_data()
            
        elif choice == "5":
            year = int(input("Enter year to check (e.g., 2024): "))
            downloader.list_available_data(year)
            
        elif choice == "6":
            print("📊 Downloading test dataset (2025/09)...")
            downloader.download_month_data(2025, 9)
            
        elif choice == "7":
            print("👋 Goodbye!")
            break
            
        else:
            print("❌ Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
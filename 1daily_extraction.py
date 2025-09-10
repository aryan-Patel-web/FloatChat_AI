#!/usr/bin/env python3
"""
Daily ARGO Data Extraction System
Automatically monitors and downloads new ARGO files from September 2025 onwards
Organizes files by date and handles retries, logging, and error management
"""

import os
import re
import requests
from datetime import datetime, timedelta
import time
import logging
from pathlib import Path
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin
import hashlib

class DailyArgoExtractor:
    def __init__(self, base_folder="daily_dataset", check_interval=3600):
        """
        Initialize daily ARGO data extractor
        
        Args:
            base_folder: Base directory for storing daily data
            check_interval: Time in seconds between checks (default: 1 hour)
        """
        self.base_folder = Path(base_folder)
        self.check_interval = check_interval
        self.base_url = "https://data-argo.ifremer.fr/geo/indian_ocean/"
        self.session = requests.Session()
        
        # Setup logging
        self.setup_logging()
        
        # Create folder structure
        self.create_folder_structure()
        
        # Load tracking database
        self.tracking_file = self.base_folder / "file_tracking.json"
        self.file_database = self.load_tracking_database()
        
        self.logger.info("Daily ARGO Extractor initialized")
        self.logger.info(f"Base folder: {self.base_folder}")
        self.logger.info(f"Check interval: {check_interval} seconds")

    def setup_logging(self):
        """Setup comprehensive logging system"""
        log_folder = self.base_folder / "logs"
        log_folder.mkdir(parents=True, exist_ok=True)
        
        # Create formatters
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Setup main logger
        self.logger = logging.getLogger('DailyArgoExtractor')
        self.logger.setLevel(logging.INFO)
        
        # File handler for all logs
        file_handler = logging.FileHandler(
            log_folder / f"daily_extraction_{datetime.now().strftime('%Y%m')}.log"
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Console handler for immediate feedback
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # Separate error log
        error_handler = logging.FileHandler(
            log_folder / f"errors_{datetime.now().strftime('%Y%m')}.log"
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        self.logger.addHandler(error_handler)

    def create_folder_structure(self):
        """Create organized folder structure for daily data"""
        folders_to_create = [
            self.base_folder,
            self.base_folder / "logs",
            self.base_folder / "failed_downloads",
            self.base_folder / "metadata"
        ]
        
        for folder in folders_to_create:
            folder.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("Folder structure created successfully")

    def load_tracking_database(self):
        """Load or create file tracking database"""
        if self.tracking_file.exists():
            try:
                with open(self.tracking_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading tracking database: {e}")
                return {}
        return {}

    def save_tracking_database(self):
        """Save file tracking database"""
        try:
            with open(self.tracking_file, 'w') as f:
                json.dump(self.file_database, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving tracking database: {e}")

    def get_date_folder(self, date_str):
        """
        Get folder path for specific date
        
        Args:
            date_str: Date string in format YYYYMMDD
        
        Returns:
            Path object for date folder
        """
        # Parse date
        try:
            date_obj = datetime.strptime(date_str, '%Y%m%d')
            folder_name = date_obj.strftime('%d%b%Y').lower()  # e.g., "11sep2025"
            return self.base_folder / folder_name
        except ValueError as e:
            self.logger.error(f"Invalid date format {date_str}: {e}")
            return None

    def extract_date_from_filename(self, filename):
        """
        Extract date from ARGO filename
        
        Args:
            filename: ARGO filename like "20250911_prof.nc"
        
        Returns:
            Date string in YYYYMMDD format or None
        """
        match = re.match(r'(\d{8})_prof\.nc', filename)
        if match:
            return match.group(1)
        return None

    def scan_monthly_directory(self, year, month):
        """
        Scan monthly directory for new files
        
        Args:
            year: Year as integer
            month: Month as integer
        
        Returns:
            List of file information dictionaries
        """
        url = f"{self.base_url}{year}/{month:02d}/"
        
        try:
            self.logger.info(f"Scanning directory: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            files_found = []
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.endswith('_prof.nc'):
                    file_url = urljoin(url, href)
                    
                    # Extract file information
                    file_info = {
                        'filename': href,
                        'url': file_url,
                        'date_str': self.extract_date_from_filename(href),
                        'size': self._extract_size_from_row(link),
                        'last_modified': self._extract_modified_date(link)
                    }
                    
                    if file_info['date_str']:
                        files_found.append(file_info)
            
            self.logger.info(f"Found {len(files_found)} files in {year}/{month:02d}")
            return files_found
            
        except Exception as e:
            self.logger.error(f"Error scanning {url}: {e}")
            return []

    def _extract_size_from_row(self, link):
        """Extract file size from HTML table row"""
        try:
            row = link.find_parent('tr')
            if row:
                cells = row.find_all('td')
                if len(cells) >= 3:
                    return cells[2].get_text().strip()
        except:
            pass
        return "Unknown"

    def _extract_modified_date(self, link):
        """Extract last modified date from HTML table row"""
        try:
            row = link.find_parent('tr')
            if row:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    return cells[1].get_text().strip()
        except:
            pass
        return "Unknown"

    def is_new_file(self, file_info):
        """
        Check if file is new or updated
        
        Args:
            file_info: File information dictionary
        
        Returns:
            Boolean indicating if file is new
        """
        filename = file_info['filename']
        current_modified = file_info['last_modified']
        
        if filename not in self.file_database:
            return True
        
        # Check if file was modified
        stored_modified = self.file_database[filename].get('last_modified')
        if stored_modified != current_modified:
            self.logger.info(f"File {filename} was updated (modified: {current_modified})")
            return True
        
        # Check if download was successful
        if not self.file_database[filename].get('download_successful', False):
            self.logger.info(f"Previous download of {filename} failed, retrying")
            return True
        
        return False

    def download_file_with_retry(self, file_info, max_retries=3):
        """
        Download file with automatic retry mechanism
        
        Args:
            file_info: File information dictionary
            max_retries: Maximum number of retry attempts
        
        Returns:
            Boolean indicating success
        """
        filename = file_info['filename']
        url = file_info['url']
        date_str = file_info['date_str']
        
        # Get target folder
        date_folder = self.get_date_folder(date_str)
        if not date_folder:
            return False
        
        date_folder.mkdir(parents=True, exist_ok=True)
        local_path = date_folder / filename
        
        for attempt in range(max_retries + 1):
            try:
                self.logger.info(f"Downloading {filename} (attempt {attempt + 1}/{max_retries + 1})")
                
                response = self.session.get(url, stream=True, timeout=60)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0
                
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                
                # Verify download
                if total_size > 0 and downloaded_size != total_size:
                    raise Exception(f"Download incomplete: {downloaded_size}/{total_size} bytes")
                
                # Calculate file hash for integrity
                file_hash = self._calculate_file_hash(local_path)
                
                # Update tracking database
                self.file_database[filename] = {
                    'date_str': date_str,
                    'download_time': datetime.now().isoformat(),
                    'local_path': str(local_path),
                    'size': file_info['size'],
                    'last_modified': file_info['last_modified'],
                    'download_successful': True,
                    'file_hash': file_hash,
                    'attempts': attempt + 1
                }
                
                self.logger.info(f"Successfully downloaded {filename} to {date_folder.name}")
                return True
                
            except Exception as e:
                self.logger.warning(f"Download attempt {attempt + 1} failed for {filename}: {e}")
                
                # Clean up partial file
                if local_path.exists():
                    local_path.unlink()
                
                if attempt < max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    self.logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    # Mark as failed
                    self.file_database[filename] = {
                        'date_str': date_str,
                        'download_time': datetime.now().isoformat(),
                        'last_modified': file_info['last_modified'],
                        'download_successful': False,
                        'error': str(e),
                        'attempts': attempt + 1
                    }
                    
                    # Move to failed downloads folder
                    failed_folder = self.base_folder / "failed_downloads"
                    failed_info_file = failed_folder / f"{filename}.failed"
                    with open(failed_info_file, 'w') as f:
                        json.dump(file_info, f, indent=2)
                    
                    self.logger.error(f"Failed to download {filename} after {max_retries + 1} attempts")
                    return False

    def _calculate_file_hash(self, file_path):
        """Calculate SHA256 hash of downloaded file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def check_for_new_data(self):
        """
        Check for new data and download if available
        
        Returns:
            Number of new files downloaded
        """
        self.logger.info("Starting check for new data...")
        
        # Get current date and determine which months to check
        current_date = datetime.now()
        months_to_check = []
        
        # Always check current month
        months_to_check.append((current_date.year, current_date.month))
        
        # If it's early in the month, also check previous month
        if current_date.day <= 5:
            prev_month = current_date.replace(day=1) - timedelta(days=1)
            months_to_check.append((prev_month.year, prev_month.month))
        
        new_files_count = 0
        
        for year, month in months_to_check:
            self.logger.info(f"Checking {year}/{month:02d} for new files...")
            
            files = self.scan_monthly_directory(year, month)
            new_files = [f for f in files if self.is_new_file(f)]
            
            if not new_files:
                self.logger.info(f"No new data found in {year}/{month:02d}")
                continue
            
            self.logger.info(f"Found {len(new_files)} new files in {year}/{month:02d}")
            
            for file_info in new_files:
                if self.download_file_with_retry(file_info):
                    new_files_count += 1
                
                # Save progress after each file
                self.save_tracking_database()
                
                # Brief pause between downloads
                time.sleep(1)
        
        self.logger.info(f"Check completed. Downloaded {new_files_count} new files")
        return new_files_count

    def run_continuous_monitoring(self):
        """
        Run continuous monitoring for new files
        """
        self.logger.info("Starting continuous monitoring...")
        self.logger.info(f"Will check for new data every {self.check_interval} seconds")
        
        while True:
            try:
                new_files = self.check_for_new_data()
                
                if new_files > 0:
                    self.logger.info(f"Downloaded {new_files} new files")
                else:
                    self.logger.info("No new data available")
                
                # Wait before next check
                self.logger.info(f"Waiting {self.check_interval} seconds until next check...")
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                self.logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                self.logger.info("Waiting 300 seconds before retry...")
                time.sleep(300)

    def get_status_report(self):
        """Generate status report of downloaded files"""
        total_files = len(self.file_database)
        successful_downloads = sum(1 for f in self.file_database.values() 
                                 if f.get('download_successful', False))
        failed_downloads = total_files - successful_downloads
        
        # Group by date
        files_by_date = {}
        for filename, info in self.file_database.items():
            date_str = info.get('date_str', 'unknown')
            if date_str not in files_by_date:
                files_by_date[date_str] = {'successful': 0, 'failed': 0}
            
            if info.get('download_successful', False):
                files_by_date[date_str]['successful'] += 1
            else:
                files_by_date[date_str]['failed'] += 1
        
        self.logger.info("=" * 50)
        self.logger.info("DAILY EXTRACTION STATUS REPORT")
        self.logger.info("=" * 50)
        self.logger.info(f"Total files tracked: {total_files}")
        self.logger.info(f"Successful downloads: {successful_downloads}")
        self.logger.info(f"Failed downloads: {failed_downloads}")
        self.logger.info("\nFiles by date:")
        
        for date_str in sorted(files_by_date.keys()):
            stats = files_by_date[date_str]
            self.logger.info(f"  {date_str}: {stats['successful']} successful, {stats['failed']} failed")
        
        self.logger.info("=" * 50)


def main():
    """Main function to run the daily extractor"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Daily ARGO Data Extractor')
    parser.add_argument('--folder', default='daily_dataset', 
                       help='Base folder for storing data')
    parser.add_argument('--interval', type=int, default=3600,
                       help='Check interval in seconds (default: 1 hour)')
    parser.add_argument('--once', action='store_true',
                       help='Run once instead of continuous monitoring')
    parser.add_argument('--status', action='store_true',
                       help='Show status report and exit')
    
    args = parser.parse_args()
    
    # Initialize extractor
    extractor = DailyArgoExtractor(
        base_folder=args.folder,
        check_interval=args.interval
    )
    
    if args.status:
        extractor.get_status_report()
    elif args.once:
        extractor.check_for_new_data()
    else:
        extractor.run_continuous_monitoring()


if __name__ == "__main__":
    main()
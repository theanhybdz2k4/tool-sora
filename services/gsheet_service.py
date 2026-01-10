"""
Google Sheets Service
Handles reading data from Google Sheets URL (public sheets only)
"""
import csv
import re
import urllib.request
from io import StringIO
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class JobRow:
    """Represents a single job from the spreadsheet"""
    stt: str = ""
    prompt: str = ""
    image: str = ""
    savename: str = ""
    path: str = ""
    aspect_ratio: str = "16:9"
    duration: str = "5s"
    model: str = ""
    presets: str = ""
    status: str = ""
    row_index: int = 0
    
    def to_dict(self) -> dict:
        return {
            'stt': self.stt,
            'prompt': self.prompt,
            'image': self.image,
            'savename': self.savename,
            'path': self.path,
            'aspect_ratio': self.aspect_ratio,
            'duration': self.duration,
            'model': self.model,
            'presets': self.presets,
            'status': self.status,
            'row_index': self.row_index,
        }


class GoogleSheetsService:
    """Service for reading data from Google Sheets"""
    
    def __init__(self, log_callback=None):
        self.log = log_callback or print
        
    def extract_sheet_id(self, url: str) -> Optional[str]:
        """Extract sheet ID from Google Sheets URL"""
        # Match patterns like:
        # https://docs.google.com/spreadsheets/d/SHEET_ID/edit
        # https://docs.google.com/spreadsheets/d/SHEET_ID/edit#gid=0
        match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
        if match:
            return match.group(1)
        return None
        
    def fetch_as_csv(self, sheet_id: str, gid: str = "0") -> Optional[str]:
        """Fetch sheet data as CSV (requires public access)"""
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        
        try:
            req = urllib.request.Request(
                csv_url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.read().decode('utf-8')
        except urllib.error.HTTPError as e:
            if e.code == 404:
                self.log("❌ Sheet không tồn tại hoặc không được chia sẻ công khai")
            else:
                self.log(f"❌ HTTP Error {e.code}: {e.reason}")
            return None
        except Exception as e:
            self.log(f"❌ Không thể tải sheet: {e}")
            return None
            
    def parse_csv(self, csv_data: str) -> List[JobRow]:
        """Parse CSV data into JobRow objects"""
        jobs = []
        
        reader = csv.DictReader(StringIO(csv_data))
        
        for row_idx, row in enumerate(reader, start=2):  # Start from row 2 (after header)
            job = JobRow(row_index=row_idx)
            
            # Map columns (case-insensitive)
            for key, value in row.items():
                if not key:
                    continue
                key_lower = key.strip().lower().replace(' ', '_')
                value = str(value).strip() if value else ""
                
                if key_lower == 'stt':
                    job.stt = value
                elif key_lower == 'prompt':
                    job.prompt = value
                elif key_lower == 'image':
                    job.image = value
                elif key_lower in ('savename', 'save_name'):
                    job.savename = value
                elif key_lower == 'path':
                    job.path = value
                elif key_lower in ('aspect_ratio', 'aspectratio', 'ratio'):
                    job.aspect_ratio = value or "16:9"
                elif key_lower == 'duration':
                    job.duration = value or "5s"
                elif key_lower == 'model':
                    job.model = value
                elif key_lower == 'presets':
                    job.presets = value
                elif key_lower == 'status':
                    job.status = value
                    
            # Only add if prompt exists
            if job.prompt:
                jobs.append(job)
                
        return jobs
        
    def load_from_url(self, url: str, skip_completed: bool = True) -> List[JobRow]:
        """Load jobs from Google Sheets URL"""
        sheet_id = self.extract_sheet_id(url)
        if not sheet_id:
            self.log("❌ URL không hợp lệ. Vui lòng dùng link Google Sheets.")
            return []
            
        self.log(f"📋 Sheet ID: {sheet_id}")
        
        # Extract gid if present
        gid = "0"
        gid_match = re.search(r'[#&]gid=(\d+)', url)
        if gid_match:
            gid = gid_match.group(1)
            
        csv_data = self.fetch_as_csv(sheet_id, gid)
        if not csv_data:
            return []
            
        jobs = self.parse_csv(csv_data)
        self.log(f"📊 Loaded {len(jobs)} rows từ sheet")
        
        if skip_completed:
            completed_statuses = {'done', 'completed', 'success', 'finished', 'hoàn thành'}
            original_count = len(jobs)
            jobs = [j for j in jobs if j.status.lower() not in completed_statuses]
            skipped = original_count - len(jobs)
            if skipped > 0:
                self.log(f"⏭️ Skipped {skipped} completed rows")
                
        return jobs


def test_service():
    """Test the service with a public sheet"""
    service = GoogleSheetsService()
    
    # Test URL parsing
    test_url = "https://docs.google.com/spreadsheets/d/1u6zkmPAmba4oQn5bFPFKrl7ZZlF7XT2sBUYA8e6RI6E/edit#gid=0"
    sheet_id = service.extract_sheet_id(test_url)
    print(f"Sheet ID: {sheet_id}")
    
    # Test loading
    jobs = service.load_from_url(test_url)
    for job in jobs:
        print(f"Job: {job.stt} - {job.prompt[:50]}...")
        

if __name__ == "__main__":
    test_service()

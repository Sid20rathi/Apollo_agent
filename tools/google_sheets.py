import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from config import config

class GoogleSheetsClient:
    def __init__(self):
        # define the scope
        self.scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
        
        self.creds_file = config.GOOGLE_APPLICATION_CREDENTIALS
        self.sheet_name = config.SPREADSHEET_NAME
        
        self.client = None
        self.sheet = None
        
        self._authenticate()

    def _authenticate(self):
        if not os.path.exists(self.creds_file):
            print(f"Warning: Google Credentials file not found at {self.creds_file}.")
            # We don't raise an exception to allow the graph to run without sheets for testing
            return
            
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(self.creds_file, self.scope)
            self.client = gspread.authorize(creds)
            # Find a workbook by name
            workbook = self.client.open(self.sheet_name)
            self.sheet = workbook.sheet1 # Get first sheet
            
            # Ensure headers exist
            headers = self.sheet.row_values(1)
            expected_headers = ["Date", "Company", "Contact Name", "Title", "Email", "Status", "Notes"]
            if not headers:
                self.sheet.append_row(expected_headers)
                
        except Exception as e:
            print(f"Error connecting to Google Sheets: {str(e)}")

    def get_todays_outreach_count(self):
        """
        Count how many emails were sent today to respect API and spam limits.
        """
        if not self.sheet: return 0
        
        try:
            records = self.sheet.get_all_records()
            today_str = datetime.now().strftime("%Y-%m-%d")
            
            count = sum(1 for row in records if str(row.get('Date', '')).startswith(today_str))
            return count
        except Exception as e:
            print(f"Error reading from Google Sheets: {str(e)}")
            return 0
            
    def log_outreach(self, company, name, title, email, status, notes=""):
        """
        Log a new outreach attempt to the spreadsheet.
        """
        if not self.sheet:
            print(f"Would log to sheet: {company} - {email} ({status})")
            return
            
        try:
            today_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            row = [today_str, company, name, title, email, status, notes]
            self.sheet.append_row(row)
        except Exception as e:
            print(f"Error appending to Google Sheets: {str(e)}")

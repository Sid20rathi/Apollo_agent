import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from config import config
import json

class GoogleSheetsClient:
    def __init__(self):
        # define the scope
        self.scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
        
        self.creds_file = config.GOOGLE_APPLICATION_CREDENTIALS
        self.sheet_name = config.SPREADSHEET_NAME
        
        self.client = None
        self.outreach_sheet = None
        self.discovery_sheet = None
        
        self._authenticate()

    def _authenticate(self):
        if not os.path.exists(self.creds_file):
            print(f"Warning: Google Credentials file not found at {self.creds_file}.")
            return
            
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(self.creds_file, self.scope)
            self.client = gspread.authorize(creds)
            workbook = self.client.open(self.sheet_name)
            
            # Outreach Sheet (Historical tracker)
            self.outreach_sheet = workbook.sheet1 
            headers = self.outreach_sheet.row_values(1)
            expected_headers = ["Date", "Company", "Contact Name", "Title", "Email", "Status", "Notes"]
            if not headers:
                self.outreach_sheet.append_row(expected_headers)
                
            # Discovery Sheet (Pipeline state tracking)
            try:
                self.discovery_sheet = workbook.worksheet("Discovery")
            except gspread.exceptions.WorksheetNotFound:
                print("Creating 'Discovery' worksheet...")
                self.discovery_sheet = workbook.add_worksheet(title="Discovery", rows="1000", cols="8")
                self.discovery_sheet.append_row(["Date", "Company", "Domain", "Status", "Emails", "Intel", "Source"])
                
        except Exception as e:
            print(f"Error connecting to Google Sheets: {str(e)}")

    def get_todays_outreach_count(self):
        if not self.outreach_sheet: return 0
        try:
            records = self.outreach_sheet.get_all_records()
            today_str = datetime.now().strftime("%Y-%m-%d")
            count = sum(1 for row in records if str(row.get('Date', '')).startswith(today_str))
            return count
        except Exception as e:
            print(f"Error reading from Google Sheets: {str(e)}")
            return 0
            
    def get_known_domains(self):
        """Returns lowercase set of all known domains to ensure true uniqueness."""
        if not self.discovery_sheet: return set()
        try:
            records = self.discovery_sheet.get_all_records()
            return {str(row.get('Domain', '')).strip().lower() for row in records if row.get('Domain')}
        except Exception as e:
            print(f"Error fetching known domains: {str(e)}")
            return set()
            
    def append_new_discovery(self, company_name, domain, source=""):
        """Adds a newly discovered company with status 'New'."""
        if not self.discovery_sheet: return
        try:
            today_str = datetime.now().strftime("%Y-%m-%d")
            row = [today_str, company_name, domain, "New", "", "", source]
            self.discovery_sheet.append_row(row)
        except Exception as e:
            print(f"Error appending to Discovery sheet: {str(e)}")
            
    def get_companies_by_status(self, status, limit=None):
        """Fetches companies from Discovery sheet that match the given status."""
        if not self.discovery_sheet: return []
        try:
            records = self.discovery_sheet.get_all_records()
            matches = []
            for idx, row in enumerate(records):
                if str(row.get('Status', '')).strip().lower() == status.lower():
                    row['__row_index'] = idx + 2 # +2 because row 1 is header, list is 0-indexed
                    matches.append(row)
            if limit:
                return matches[:limit]
            return matches
        except Exception as e:
            print(f"Error fetching {status} companies: {str(e)}")
            return []

    def update_discovery_status(self, row_index, new_status, emails_str="", intel_str=""):
        """Updates a specific row in the Discovery sheet to move it to the next pipeline stage."""
        if not self.discovery_sheet: return
        try:
            # Column mapping: 1=Date, 2=Company, 3=Domain, 4=Status, 5=Emails, 6=Intel
            self.discovery_sheet.update_cell(row_index, 4, new_status)
            if emails_str:
                self.discovery_sheet.update_cell(row_index, 5, emails_str)
            if intel_str:
                self.discovery_sheet.update_cell(row_index, 6, intel_str)
        except Exception as e:
            print(f"Error updating Discovery row {row_index}: {str(e)}")

    def log_outreach(self, company, name, title, email, status, notes=""):
        if not self.outreach_sheet:
            print(f"Would log to sheet: {company} - {email} ({status})")
            return
        try:
            today_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            row = [today_str, company, name, title, email, status, notes]
            self.outreach_sheet.append_row(row)
        except Exception as e:
            print(f"Error appending to Google Sheets: {str(e)}")

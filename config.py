import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    APOLLO_API_KEY = os.getenv("APOLLO_API_KEY")
    RESEND_API_KEY = os.getenv("RESEND_API_KEY")
    APIFY_KEY = os.getenv("APIFY_KEY")
    
    LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
    LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "apollo-marketing-agent")
    LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "credentials.json")
    SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "apollo_outreach_tracker")
    
    DAILY_EMAIL_LIMIT = int(os.getenv("DAILY_EMAIL_LIMIT", "30")) # Increased to 30 to process more distinct companies
    SENDER_EMAIL = os.getenv("SENDER_EMAIL")
    COMPANY_NAME = os.getenv("COMPANY_NAME", "Your Company Name")
    EXPECTED_OUTREACH_TOPIC = os.getenv("EXPECTED_OUTREACH_TOPIC", "Influencer Marketing Campaign Partnerships")

    @classmethod
    def validate(cls):
        missing = []
        if not cls.GEMINI_API_KEY: missing.append("GEMINI_API_KEY")
        if not cls.TAVILY_API_KEY: missing.append("TAVILY_API_KEY")
        if not cls.APOLLO_API_KEY: missing.append("APOLLO_API_KEY")
        if not cls.RESEND_API_KEY: missing.append("RESEND_API_KEY")
        if not cls.APIFY_KEY: missing.append("APIFY_KEY")
        if not cls.SENDER_EMAIL: missing.append("SENDER_EMAIL")
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
            
config = Config()

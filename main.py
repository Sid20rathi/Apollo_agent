import time
import schedule
from graph import build_graph
from config import config

def run_daily_outreach():
    """
    Executes the LangGraph sequence.
    """
    print("\n=============================================")
    print(f"Starting Daily Outreach for: {config.COMPANY_NAME}")
    print("=============================================\n")
    
    app = build_graph()
    
    # Initial state
    initial_state = {
        "companies_to_target": [],
        "found_contacts": [],
        "sent_emails": [],
        "errors": []
    }
    
    # Run the graph
    app.invoke(initial_state)
    
    print("\n=============================================")
    print(f"Daily Outreach Complete.")
    print("=============================================\n")

def main():
    # Make sure env is set
    config.validate()
    
    print("Starting Apollo Marketing Agent System...")
    
    # For testing, you can uncomment this to run it immediately once
    run_daily_outreach()
    
    # Schedule the job every day at 10:00 AM
    schedule.every().day.at("10:00").do(run_daily_outreach)
    
    print("Job scheduled. Waiting...")
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()

from typing import TypedDict, List, Dict, Any, Annotated
from typing_extensions import NotRequired
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
import json
import concurrent.futures

from config import config
from tools.apollo_client import ApolloClient
from tools.resend_client import ResendClient
from tools.google_sheets import GoogleSheetsClient
from tools.search_client import SearchClient

# --- STATE DEFINITION ---
class OutreachState(TypedDict):
    """
    Defines the state passed between the LangGraph nodes.
    """
    companies_to_target: List[Dict[str, str]]
    found_contacts: List[Dict[str, Any]]
    sent_emails: List[Dict[str, str]]
    errors: List[str]

# --- NODE 1: RESEARCH MARKET ---
def research_market(state: OutreachState) -> OutreachState:
    """
    Agent 1: Research the market for newly funded or stable Indian startups
    suitable for influencer marketing.
    """
    print("--- \033[94mAGENT 1: Researching Market\033[0m ---")
    
 
    sheets_client = GoogleSheetsClient()
    todays_count = sheets_client.get_todays_outreach_count()
    if todays_count >= config.DAILY_EMAIL_LIMIT:
        print(f"Daily limit of {config.DAILY_EMAIL_LIMIT} reached. Aborting pipeline.")
        return state

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=config.GEMINI_API_KEY, temperature=0.3)
    search_client = SearchClient()
    tools = search_client.get_tools()
    tavily_tool = tools[0]
    apify_tool = tools[1] if len(tools) > 1 else None
    
   
    system_prompt = """You are a top-tier B2B market researcher focusing on the Indian market.
Your goal is to identify a minimum of 20 to 30 newly funded startups or stable companies in India that are highly likely to benefit from an 'Influencer Marketing Campaign'.
Consumer brands, D2C, e-commerce, EdTech, and Fintech are good targets.

You MUST return your findings as a strict JSON array of objects.
Each object must have exactly two keys: "name" (the company name) and "domain" (the company's website domain, e.g., "example.com", no https://).
Do NOT include markdown formatting like ```json.
"""
    print("Running parallel web searches (Tavily + Apify)...")
    def run_tavily():
        return tavily_tool.invoke("20 Newly funded Indian startups D2C e-commerce edtech latest news")

    def run_apify():
        if apify_tool:
            return apify_tool.invoke("latest top 30 Indian startups 2025-2026 funding list")
        return ""
        
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_tavily = executor.submit(run_tavily)
        future_apify = executor.submit(run_apify)
        search_results = f"TAVILY RESULTS:\\n{future_tavily.result()}\\n\\nAPIFY RESULTS:\\n{future_apify.result()}"
        
    user_msg = f"Use this extensive search context to find 20-30 target companies:\\n{search_results}\\n\\nProvide the JSON list of minimum 20 companies and domains."
    
    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_msg)])
    
    try:
    
        text = response.content.replace("```json", "").replace("```", "").strip()
        companies = json.loads(text)
        
        # Filter out companies that have already been contacted
        contacted_list = sheets_client.get_contacted_companies()
        new_companies = []
        for c in companies:
            name_lower = str(c.get('name', '')).strip().lower()
            if name_lower not in contacted_list:
                new_companies.append(c)
            else:
                print(f"Skipping {c.get('name')} - already contacted previously.")
        
        print(f"Found {len(new_companies)} new companies (filtered out {len(companies) - len(new_companies)} duplicates).")
        return {"companies_to_target": new_companies}
    except Exception as e:
        print(f"Error parsing Gemini response: {e}")
        return {"errors": ["Failed to extract company list from Gemini"]}

# --- NODE 2: FIND CONTACTS ---
def find_contacts(state: OutreachState) -> OutreachState:
    """
    Agent 2: Iterates over the targeted companies and uses Apollo to find email IDs
    of relevant decision-makers.
    """
    print("--- \033[94mAGENT 2: Finding Contacts\033[0m ---")
    companies = state.get("companies_to_target", [])
    if not companies:
        print("No companies found to target.")
        return state
        
    apollo = ApolloClient()
    all_contacts = []
    
   
    for company in companies:
        domain = company.get("domain")
        company_name = company.get("name")
        if not domain: continue
        
        print(f"Searching Apollo for contacts at {company_name} ({domain})...")
        contacts = apollo.search_contacts(domain)
        
        # Attach company name context if apollo missed it
        for c in contacts:
            if not c.get("company"): c["company"] = company_name
            
        all_contacts.extend(contacts)
        
    print(f"Found a total of {len(all_contacts)} contacts with emails.")
    return {"found_contacts": all_contacts}

# --- NODE 3: DRAFT & SEND EMAILS ---
def draft_and_send_emails(state: OutreachState) -> OutreachState:
    """
    Agent 3: Drafts personalized emails and sends them on behalf of the company.
    Logs successful attempts to Google Sheets.
    """
    print("--- \033[94mAGENT 3: Drafting & Sending Emails\033[0m ---")
    contacts = state.get("found_contacts", [])
    if not contacts:
        return state
        
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=config.GEMINI_API_KEY, temperature=0.7)
    resend_client = ResendClient()
    sheets_client = GoogleSheetsClient()
    
    sent_logs = []
    
    todays_count = sheets_client.get_todays_outreach_count()
    remaining_quota = config.DAILY_EMAIL_LIMIT - todays_count
    
    for contact in contacts[:remaining_quota]:
        name = contact.get("name", "there")
        title = contact.get("title", "Leader")
        company = contact.get("company", "your company")
        email = contact.get("email")
        
        if not email: continue
        
        print(f"Sending email to {name} ({title}) at {company}...")
        
        # Hardcoded email content from test_single_email.py as requested
        html_body = f"""
    <p>Hi {name},</p>
    <p>We have worked with brands like Tata, Canon, Nykaa, Pluxee, and many more.<br> - Drove 50M+ reach across 500+ campaigns.<br>We don't pitch influencers. We pitch the brand fits. <br></p>


    <p> open to a quick call? {config.CAL_URL}<p>

    <p>Best,<br>Nidhi<br>{config.COMPANY_NAME} | {config.COMPANY_WEBSITE}</p>
        """
        
        text_body = f"""Hi {name},

- worked with brands like Tata, Canon, Nykaa, Pluxee, and many more.
- drove 50M+ reach across 500+ campaigns
- we don't pitch influencers. we pitch the brand fits.

open to a quick call? {config.CAL_URL}

Best,
Nidhi
The Latest Buzz | {config.COMPANY_WEBSITE}"""
        
        subject = "This will take you 30 seconds to read"
        
        # Send Email
        success, info = resend_client.send_pitch_email(email, subject, html_body, text_body)
        
        status = "Sent" if success else "Failed"
        sheets_client.log_outreach(company, name, title, email, status, str(info))
        
        if success:
            sent_logs.append({"email": email, "company": company})
            
    print(f"Process complete. Drafted & Sent {len(sent_logs)} emails.")
    return {"sent_emails": sent_logs}

# --- GRAPH COMPILATION ---
def build_graph() -> StateGraph:
    """
    Compiles and returns the LangGraph application.
    """
    workflow = StateGraph(OutreachState)
    
    workflow.add_node("research_market", research_market)
    workflow.add_node("find_contacts", find_contacts)
    workflow.add_node("draft_and_send_emails", draft_and_send_emails)
    
    workflow.add_edge(START, "research_market")
    workflow.add_edge("research_market", "find_contacts")
    workflow.add_edge("find_contacts", "draft_and_send_emails")
    workflow.add_edge("draft_and_send_emails", END)
    
    return workflow.compile()

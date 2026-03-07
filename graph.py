from typing import TypedDict, List, Dict, Any, Annotated
from typing_extensions import NotRequired
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
import json

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
    
    # Check sheet to see if we've hit our daily limit early
    sheets_client = GoogleSheetsClient()
    todays_count = sheets_client.get_todays_outreach_count()
    if todays_count >= config.DAILY_EMAIL_LIMIT:
        print(f"Daily limit of {config.DAILY_EMAIL_LIMIT} reached. Aborting pipeline.")
        return state

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=config.GEMINI_API_KEY, temperature=0.3)
    search_client = SearchClient()
    search_tool = search_client.get_tools()[0]
    
    # We use LLM to decide what to search for, we'll do a simple prompt for the prototype
    system_prompt = """You are a top-tier B2B market researcher focusing on the Indian market.
Your goal is to identify 3-5 newly funded startups or stable companies in India that are highly likely to benefit from an 'Influencer Marketing Campaign'.
Consumer brands, D2C, e-commerce, EdTech, and Fintech are good targets.

You MUST return your findings as a strict JSON array of objects.
Each object must have exactly two keys: "name" (the company name) and "domain" (the company's website domain, e.g., "example.com", no https://).
Do NOT include markdown formatting like ```json.
"""
    
    # In a full LangGraph we'd use a ToolNode for the search, but since Tavily gives great direct
    # results, we can just feed a query to it and then context into Gemini.
    search_results = search_tool.invoke("Newly funded Indian startups D2C e-commerce edtech latest news")
    
    user_msg = f"Use this search context to find 3-5 target companies:\n{search_results}\n\nProvide the JSON list of companies and domains."
    
    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_msg)])
    
    try:
        # Clean any accidental markdown formatting
        text = response.content.replace("```json", "").replace("```", "").strip()
        companies = json.loads(text)
        print(f"Found {len(companies)} companies: {[c.get('name') for c in companies]}")
        return {"companies_to_target": companies}
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
    
    # To respect limits, we'll just process until we have enough
    # For daily limits of 20, 3-5 companies with 2 contacts each is enough.
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
        
        print(f"Drafting email for {name} ({title}) at {company}...")
        
        system_prompt = f"""You are a professional B2B business development representative for "{config.COMPANY_NAME}".
Your goal is to write a highly personalized, concise cold email pitching our {config.EXPECTED_OUTREACH_TOPIC}.
The target recipient is {name}, whose title is {title} at the company "{company}".

Guidelines:
- Keep it under 150 words.
- Be polite, professional, yet casual enough for the Indian startup ecosystem.
- Start directly (no "I hope this email finds you well").
- Provide a clear call to action (e.g., a 10 min chat).
- Do NOT include subject line in the body. Output ONLY the raw HTML body (e.g. using <p>, <br>).
"""
        response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content="Draft the email body now.")])
        html_body = response.content
        
        subject = f"Influencer Marketing for {company} / {config.COMPANY_NAME}"
        
        # Send Email
        # success, info = resend_client.send_pitch_email(email, subject, html_body)
        print(f"Skipping actual email send for testing. Email would be sent to {email}")
        success, info = True, "Test_Skipped_Send"
        
        status = "Test (Not Sent)" if success else "Failed"
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

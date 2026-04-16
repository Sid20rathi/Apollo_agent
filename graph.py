from typing import TypedDict, List, Dict, Any, Annotated
from typing_extensions import NotRequired
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
import json
import concurrent.futures
from datetime import datetime
import random

from config import config
from tools.apollo_client import ApolloClient
from tools.resend_client import ResendClient
from tools.google_sheets import GoogleSheetsClient
from tools.search_client import SearchClient

# --- STATE DEFINITION ---
class OutreachState(TypedDict):
    """
    State is now primarily stored in Google Sheets.
    This dict just passes along error tracking and basic metrics.
    """
    errors: List[str]
    emails_sent_count: int
    sent_emails: List[Dict[str, str]]
    query: NotRequired[str]

# --- HELPER DYNAMIC QUERIES ---
def get_dynamic_queries(month_name, year):
    cities = ["Bangalore", "Mumbai", "Delhi NCR", "Pune", "Hyderabad", "Chennai"]
    niches = ["SaaS", "D2C", "EdTech", "Fintech", "HealthTech", "AI", "E-commerce apps"]
    
    city = random.choice(cities)
    niche = random.choice(niches)
    
    tavily_queries = [
        f"new {niche} startups founded in {city} {year}",
        f"top list of newly funded {niche} companies in India {month_name} {year}",
        f"bootstrapped {niche} startups in India hiring {month_name} {year}"
    ]
    
    apify_queries = [
        f"latest {niche} startups {city} {year} funding",
        f"emerging B2B {niche} companies India {year}"
    ]
    return tavily_queries, apify_queries, city, niche

# --- NODE 1: RESEARCH MARKET ---
def research_market(state: OutreachState) -> OutreachState:
    """
    Agent 1: Discovery Stage.
    Finds new companies using rotating queries, dedups against Google Sheets, and saves 'New' leads.
    """
    print("--- \033[94mSTAGE 1: Discovery (Finding New Companies)\033[0m ---")
    
    sheets_client = GoogleSheetsClient()
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=config.GEMINI_API_KEY, temperature=0.5)
    search_client = SearchClient()
    tools = search_client.get_tools()
    
    tavily_tool = tools[0]
    apify_tool = tools[1] if len(tools) > 1 else None
    
    current_date = datetime.now()
    month_name = current_date.strftime("%B")
    year = current_date.year

    query = state.get("query", "").strip()
    
    if query:
        print(f"Targeting custom query: {query}")
        tavily_queries = [query]
        apify_queries = [query]
        niche = "target"
        system_prompt = f"""You are a top-tier B2B market researcher inside an automated pipeline.
Your goal is to identify 20 to 30 unique companies matching this search intent: '{query}'.

You MUST return your findings as a strict JSON array of objects.
Each object must have exactly three keys: 
1. "name" (the company name) 
2. "domain" (the company's website domain, e.g., "example.com", no https://)
3. "summary" (A 1-sentence description of what they do)

Do NOT include markdown formatting like ```json.
"""
    else:
        tavily_queries, apify_queries, city, niche = get_dynamic_queries(month_name, year)
        print(f"Targeting: {niche} startups in {city} / India...")

        system_prompt = f"""You are a top-tier B2B market researcher inside an automated pipeline.
Your goal is to identify 20 to 30 unique newly funded or emerging {niche} startups in India (specifically around {city} or pan-India).

You MUST return your findings as a strict JSON array of objects.
Each object must have exactly three keys: 
1. "name" (the company name) 
2. "domain" (the company's website domain, e.g., "example.com", no https://)
3. "summary" (A 1-sentence description of what they do)

Do NOT include markdown formatting like ```json.
"""

    def run_tavily(query):
        try:
            return tavily_tool.invoke(query)
        except Exception as e:
            print(f"Tavily error: {e}")
            return ""

    def run_apify(query):
        if apify_tool:
            try:
                return apify_tool.invoke(query)
            except Exception as e:
                print(f"Apify error: {e}")
                pass
        return ""
        
    with concurrent.futures.ThreadPoolExecutor() as executor:
        tavily_futures = [executor.submit(run_tavily, q) for q in tavily_queries]
        apify_futures = [executor.submit(run_apify, q) for q in apify_queries]
        
        search_results_blocks = []
        for i, f in enumerate(tavily_futures):
            res = f.result()
            if res: search_results_blocks.append(f"TAVILY QUERY '{tavily_queries[i]}' RESULTS:\n{res}")
        for i, f in enumerate(apify_futures):
            res = f.result()
            if res: search_results_blocks.append(f"APIFY QUERY '{apify_queries[i]}' RESULTS:\n{res}")
            
        search_results = "\n\n".join(search_results_blocks)
        
    user_msg = f"Use this extensive search context containing fresh {niche} and startups to find 20-30 target companies:\n{search_results}\n\nProvide the JSON list of companies, domains, and summary."
    
    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_msg)])
    
    try:
        text = response.content.replace("```json", "").replace("```", "").strip()
        companies = json.loads(text)
        
        # De-duplication Stage
        known_domains = sheets_client.get_known_domains()
        
        new_count = 0
        for c in companies:
            domain = str(c.get('domain', '')).strip().lower()
            name = str(c.get('name', '')).strip()
            # Basic domain cleanup
            if domain.startswith("www."):
                domain = domain[4:]
            
            if domain and domain not in known_domains:
                source_label = f"Search: {query[:15]}..." if query else f"Tavily/Apify {month_name} {year}"
                sheets_client.append_new_discovery(name, domain, source=source_label)
                known_domains.add(domain) # Prevent duplicates in same run
                new_count += 1
            else:
                print(f"Skipping {name} ({domain}) - already known or invalid domain.")
        
        print(f"Added {new_count} purely new unique companies to Discovery pipeline.")
        return state
    except Exception as e:
        print(f"Error parsing Gemini response or saving to sheet: {e}")
        return {"errors": ["Failed to extract company list from Gemini"]}

# --- NODE 2: ENRICHMENT ---
def find_contacts(state: OutreachState) -> OutreachState:
    """
    Agent 2: Enrichment Stage.
    Pulls 'New' companies from Discovery sheet, finds contacts via Apollo, and updates them to 'Enriched'.
    """
    print("--- \033[94mSTAGE 2: Enrichment (Finding Contacts & Intel)\033[0m ---")
    sheets_client = GoogleSheetsClient()
    
    new_companies = sheets_client.get_companies_by_status("New", limit=30)
    
    if not new_companies:
        print("No 'New' companies found in pipeline to enrich.")
        return state
        
    apollo = ApolloClient()
    
    enriched_count = 0
    for company in new_companies:
        domain = company.get("Domain", "")
        company_name = company.get("Company", "")
        row_index = company.get("__row_index")
        
        if not domain: continue
        
        print(f"Searching Apollo for contacts at {company_name} ({domain})...")
        contacts = apollo.search_contacts(domain)
        
        if contacts:
            # Format emails JSON
            emails_str = json.dumps([{
                "name": c.get("name", ""),
                "title": c.get("title", ""),
                "email": c.get("email", "")
            } for c in contacts])
            
            # Here we could call an LLM to build a personalized intel string, but keeping it simple for now
            intel_str = f"Found {len(contacts)} contacts."
            
            sheets_client.update_discovery_status(row_index, "Enriched", emails_str, intel_str)
            enriched_count += 1
        else:
            # If no contacts found, we might want to flag it as "Discarded" or "NoContacts" so we don't retry endlessly
            sheets_client.update_discovery_status(row_index, "No Contacts")
            
    print(f"Successfully enriched {enriched_count} companies with contacts.")
    return state

# --- NODE 3: DRAFT & SEND EMAILS ---
def draft_and_send_emails(state: OutreachState) -> OutreachState:
    """
    Agent 3: Outreach Stage.
    Pulls 'Enriched' companies, drafts personalized emails, sends them, and updates to 'Contacted'.
    """
    print("--- \033[94mSTAGE 3: Outreach (Drafting & Sending Emails)\033[0m ---")
    
    sheets_client = GoogleSheetsClient()
    todays_count = sheets_client.get_todays_outreach_count()
    remaining_quota = config.DAILY_EMAIL_LIMIT - todays_count
    
    if remaining_quota <= 0:
        print(f"Daily limit of {config.DAILY_EMAIL_LIMIT} reached. Aborting outreach.")
        return state
        
    enriched_companies = sheets_client.get_companies_by_status("Enriched", limit=remaining_quota)
    if not enriched_companies:
        print("No 'Enriched' companies found in pipeline. Need more discovery/enrichment.")
        return state
        
    resend_client = ResendClient()
    
    sent_count = 0
    for company in enriched_companies:
        emails_str = company.get("Emails", "")
        company_name = company.get("Company", "")
        row_index = company.get("__row_index")
        
        if not emails_str: continue
        
        try:
            contacts = json.loads(emails_str)
        except json.JSONDecodeError:
            continue
            
        if not contacts: continue
        
        # Pick the best contact (first one returned by Apollo is usually best scored)
        best_contact = contacts[0]
        name = best_contact.get("name", "there")
        title = best_contact.get("title", "Leader")
        email = best_contact.get("email")
        
        if not email: continue
        
        print(f"Sending email to {name} ({title}) at {company_name}...")
        
        # Hardcoded email content
        html_body = f"""
    <p>Hi {name.split(' ')[0]},</p>
    <p>We have worked with brands like Tata, Canon, Nykaa, Pluxee, and many more.<br> - Drove 50M+ reach across 500+ campaigns.<br>We don't pitch influencers. We pitch the brand fits. <br></p>
    <p> open to a quick call? {config.CAL_URL}<p>
    <p>Best,<br>Nidhi<br>{config.COMPANY_NAME} | {config.COMPANY_WEBSITE}</p>
        """
        
        text_body = f"""Hi {name.split(' ')[0]},

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
        sheets_client.log_outreach(company_name, name, title, email, status, str(info))
        
        if success:
            sheets_client.update_discovery_status(row_index, "Contacted")
            sent_count += 1
            if "sent_emails" not in state:
                state["sent_emails"] = []
            state["sent_emails"].append({
                "company": company_name,
                "email": email
            })
        else:
            sheets_client.update_discovery_status(row_index, "Failed Outreach")
            
    print(f"Process complete. Drafted & Sent {sent_count} emails today.")
    state["emails_sent_count"] = state.get("emails_sent_count", 0) + sent_count
    return state

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


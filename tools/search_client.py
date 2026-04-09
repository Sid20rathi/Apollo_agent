from langchain_tavily import TavilySearch
from langchain_core.tools import tool
from apify_client import ApifyClient
from config import config

@tool("apify_search")
def apify_search(query: str) -> str:
    """Search Google via Apify for comprehensive business results."""
    if not config.APIFY_KEY:
        return "Apify is not configured."
    client = ApifyClient(config.APIFY_KEY)
    
    # We use Google Search Scraper. Depending on the query length and limits, 15-30 results are enough.
    run = client.actor("apify/google-search-scraper").call(run_input={
        "queries": query,
        "maxPagesPerQuery": 1,
        "resultsPerPage": 30
    })
    
    items = client.dataset(run["defaultDatasetId"]).list_items().items
    results = []
    
    # The output is grouped by queries, so we loop over the items
    for item in items:
        for organic in item.get('organicResults', []):
            results.append(f"Title: {organic.get('title')}\\nURL: {organic.get('url')}\\nDescription: {organic.get('description')}")
            
    return "\\n\\n".join(results)

class SearchClient:
    def __init__(self):
        # We will expose a LangChain Tool for the Gemini agent to use seamlessly
        self.tavily_tool = TavilySearch(max_results=20)
        
    def get_tools(self):
        tools = [self.tavily_tool]
        if config.APIFY_KEY:
            tools.append(apify_search)
        return tools

from langchain_community.tools.tavily_search import TavilySearchResults
from config import config

class SearchClient:
    def __init__(self):
        # We will expose a LangChain Tool for the Gemini agent to use seamlessly
        self.tavily_tool = TavilySearchResults(max_results=10)
        
    def get_tools(self):
        return [self.tavily_tool]

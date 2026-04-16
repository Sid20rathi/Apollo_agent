from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from graph import build_graph
from config import config
import logging
from pydantic import BaseModel
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Validate config on startup
config.validate()

app = FastAPI(title="Apollo Agent API")

# CORS middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Endpoint for Render to check if the app is awake."""
    return {"status": "ok", "service": "apollo-agent", "message": "Backend is live"}

class TriggerRequest(BaseModel):
    query: Optional[str] = None

@app.post("/trigger")
async def trigger_outreach(req: TriggerRequest = None):
    """Manual trigger for the Apollo Outreach Agent."""
    logger.info("Outreach trigger received via API.")
    
    try:
        # Re-build the graph to ensure fresh state
        workflow = build_graph()
        
        # Initial state (State managed mostly in Google Sheets now)
        initial_state = {
            "errors": [],
            "emails_sent_count": 0,
            "sent_emails": [],
            "query": req.query if req and req.query else ""
        }
        
        # Run the graph (this is synchronous in graph.py, but we run it inside the async handler)
        # Note: Render may timeout if this takes > 30s.
        final_state = workflow.invoke(initial_state)
        
        errors = final_state.get("errors", [])
        sent_emails = final_state.get("sent_emails", [])
        emails_sent_count = final_state.get("emails_sent_count", 0)
        
        if errors:
            logger.error(f"Graph execution errors: {errors}")
            
        return {
            "status": "success",
            "message": "Pipeline execution complete. Check Google Sheets for logs and updates.",
            "errors": errors,
            "emails_sent_count": emails_sent_count,
            "sent_emails": sent_emails
        }
    except Exception as e:
        logger.exception("Failed to execute outreach graph")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from graph import build_graph
from config import config
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
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

@app.post("/trigger")
async def trigger_outreach():
    """Manual trigger for the Apollo Outreach Agent."""
    logger.info("Outreach trigger received via API.")
    
    try:
        # Re-build the graph to ensure fresh state
        workflow = build_graph()
        
        # Initial state
        initial_state = {
            "companies_to_target": [],
            "found_contacts": [],
            "sent_emails": [],
            "errors": []
        }
        
        # Run the graph (this is synchronous in graph.py, but we run it inside the async handler)
        # Note: Render may timeout if this takes > 30s.
        final_state = workflow.invoke(initial_state)
        
        sent_emails = final_state.get("sent_emails", [])
        errors = final_state.get("errors", [])
        
        if errors:
            logger.error(f"Graph execution errors: {errors}")
            
        return {
            "status": "success",
            "emails_sent_count": len(sent_emails),
            "sent_emails": sent_emails,
            "errors": errors
        }
    except Exception as e:
        logger.exception("Failed to execute outreach graph")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

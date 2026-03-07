import os
from langsmith import Client
from langsmith.evaluation import evaluate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from config import config

# Ensure we have our environment variables
config.validate()

client = Client()

def create_dataset():
    """
    Create a sample dataset in LangSmith to test the email generation Agent.
    """
    dataset_name = "Apollo_Outreach_Emails"
    
    # Create dataset if it doesn't exist
    if not client.has_dataset(dataset_name=dataset_name):
        dataset = client.create_dataset(
            dataset_name=dataset_name, 
            description="Dataset for evaluating our outbound marketing emails generating by Gemini."
        )
        print(f"Created dataset: {dataset.id}")
        
        # Add examples
        examples = [
            (
                {"name": "Rahul Sharma", "title": "CMO", "company": "Swiggy"},
                {"expected_format": "Concise, B2B friendly, mentioning influencer marketing"}
            ),
            (
                {"name": "Priya Patel", "title": "Founder", "company": "Nykaa"},
                {"expected_format": "Concise, B2B friendly, mentioning influencer marketing"}
            )
        ]
        
        for inputs, outputs in examples:
            client.create_example(inputs=inputs, outputs=outputs, dataset_id=dataset.id)
            
    return dataset_name

def generate_email(inputs: dict) -> dict:
    """
    This simulates the logic inside Agent 3 for the evaluator.
    """
    name = inputs.get("name")
    title = inputs.get("title")
    company = inputs.get("company")
    
    system_prompt = f'''You are a professional B2B business development representative for "{config.COMPANY_NAME}".
Your goal is to write a highly personalized, concise cold email pitching our {config.EXPECTED_OUTREACH_TOPIC}.
The target recipient is {name}, whose title is {title} at the company "{company}".

Guidelines:
- Keep it under 150 words.
- Be polite, professional, yet casual enough for the Indian startup ecosystem.
- Start directly (no "I hope this email finds you well").
- Provide a clear call to action.
'''
    # The actual graph/agent logic uses Gemini, so we simulate it here:
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=config.GEMINI_API_KEY, temperature=0.7)
    
    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content="Draft the email body now.")])
    
    return {"email_body": response.content}


def evaluate_conciseness(run, example) -> dict:
    """Evaluates if the email is concise."""
    eval_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=config.GEMINI_API_KEY, temperature=0.0)
    email_text = run.outputs.get("email_body", "")
    
    prompt = f"Score the following email from 0 to 1 based on conciseness (is it straight to the point without fluff?). Output ONLY the number (0 or 1).\n\nEmail:\n{email_text}"
    score_str = eval_llm.invoke(prompt).content.strip()
    try:
        score = float(score_str)
    except:
        score = 0.0
    return {"key": "conciseness", "score": score}

def evaluate_professionalism(run, example) -> dict:
    """Evaluates if the email connects well in a B2B setting."""
    eval_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=config.GEMINI_API_KEY, temperature=0.0)
    email_text = run.outputs.get("email_body", "")
    
    prompt = f"Score the following email from 0 to 1 based on professionalism for Indian B2B outreach (professional but casual). Output ONLY the number (0 or 1).\n\nEmail:\n{email_text}"
    score_str = eval_llm.invoke(prompt).content.strip()
    try:
        score = float(score_str)
    except:
        score = 0.0
    return {"key": "professionalism", "score": score}

def run_evaluation():
    print("Setting up LangSmith Evaluation...")
    dataset_name = create_dataset()
    
    print(f"Running evaluation on dataset '{dataset_name}'...")
    
    evaluation = evaluate(
        generate_email,
        data=dataset_name, 
        evaluators=[evaluate_conciseness, evaluate_professionalism],
        experiment_prefix="Gemini-Email-Gen",
        metadata={"model": "gemini-2.5-flash", "type": "outreach_agents"}
    )
    
    print("\nEvaluation successfully logged to LangSmith!")

if __name__ == "__main__":
    run_evaluation()

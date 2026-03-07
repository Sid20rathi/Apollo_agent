import os
from langsmith import Client
from langsmith.evaluation import evaluate, LangChainStringEvaluator
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
                {"expected_format": "Concise, B2B friendly, mentioning influencer marketing, < 150 words"}
            ),
            (
                {"name": "Priya Patel", "title": "Founder", "company": "Nykaa"},
                {"expected_format": "Concise, B2B friendly, mentioning influencer marketing, < 150 words"}
            )
        ]
        
        for inputs, outputs in examples:
            client.create_example(inputs=inputs, outputs=outputs, dataset_id=dataset.id)
            
    return dataset_name

def generate_email(inputs: dict) -> dict:
    """
    This simulates the logic inside Agent 3 for the evaluator.
    """
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", google_api_key=config.GEMINI_API_KEY, temperature=0.7)
    
    name = inputs.get("name")
    title = inputs.get("title")
    company = inputs.get("company")
    
    system_prompt = f"""You are a professional B2B business development representative for "{config.COMPANY_NAME}".
Your goal is to write a highly personalized, concise cold email pitching our {config.EXPECTED_OUTREACH_TOPIC}.
The target recipient is {name}, whose title is {title} at the company "{company}".
    # The actual graph/agent logic uses Gemini, so we simulate it here:
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=config.GEMINI_API_KEY, temperature=0.7)
    
    responses = []
    
    for row in data:
        prompt = (
            f"Draft a short pitch email for {row['company_name']}.\n"
            f"Contact: {row['contact_name']}, {row['contact_title']}.\n"
            f"Company Context: {row['company_context']}"
        )
        # Using LLM directly to simulate generation logic
        msg = llm.invoke(prompt)
        responses.append({
            "inputs": row,
            "outputs": {"email_draft": msg.content}
        })
        
    return responses

def evaluate_relevance(run, example) -> dict:
    eval_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=config.GEMINI_API_KEY, temperature=0.0)

    # A custom criteria to act as our "judge"
    conciseness_evaluator = LangChainStringEvaluator(
        "criteria",
        config={
            "criteria": "conciseness",
            "llm": eval_llm
        }
    )
    
    professionalism_evaluator = LangChainStringEvaluator(
        "criteria",
        config={
            "criteria": "professionalism",
            "llm": eval_llm
        }
    )
    
    # Run the evaluations
    return {
        "conciseness": conciseness_evaluator.evaluate_strings(
            prediction=run.outputs["email_draft"],
            input=run.inputs["company_context"]
        ),
        "professionalism": professionalism_evaluator.evaluate_strings(
            prediction=run.outputs["email_draft"],
            input=run.inputs["company_context"]
        )
    }

def run_evaluation():
    print("Setting up LangSmith Evaluation...")
    dataset_name = create_dataset()
    
    print(f"Running evaluation on dataset '{dataset_name}'...")
    
    evaluation = evaluate(
        simulate_agent_pipeline,
        data=dataset_name, 
        evaluators=[evaluate_relevance],
        experiment_prefix="Gemini-Email-Gen",
        metadata={"model": "gemini-2.5-flash", "type": "outreach_agents"}
    )
    
    print("\nEvaluation successfully logged to LangSmith!")

if __name__ == "__main__":
    run_evaluation()

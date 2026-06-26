import os
import json
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="QueueStorm Investigator API")

# Initialize LLM Client (Using Google Gemini API as example)
# Replace with your preferred LLM SDK if needed
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None
MODEL_ID = "gemini-2.5-flash" # Fast, good for reasoning and structured output

# --- 1. PYDANTIC SCHEMAS (Input) ---
class Transaction(BaseModel):
    transaction_id: str
    amount: float
    date: str
    status: str
    details: Optional[str] = ""

class TicketRequest(BaseModel):
    ticket_id: str
    complaint: str
    transactions: List[Transaction] = Field(..., min_length=2, max_length=5)

# --- 2. ENUMS FOR STRICT VALIDATION ---
class EvidenceVerdict(str, Enum):
    consistent = "consistent"
    inconsistent = "inconsistent"
    insufficient_data = "insufficient_data"

class CaseType(str, Enum):
    wrong_transfer = "wrong_transfer"
    payment_failed = "payment_failed"
    refund_request = "refund_request"
    duplicate_payment = "duplicate_payment"
    merchant_settlement_delay = "merchant_settlement_delay"
    agent_cash_in_issue = "agent_cash_in_issue"
    phishing_or_social_engineering = "phishing_or_social_engineering"
    other = "other"

class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

class DepartmentRouting(str, Enum):
    customer_support = "customer_support"
    dispute_resolution = "dispute_resolution"
    payments_ops = "payments_ops"
    merchant_operations = "merchant_operations"
    agent_operations = "agent_operations"
    fraud_risk = "fraud_risk"

# --- 3. PYDANTIC SCHEMAS (Output) ---
class AnalysisResponse(BaseModel):
    ticket_id: str
    relevant_transaction_id: Optional[str] = None
    evidence_verdict: EvidenceVerdict
    case_type: CaseType
    severity: Severity
    department_routing: DepartmentRouting
    agent_summary: str
    recommended_next_action: str
    customer_reply: str
    human_review_required: bool
    confidence: Optional[float] = 0.95
    reason_codes: Optional[List[str]] = []

# --- 4. PROMPT & SAFETY LOGIC ---
SYSTEM_PROMPT = """
You are an AI-powered support copilot for a digital finance platform.
Your job is to read a customer complaint (in English, Bangla, or Banglish) and cross-reference it with the provided recent transactions.

INVESTIGATION TASK:
1. Find the matching transaction based on amounts, dates, or context.
2. Determine if the system data supports the complaint (consistent), contradicts it (inconsistent), or if there is insufficient data.

CRITICAL SAFETY RULES (NON-NEGOTIABLE):
1. NEVER ask for a PIN, OTP, password, or CVV in the customer_reply.
2. NEVER confirm a definitive refund or reversal. Always use hedged language like "any eligible amount will be returned through official channels after verification."
3. NEVER direct the customer to a third party. Only direct them to official platform channels.

Return ONLY a valid JSON object matching the requested schema.
Ensure `human_review_required` is true for disputes, high-value, suspicious, or ambiguous cases.
"""

# --- 5. ENDPOINTS ---

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "ok"}

@app.post("/analyze-ticket", response_model=AnalysisResponse)
async def analyze_ticket(payload: TicketRequest):
    if not client:
        raise HTTPException(status_code=500, detail="LLM Client not configured properly.")
        
    try:
        # Prepare context for the prompt
        transactions_text = json.dumps([t.model_dump() for t in payload.transactions], indent=2)
        user_prompt = f"""
        Ticket ID: {payload.ticket_id}
        Complaint: "{payload.complaint}"
        Recent Transactions:
        {transactions_text}
        
        Analyze the ticket and generate the required JSON response. Make sure to echo back the exact Ticket ID.
        """

        # Call LLM with Structured Output enforcement
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=[SYSTEM_PROMPT, user_prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AnalysisResponse,
                temperature=0.1 # Keep temperature low for analytical consistency
            ),
        )

        # Parse and validate the response against Pydantic model
        result_json = json.loads(response.text)
        return AnalysisResponse(**result_json)

    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="LLM failed to return valid JSON.")
    except Exception as e:
        # Never crash, gracefully return a 500 error on unexpected failures
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
# QueueStorm Investigator

An AI-powered support copilot REST API service for a digital finance platform. It cross-references multilingual customer complaints (English, Bangla, Banglish) with transaction histories to generate automated, safe, and structured responses.

## Tech Stack
* **Framework:** Python / FastAPI (for speed and robust error handling)
* **Validation:** Pydantic (ensures strict enum compliance and JSON schemas)
* **LLM Integration:** Google GenAI SDK (Gemini 2.5 Flash for high-speed reasoning)
* **Containerization:** Docker

## MODELS & AI Strategy
We selected **Gemini 2.5 Flash** because it supports native JSON schema adherence (`response_schema`), meaning we never have to worry about broken JSON outputs. The system prompt is engineered to handle Bangla and Banglish through zero-shot cross-lingual reasoning.

### Safety Logic Implementations
Safety is enforced via explicit negative constraints injected directly into the system prompt:
1. **No Credentials:** Explicit instruction to never ask for PIN/OTP/CVV.
2. **No Definitive Refunds:** Required to use hedged phrasing ("eligible amount will be returned...").
3. **No Third Parties:** Explicit instruction forcing routing only to official platform channels.
*Temperature is set to 0.1* to eliminate hallucination risks on safety guardrails.

## Running Locally

1. Clone the repo.
2. Copy `.env.example` to `.env` and add your API key.
3. Install dependencies: `pip install -r requirements.txt`
4. Run: `uvicorn main:app --reload`
5. Test: Send a POST request to `http://localhost:8000/analyze-ticket`.

## Running with Docker
```bash
docker build -t queuestorm-investigator .
docker run -p 8000:8000 --env-file .env queuestorm-investigator
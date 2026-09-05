import os
from dotenv import load_dotenv
from groq import Groq
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

# Load environment variables
load_dotenv()
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

app = FastAPI()

# Enable CORS so the frontend can call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load CSVs ONCE when the server starts
gateway_df = pd.read_csv("data/gateway_logs.csv")
bank_df = pd.read_csv("data/bank_logs.csv")
ledger_df = pd.read_csv("data/ledger_logs.csv")


def check_gateway(txn_id: str):
    row = gateway_df[gateway_df["txn_id"] == txn_id]
    if row.empty:
        return {"status": "not_found", "amount": None, "fee": None}
    row = row.iloc[0]
    return {
    "status": row["gateway_status"],
    "amount": int(row["amount"]),
    "fee": int(row["fee"]),
    "timestamp": row["timestamp"],
}

def check_bank(txn_id: str):
    row = bank_df[bank_df["txn_id"] == txn_id]
    if row.empty:
        return {"status": "not_found", "utr": None, "hold_reason": None}
    row = row.iloc[0]
    hold_reason = row["hold_reason"] if pd.notna(row["hold_reason"]) else None
    return {"status": row["bank_status"], "utr": row["utr"], "hold_reason": hold_reason}


def check_ledger(txn_id: str, expected_amount):
    row = ledger_df[ledger_df["txn_id"] == txn_id]
    if row.empty:
        return {"status": "missing", "credited_amount": None, "expected_amount": expected_amount}
    credited = int(row.iloc[0]["credited_amount"])
    if expected_amount is not None and credited != expected_amount:
        return {"status": "mismatch", "credited_amount": credited, "expected_amount": expected_amount}
    return {"status": "credited", "credited_amount": credited, "expected_amount": expected_amount}


def determine_overall_status(gateway, bank, ledger):
    if gateway["status"] == "not_found" or bank["status"] == "not_found" or ledger["status"] == "missing":
        return "REQUIRES_HUMAN_REVIEW"
    if bank["status"] == "held":
        return "DELAY"
    if ledger["status"] == "mismatch":
        return "MISMATCH"
    return "SUCCESS"


def get_explanation(trace_data: dict) -> str:
    # Hard fallback BEFORE calling the LLM
    if trace_data["overall_status"] == "REQUIRES_HUMAN_REVIEW":
        return "This transaction has missing or inconsistent records across systems and requires manual review by a support agent."

    prompt = f"""You are a fintech support assistant. Given this transaction trace data: {trace_data}

In exactly 2 sentences, explain in plain English what happened to this transaction and why, for a non-technical support agent. Do not invent information not present in the data."""

    try:
        response = groq_client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            timeout=5,
        )
        return response.choices[0].message.content
    except Exception as e:
        print("GROQ ERROR:", repr(e))   # <-- add this line
    return "Unable to generate an AI explanation right now. Please review the trace data manually."

@app.get("/trace/{txn_id}")
def trace_transaction(txn_id: str, date: str | None = None):
    gateway = check_gateway(txn_id)

    if date and (
    gateway["status"] == "not_found"
    or not str(gateway["timestamp"]).startswith(date)
):
     return {"error": "Transaction not found"}

    expected_amount = None
    if gateway["amount"] is not None and gateway["fee"] is not None:
        expected_amount = gateway["amount"] - gateway["fee"]

    bank = check_bank(txn_id)
    ledger = check_ledger(txn_id, expected_amount)

    overall_status = determine_overall_status(gateway, bank, ledger)

    result = {
        "txn_id": txn_id,
        "overall_status": overall_status,
        "steps": {
            "gateway": gateway,
            "bank": bank,
            "ledger": ledger,
        },
        "requires_human_review": overall_status == "REQUIRES_HUMAN_REVIEW",
    }

    result["explanation"] = get_explanation(result)
    return result
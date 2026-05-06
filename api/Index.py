import os
import json
import requests
from fastapi import FastAPI, Request, Response
from supabase import create_client, Client
import google.generativeai as genai

app = FastAPI()

# Wachtwoord voor Meta
VERIFY_TOKEN = "orren_secret_token_2024"

# Laad variabelen (met fallback om crash te voorkomen)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "")

# Initialiseer alleen als de sleutels er zijn
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini = genai.GenerativeModel('gemini-1.5-flash')

@app.get("/api/webhook")
async def verify(request: Request):
    params = request.query_params
    # Log de inkomende aanvraag voor debuggen in Vercel
    print(f"Inkomende verificatie: {params}")
    if params.get("hub.verify_token") == VERIFY_TOKEN:
        return Response(content=params.get("hub.challenge"), status_code=200)
    return Response(content="Invalid token", status_code=403)

@app.post("/api/webhook")
async def webhook(request: Request):
    # De rest van je logica blijft hier...
    return Response(content="OK", status_code=200)

@app.get("/")
async def root():
    return {"status": "Server is online", "supabase_configured": bool(SUPABASE_URL)}

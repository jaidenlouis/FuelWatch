import os
import json
import requests
from fastapi import FastAPI, Request, Response
from supabase import create_client, Client
import google.generativeai as genai

app = FastAPI()

# 1. Configuratie laden vanuit Vercel Environment Variables
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
VERIFY_TOKEN = "orren_secret_token_2024"

# 2. Initialisatie van de diensten
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)
gemini = genai.GenerativeModel('gemini-1.5-flash')

@app.get("/")
async def root():
    return {"status": "online", "message": "BrandstofBot is actief"}

@app.get("/api/webhook")
async def verify(request: Request):
    params = request.query_params
    if params.get("hub.verify_token") == VERIFY_TOKEN:
        return Response(content=params.get("hub.challenge"), status_code=200)
    return Response(content="Wachtwoord onjuist", status_code=403)

@app.post("/api/webhook")
async def webhook(request: Request):
    data = await request.json()
    
    try:
        # Check of het bericht van WhatsApp komt
        if "messages" in data["entry"][0]["changes"][0]["value"]:
            message = data["entry"][0]["changes"][0]["value"]["messages"][0]
            number = message["from"]
            
            # Gebruiker check/aanmaken in Supabase
            user_check = supabase.table("users").select("*").eq("whatsapp_number", number).execute()
            if not user_check.data:
                supabase.table("users").insert({"whatsapp_number": number, "user_type": "public"}).execute()

            # OPTIE A: Locatie ontvangen
            if message["type"] == "location":
                lat = message["location"]["latitude"]
                lon = message["location"]["longitude"]
                
                supabase.table("stations").insert({
                    "name": f"Station-{number[-4:]}",
                    "location": f"POINT({lon} {lat})"
                }).execute()
                
                send_whatsapp(number, "📍 Locatie opgeslagen! Stuur nu een foto van het prijzenbord.")

            # OPTIE B: Foto ontvangen (AI Analyse)
            elif message["type"] == "image":
                image_id = message["image"]["id"]
                
                # Haal foto URL op bij Meta
                media_info = requests.get(
                    f"https://graph.facebook.com/v18.0/{image_id}",
                    headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
                ).json()
                
                # Download de foto
                img_bytes = requests.get(
                    media_info["url"],
                    headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
                ).content

                # Gemini AI analyse
                prompt = "Extract fuel prices (Petrol/Super and Diesel) from this image. Return ONLY JSON: {\"petrol\": float, \"diesel\": float, \"currency\": \"GHS\"}"
                response = gemini.generate_content([prompt, {"mime_type": "image/jpeg", "data": img_bytes}])
                
                try:
                    clean_json = response.text.replace('```json', '').replace('```', '').strip()
                    prices = json.loads(clean_json)
                    msg = f"✅ Gelezen prijzen:\n⛽ Petrol: {prices.get('petrol')} GHS\n🚜 Diesel: {prices.get('diesel')} GHS\n\nKlopt dit?"
                    send_whatsapp(number, msg)
                except:
                    send_whatsapp(number, "❌ Kon de prijzen niet goed lezen. Is de foto scherp?")

            # OPTIE C: Gewoon tekstbericht
            else:
                send_whatsapp(number, "Hoi! Stuur me een locatie of een foto van een brandstofstation om te beginnen. ⛽")

    except Exception as e:
        print(f"Fout: {e}")

    return Response(content="OK", status_code=200)

def send_whatsapp(to, text):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    requests.post(url, json=payload, headers=headers)

# Belangrijk voor Vercel deployment
handler = app

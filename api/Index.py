import os
import json
import requests
from fastapi import FastAPI, Request, Response
from supabase import create_client, Client
import google.generativeai as genai

app = FastAPI()

# Omgevingsvariabelen (In te stellen in Vercel)
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
VERIFY_TOKEN = "orren_secret_token_2024" # Bedenk zelf een token voor Meta

# Initialisatie
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)
gemini = genai.GenerativeModel('gemini-1.5-flash')

@app.get("/")
async def root():
    return {"status": "Fuel Repo Bot is online"}

# 1. Webhook Verificatie voor Meta
@app.get("/webhook")
async def verify(request: Request):
    params = request.query_params
    if params.get("hub.verify_token") == VERIFY_TOKEN:
        return Response(content=params.get("hub.challenge"), status_code=200)
    return Response(content="Invalid token", status_code=403)

# 2. Hoofd Webhook (Ontvangt berichten)
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    
    try:
        if "messages" in data["entry"][0]["changes"][0]["value"]:
            message = data["entry"][0]["changes"][0]["value"]["messages"][0]
            number = message["from"]
            
            # Stap A: Check of gebruiker bestaat
            user_data = supabase.table("users").select("*").eq("whatsapp_number", number).execute()
            if not user_data.data:
                supabase.table("users").insert({"whatsapp_number": number, "user_type": "public"}).execute()

            # Stap B: Verwerk Locatie (Station aanmaken/vinden)
            if message["type"] == "location":
                lat = message["location"]["latitude"]
                lon = message["location"]["longitude"]
                
                # Zoek dichtstbijzijnde station (simpele versie: we maken er gewoon een aan)
                new_station = supabase.table("stations").insert({
                    "name": f"Station {number[-4:]}",
                    "location": f"POINT({lon} {lat})"
                }).execute()
                
                send_whatsapp(number, "Locatie opgeslagen! Stuur nu een foto van het prijzenbord.")

            # Stap C: Verwerk Foto met Gemini
            elif message["type"] == "image":
                image_id = message["image"]["id"]
                media_url_info = requests.get(
                    f"https://graph.facebook.com/v18.0/{image_id}",
                    headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
                ).json()
                
                image_bytes = requests.get(
                    media_url_info["url"],
                    headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
                ).content

                # Gemini OCR Prompt
                prompt = """
                Extract fuel prices (Petrol/Super and Diesel) from this image.
                Format as JSON: {"petrol": float, "diesel": float, "currency": "GHS"}.
                If prices aren't clear, return {"error": "low_quality"}.
                """
                response = gemini.generate_content([prompt, {"mime_type": "image/jpeg", "data": image_bytes}])
                
                try:
                    prices = json.loads(response.text.replace('```json', '').replace('```', ''))
                    if "error" not in prices:
                        # Hier zou je de station_id ophalen uit de sessie, voor nu even hardcoded:
                        msg = f"Gevonden: Petrol {prices.get('petrol')} GHS, Diesel {prices.get('diesel')} GHS. Dank voor je bijdrage!"
                        send_whatsapp(number, msg)
                    else:
                        send_whatsapp(number, "Ik kon de prijzen niet goed lezen. Probeer een scherpere foto.")
                except:
                    send_whatsapp(number, "Er ging iets mis bij het parsen van de foto.")

    except Exception as e:
        print(f"Error: {e}")

    return Response(content="OK", status_code=200)

def send_whatsapp(to, text):
    requests.post(
        f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages",
        headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
        json={
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text}
        }
    )
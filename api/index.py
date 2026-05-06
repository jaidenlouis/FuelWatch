import os, json, requests, asyncio
from fastapi import FastAPI, Request, Response, BackgroundTasks
from supabase import create_client, Client
import google.generativeai as genai

app = FastAPI()

# Configuratie
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = "orren_secret_token_2024"

# Clients
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini = genai.GenerativeModel('gemini-1.5-flash')

# --- HULPFUNCTIES ---

def send_whatsapp(to, text):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}}
    requests.post(url, json=payload, headers=headers)

async def process_image_task(number, image_id, user_weight):
    """Asynchrone verwerking om Meta retries te voorkomen"""
    try:
        # 1. Media URL ophalen & downloaden
        media_info = requests.get(f"https://graph.facebook.com/v18.0/{image_id}", 
                                  headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"}).json()
        img_bytes = requests.get(media_info["url"], headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"}).content

        # 2. Goedkope Pre-filter (Stap 2.1 uit Gap Analysis)
        pre_filter_prompt = "Is this an image of a gas station price board? Answer only Yes or No."
        check = gemini.generate_content([pre_filter_prompt, {"mime_type": "image/jpeg", "data": img_bytes}])
        
        if "yes" not in check.text.lower():
            send_whatsapp(number, "❌ Dit lijkt niet op een prijzenbord. Probeer het opnieuw.")
            return

        # 3. Full Extraction & Validation (Stap 3.3)
        prompt = "Extract fuel prices. Return ONLY JSON: {\"petrol\": float, \"diesel\": float, \"station_name\": string}"
        response = gemini.generate_content([prompt, {"mime_type": "image/jpeg", "data": img_bytes}])
        
        # JSON opschonen en parsen
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        prices = json.loads(clean_json)

        # 4. Opslaan met Confidence Weight (Stap 3.2)
        # Hier zou je normaal gesproken ook een PostGIS query doen voor het dichtstbijzijnde station
        supabase.table("price_submissions").insert({
            "whatsapp_number": number,
            "petrol": prices.get('petrol'),
            "diesel": prices.get('diesel'),
            "confidence_weight": user_weight,
            "status": "pending_validation"
        }).execute()

        msg = f"✅ Prijzen ontvangen voor {prices.get('station_name', 'station')}:\n⛽ Petrol: {prices.get('petrol')}\n🚜 Diesel: {prices.get('diesel')}\nBedankt voor je bijdrage!"
        send_whatsapp(number, msg)

    except Exception as e:
        print(f"Async Error: {e}")

# --- API ROUTES ---

@app.get("/api/webhook")
async def verify(request: Request):
    params = request.query_params
    if params.get("hub.verify_token") == VERIFY_TOKEN:
        return Response(content=params.get("hub.challenge"), status_code=200)
    return Response(content="Error", status_code=403)

@app.post("/api/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    
    # DIRECTE 200 OK naar Meta om loops te voorkomen (Stap 1.1)
    if "messages" not in data["entry"][0]["changes"][0]["value"]:
        return Response(content="OK", status_code=200)

    message = data["entry"][0]["changes"][0]["value"]["messages"][0]
    number = message["from"]

    # Gebruiker info ophalen (User Type Weighting - Stap 3.2)
    user_res = supabase.table("users").select("user_type").eq("whatsapp_number", number).execute()
    if not user_res.data:
        user_type = "public"
        weight = 0.4
        supabase.table("users").insert({"whatsapp_number": number, "user_type": user_type}).execute()
    else:
        user_type = user_res.data[0]["user_type"]
        weights = {"owner": 1.0, "partner": 0.85, "driver": 0.6, "public": 0.4}
        weight = weights.get(user_type, 0.4)

    # Verwerking naar achtergrond verplaatsen
    if message["type"] == "image":
        background_tasks.add_task(process_image_task, number, message["image"]["id"], weight)
        send_whatsapp(number, "📸 Foto ontvangen! Ik ben de prijzen aan het uitlezen... een momentje.")
    
    elif message["type"] == "location":
        # Stap 3.1: Hier moet de PostGIS query komen ipv simpelweg inserten
        send_whatsapp(number, "📍 Locatie ontvangen. Stuur nu de foto van de prijzen.")
    
    else:
        send_whatsapp(number, "Stuur een locatie of foto van een station. Tekst-invoer (bij slecht bereik) komt binnenkort! ⛽")

    return Response(content="OK", status_code=200)

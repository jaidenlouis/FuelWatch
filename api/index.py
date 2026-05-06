import os, json, requests, asyncio
from fastapi import FastAPI, Request, Response, BackgroundTasks
from supabase import create_client, Client
import google.generativeai as genai

app = FastAPI()

# Config
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini = genai.GenerativeModel('gemini-1.5-flash')

def send_whatsapp(to, text):
    url = f"https://graph.facebook.com/v18.0/{os.getenv('PHONE_NUMBER_ID')}/messages"
    headers = {"Authorization": f"Bearer {os.getenv('WHATSAPP_TOKEN')}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}}
    requests.post(url, json=payload, headers=headers)

async def process_image_task(number, image_id, user_weight):
    try:
        media_info = requests.get(f"https://graph.facebook.com/v18.0/{image_id}", 
                                  headers={"Authorization": f"Bearer {os.getenv('WHATSAPP_TOKEN')}"}).json()
        img_bytes = requests.get(media_info["url"], headers={"Authorization": f"Bearer {os.getenv('WHATSAPP_TOKEN')}"}).content
        
        # Stap 2.1: Pre-filter
        check = gemini.generate_content(["Is this a fuel price board? Answer only Yes or No.", {"mime_type": "image/jpeg", "data": img_bytes}])
        if "yes" not in check.text.lower():
            send_whatsapp(number, "❌ Dit lijkt niet op een prijzenbord.")
            return

        # Stap 3.3: Extractie
        prompt = "Extract fuel prices. Return ONLY JSON: {\"petrol\": float, \"diesel\": float, \"station_name\": string}"
        response = gemini.generate_content([prompt, {"mime_type": "image/jpeg", "data": img_bytes}])
        prices = json.loads(response.text.replace('```json', '').replace('```', '').strip())

        # Stap 3.2: Opslaan
        supabase.table("price_submissions").insert({
            "whatsapp_number": number, "petrol": prices.get('petrol'), 
            "diesel": prices.get('diesel'), "confidence_weight": user_weight
        }).execute()

        send_whatsapp(number, f"✅ Gelezen: {prices.get('station_name')}\n⛽ Petrol: {prices.get('petrol')}\n🚜 Diesel: {prices.get('diesel')}")
    except Exception as e:
        print(f"Fout: {e}")

@app.get("/api/webhook")
async def verify(request: Request):
    params = request.query_params
    if params.get("hub.verify_token") == "orren_secret_token_2024":
        return Response(content=params.get("hub.challenge"), status_code=200)
    return Response(status_code=403)

@app.post("/api/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    if "messages" not in data["entry"][0]["changes"][0]["value"]:
        return Response(content="OK", status_code=200)

    message = data["entry"][0]["changes"][0]["value"]["messages"][0]
    number = message["from"]

    # Haal gewicht op
    user_res = supabase.table("users").select("user_type").eq("whatsapp_number", number).execute()
    user_type = user_res.data[0]["user_type"] if user_res.data else "public"
    weight = {"owner": 1.0, "partner": 0.85, "driver": 0.6, "public": 0.4}.get(user_type, 0.4)

    if message["type"] == "location":
        lat, lon = message["location"]["latitude"], message["location"]["longitude"]
        # Stap 3.1: PostGIS check
        rpc_res = supabase.rpc("find_nearest_station", {"user_lat": lat, "user_lon": lon}).execute()
        
        if rpc_res.data:
            msg = f"📍 Gekoppeld aan: {rpc_res.data[0]['name']}. Stuur nu de foto!"
        else:
            supabase.table("stations").insert({"name": f"Station-{number[-4:]}", "location": f"POINT({lon} {lat})"}).execute()
            msg = "📍 Nieuwe locatie opgeslagen. Stuur nu de foto!"
        send_whatsapp(number, msg)

    elif message["type"] == "image":
        background_tasks.add_task(process_image_task, number, message["image"]["id"], weight)
        send_whatsapp(number, "📸 Ontvangen! Ik analyseer de foto...")

    return Response(content="OK", status_code=200)

handler = app

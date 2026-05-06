import os
import requests
from fastapi import FastAPI, Request, Response

app = FastAPI()

# Deze variabelen haalt hij nu uit jouw Vercel instellingen
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = "orren_secret_token_2024"

@app.get("/api/webhook")
async def verify(request: Request):
    params = request.query_params
    if params.get("hub.verify_token") == VERIFY_TOKEN:
        return Response(content=params.get("hub.challenge"), status_code=200)
    return Response(content="Wachtwoord onjuist", status_code=403)

@app.post("/api/webhook")
async def message(request: Request):
    data = await request.json()
    
    try:
        # Check of het een echt bericht is
        if "messages" in data["entry"][0]["changes"][0]["value"]:
            message = data["entry"][0]["changes"][0]["value"]["messages"][0]
            user_number = message["from"]
            
            # De bot stuurt een simpel tekstberichtje terug als test
            send_whatsapp(user_number, "Hey! Ik heb je bericht ontvangenGeweldig! Als. De brandstofbot is bijna klaar voor gebruik! ⛽")
            
    except Exception as e:
        print(f"Foutje de `WHATSAPP_TOKEN` en `PHONE_NUMBER_ID` in Vercel staan, is de infrastructuur klaar om berichten te versturen.

We gaan nu de **"echte" code** in `api/index.py` zetten. Deze versie doet het volgende:
1.  **Ont bij ontvangen: {e}")

    return Response(content="OK", status_code=200)

def send_whatsapp(to, textvangt** je WhatsApp-bericht.
2.  **Identificeert** je nummer in Supabase (of maakt een nieuwe gebruiker aan).
):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers3.  **Verwerkt Locatie**: Als je een locatie stuurt, maakt hij een station aan.
4.  **Verwerkt Foto's**: Stuurt de foto naar Gemini 1.5 Flash om prijzen te extraheren.

### Stap 1: Update je `api/index.py`
Kopieer deze volledige code en vervang alles wat er nu in `api/index.py` staat op GitHub.
```python
import os
import json
import requests
from fastapi import FastAPI, Request, Response
from supabase import create_client, Client
import google.generativeai as genai

app = FastAPI()

# Configuratie laden vanuit Vercel Environment Variables
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
VERIFY_TOKEN = "orren_secret_token_2024"

# Initialisatie (alleen als de keys aanwezig zijn)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)
gemini = genai.GenerativeModel('gemini-1.5-flash')

@app.get("/api/webhook")
async def verify(request: Request):
    params = request.query_params
    if params.get("hub.verify_token") == VERIFY_TOKEN:
        return Response(content=params.get("hub.challenge"), status_code=200)
    return Response(content="Invalid token", status_code=403)

@app.post("/api/webhook")
async def webhook(request: Request):
    data = await request.json()
    
    try:
        # Check of het een bericht is
        if "messages" in data["entry"][0]["changes"][0]["value"]:
            message =```

---

### Hoe nu testen?

1.   data["entry"][0]["changes"][0]["value"]["messages"][0]
            number = message["from"]
            
            # 1. Gebruiker check/aanmaken
            user_check = supabase.table("users").select("*").eq("whatsapp_number", number).execute()
            if not**Commit & Push**: Zet deze code op GitHub.
2.  **Vercel Check**: Wacht tot de deployment klaar is (groen vinkje).
 user_check.data:
                supabase.table("users").insert({"whatsapp_number": number, "user_type": "public"}).execute()

            #3.  **WhatsApp Test**: 
    *   Ga op je telefoon naar het chatgesprek met het testnummer van Meta (dat nummer waar je eerder die verificatiecode naar stuurde).
    *   Typ een willekeurig bericht, bijvoorbeeld: *"Test!"*.
4.  **De 2. Locatie verwerken
            if message["type"] == "location":
                lat = message["location"]["latitude"]
                lon = message["location"]["longitude"]
                
                # Maak een nieuw station aan (skeleton V1)
                supabase.table("stations").insert({
                    "name": f"Station-{number[-4:]}",
                    "location": f"POINT({lon} {lat})"
                }).execute()
                
                send_ Magie**: Als alles goed staat, stuurt de bot binnen een paar seconden terug: *"Hey! Ik heb je bericht ontvangen. De brandstofbot is bijna klaarwhatsapp(number, "📍 Locatie opgeslagen! Stuur nu een foto van het prijzenbord van dit station.")

            # 3. Foto verwerken voor gebruik! ⛽"*.

**Lukt het om dit berichtje terug te krijgen?**

*P.S. Mocht je niks terug (Gemini AI)
            elif message["type"] == "image":
                image_id = message["image"]["id"]
                
                # Hakrijgen, check dan even in je Vercel Dashboard onder 'Logs'. Daar zie je precies of er een foutmelding verschijnt als jij een appje stuurt.*al de echte URL van de foto op bij Meta
                media_info = requests.get(
                    f"https://graph.facebook.com/v18.0/{image_id}",
                    headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
                ).json()
                
                # Download de afbeelding
                img_bytes = requests.get(
                    media_info["url"],
                    headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
                ).content

                # AI Analyse
                prompt = "Extract fuel prices (Petrol/Super and Diesel) from this image. Return ONLY JSON: {\"petrol\": float, \"diesel\": float, \"currency\": \"GHS\"}"
                response = gemini.generate_content([prompt, {"mime_type": "image/jpeg", "data": img_bytes}])
                
                try:
                    # Clean de AI response (soms zet Gemini er markdown omheen)
                    clean_json = response.text.replace('```json', '').replace('```', '').strip()
                    prices = json.loads(clean_json)
                    
                    msg = f"✅ Ik heb het volgende gelezen:\n⛽ Petrol: {prices.get('petrol')} GHS\n🚜 Diesel: {prices.get('diesel')} GHS\n\nKlopt dit?"
                    send_whatsapp(number, msg)
                    
                    # Hier zou je de data in 'fuel_prices' tabel opslaan
                except:
                    send_whatsapp(number, "❌ Sorry, ik kon de prijzen op deze foto niet goed lezen. Probeer het opnieuw met een scherpere foto.")

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

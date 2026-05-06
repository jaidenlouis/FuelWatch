from fastapi import FastAPI, Request, Response

app = FastAPI()

# Het geheime wachtwoord voor Meta
VERIFY_TOKEN = "orren_secret_token_2024"

@app.get("/api/webhook")
async def verify(request: Request):
    params = request.query_params
    # Als het wachtwoord klopt, stuur de challenge terug naar Meta
    if params.get("hub.verify_token") == VERIFY_TOKEN:
        return Response(content=params.get("hub.challenge"), status_code=200)
    return Response(content="Wachtwoord onjuist", status_code=403)

@app.post("/api/webhook")
async def message(request: Request):
    return Response(content="OK", status_code=200)

@app.get("/")
async def root():
    return {"message": "Server is online"}

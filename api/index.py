from fastapi import FastAPI, Request, Response

app = FastAPI()

VERIFY_TOKEN = "orren_secret_token_2024"

# Let op: we gebruiken hier alleen "/" omdat vercel.json de rest regelt
@app.get("/api/webhook")
async def verify(request: Request):
    params = request.query_params
    if params.get("hub.verify_token") == VERIFY_TOKEN:
        return Response(content=params.get("hub.challenge"), status_code=200)
    return Response(content="Wachtwoord onjuist", status_code=403)

@app.post("/api/webhook")
async def message(request: Request):
    return Response(content="OK", status_code=200)

@app.get("/")
async def root():
    return {"message": "Server is online"}

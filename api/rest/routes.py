from fastapi import FastAPI, File, UploadFile, Body, HTTPException
app = FastAPI()

@app.get("/")
def init():
    return {"Hello": "Humans"}

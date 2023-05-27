from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes.routes import router 
from api.routes.users import router as router_users 
from api.routes.files import router as router_files 
from api.routes.neo import router as router_neo 

origins = [
    "*"
]

app = FastAPI()

@app.get("/", tags=["Hello"])
def init():
    return {"Hello": "Humans"}

app.include_router(router_users)
app.include_router(router_files)
app.include_router(router)
app.include_router(router_neo)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
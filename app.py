import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from api.routes.routes import router 
from api.routes.users import router as router_users 
from api.routes.files import router as router_files 
from api.routes.neo import router as router_neo 

origins = [
    "*"
]

app = FastAPI()

connections = []  # Lista para almacenar las conexiones de los clientes


@app.get("/", tags=["Hello"])
def init():
    return {"Hello": "Humans"}

app.include_router(router_users)
app.include_router(router_files)
app.include_router(router)
app.include_router(router_neo)

@app.websocket("/ws/")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connections.append(websocket)

    try:
        while True:
            # Recibir mensaje del cliente WebSocket
            message = await websocket.receive_text(timeout=120)
            await websocket.send_text("¡Pong!")
    except Exception as e:
        print(f"Ocurrió un error en la conexión WebSocket: {str(e)}")
    finally:
        connections.remove(websocket)
    

@app.websocket("/ws/answer")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    while True:
        try:
            # Recibir datos del cliente
            print("query_request")
            query_request = await websocket.receive_json()
            print("query_request", query_request)

            # Determinar el tipo de solicitud
            request_type = query_request.get("type")

            # Validar el tipo de solicitud y realizar la acción correspondiente
            endpoint = "http://localhost:8000/api/v1/qa/answer-"+request_type 

            # Hacer una solicitud al endpoint en lugar de procesar directamente en el websocket
            async with httpx.AsyncClient(timeout=None) as client:
                response = await client.post(endpoint, json=query_request)
                print("response", response)

            if response.status_code == 200:
                await websocket.send_json(response.json())
            else:
                await websocket.send_json({"error": "Error al consultar el endpoint."})

        except WebSocketDisconnect:
            break


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
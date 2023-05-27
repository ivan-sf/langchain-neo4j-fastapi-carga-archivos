import uuid
import os
from typing import List
from fastapi import FastAPI, File, UploadFile, Body, HTTPException
from pydantic import BaseModel
from neo4j import GraphDatabase, basic_auth
from datetime import datetime
from langchain import OpenAI
from langchain.document_loaders.csv_loader import CSVLoader
from langchain.agents import create_csv_agent, create_json_agent
from langchain.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain.tools.json.tool import JsonSpec
from langchain.agents.agent_toolkits import JsonToolkit
import PyPDF2
from fastapi.middleware.cors import CORSMiddleware
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import json
import asyncio
from langchain.embeddings import OpenAIEmbeddings
import yaml

from api.models.models import Query, User, Consulta, QueryRequest, NodoCreateRequest, RelacionCreateRequest, PreguntaYML, PreguntaJson
from api.utils.neo4j import driver 

origins = [
    "*"
]

embeddings = OpenAIEmbeddings()

app = FastAPI()
connections = []  # Lista para almacenar las conexiones de los clientes

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def init():
    return {"Hello": "Humans"}
    
@app.post("/api/v1/users/create")
def create_user(user_info: User):
    user_id = user_info.user_id
    first_name = user_info.first_name
    last_name = user_info.last_name
    
    with driver.session() as session:
        session.write_transaction(create_user_node, user_id, first_name, last_name)
    
    return {"status": "Usuario creado correctamente."}


@app.post("/api/v1/files/upload_file/")
async def upload_file(user_id: str = Body(...), file: UploadFile = File(...)):
    # Verificar si el usuario existe en Neo4j
    with driver.session() as session:
        result = session.read_transaction(find_user_node, user_id)
    
    if not result:
        return {"error": "El usuario no existe."}
    
    # Obtener la extensión del archivo
    extension = os.path.splitext(file.filename)[1]
    
    if extension.lower() == ".csv":
        # Guardar el archivo en la carpeta CSV
        directory = f"files/{user_id}/csv"
    elif extension.lower() == ".txt":
        # Guardar el archivo en la carpeta TXT
        directory = f"files/{user_id}/txt"
    elif extension.lower() == ".pdf":
        # Guardar el archivo en la carpeta PDF
        directory = f"files/{user_id}/pdf"
    else:
        return {"error": "Formato de archivo inválido. Solo se permiten archivos CSV, TXT o PDF."}
    
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    # Generar un nombre único para el archivo con la extensión original
    unique_filename = str(uuid.uuid4()) + os.path.splitext(file.filename)[1]
    
    file_path = os.path.join(directory, unique_filename)
    
    # Leer y guardar el archivo
    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)
    
    # Convertir el PDF a texto y guardarlo en un archivo TXT
    if extension.lower() == ".pdf":
        txt_directory = f"files/{user_id}/txt"
        if not os.path.exists(txt_directory):
            os.makedirs(txt_directory)
        txt_file_path = os.path.join(txt_directory, unique_filename.replace(".pdf", ".txt"))
        txt_content = convert_pdf_to_txt(file_path)
        with open(txt_file_path, "wb") as txt_file:
            txt_file.write(txt_content)
    
    # Crear la relación entre el usuario y el archivo en Neo4j
    with driver.session() as session:
        session.write_transaction(create_file_node, user_id, file.filename, unique_filename, extension)
    
    return {"user_id": user_id, "filename": unique_filename, "original_filename": file.filename, "status": "Archivo cargado correctamente."}

@app.post("/api/v1/qa/answer-csv")
def run_query(consulta: Consulta):
    # Verificar si el archivo existe
    file_path = os.path.join("files/"+consulta.user_id+"/csv", consulta.file_name)
    if not os.path.exists(file_path):
        return {"error": "El archivo no existe."}

    llm = OpenAI(temperature=1)
    loader = CSVLoader(file_path)
    data = loader.load()

    agent = create_csv_agent(llm, file_path, verbose=True)

    # Ejecutar la consulta y guardar la pregunta y respuesta en nodos individuales en Neo4j
    with driver.session() as session:
        response = agent.run(consulta.query.question)
        create_nodes_in_neo4j(session, consulta.file_name, consulta.query.question, response)

    return {"question": consulta.query.question, "answer": response}


async def process_question_csv(session, agent, question):
    response = agent.run(question)
    # Realiza las operaciones necesarias con la respuesta, como guardarla en la base de datos o enviarla al cliente
    return {"question": question, "answer": response}


# Definir el endpoint para responder preguntas sobre un archivo CSV
@app.post("/api/v1/qa/answer-yml")
def responder_pregunta(consulta: PreguntaYML):
    # Verificar si el archivo existe
    file_path = os.path.join("files", consulta.file_name)
    if not os.path.exists(file_path):
        return {"error": "El archivo no existe."}

    # Cargar la especificación JSON del archivo YAML
    with open(file_path) as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
    json_spec = JsonSpec(dict_=data, max_value_length=4000)

    # Crear el agente JSON
    llm = OpenAI(temperature=0)
    json_toolkit = JsonToolkit(spec=json_spec)
    json_agent = create_json_agent(llm=llm, toolkit=json_toolkit, verbose=True)

    # Ejecutar el agente JSON para responder la pregunta
    response = json_agent.run(consulta.query)

    return {"question": consulta.query, "answer": response}


@app.post("/api/v1/qa/answer-pdf")
def answerSearch(query_request: QueryRequest):
    file_name_txt = query_request.file_name.replace(".pdf", ".txt")

    loader = DirectoryLoader('files/' + query_request.user_id + "/txt/", glob=file_name_txt)
    documents = loader.load()
    
    text_splitter = CharacterTextSplitter(chunk_size=2500, chunk_overlap=0)
    texts = text_splitter.split_documents(documents)

    docsearch = Chroma.from_documents(texts, embeddings)
    qa = RetrievalQA.from_chain_type(
        llm=OpenAI(),
        chain_type="stuff",
        retriever=docsearch.as_retriever(       )
    )

    question = query_request.query
    answer = qa.run(question)

    with driver.session() as session:
        create_nodes_in_neo4j(session, query_request.file_name, question, answer)

    return {"question": question, "answer": answer}
    



# Definir el endpoint para responder preguntas sobre un objeto JSON
@app.post("/api/v0/qa/answer-json")
def responder_pregunta(pregunta: PreguntaJson):
    # Obtener el objeto JSON y la pregunta de la solicitud
    json_obj = pregunta.json_obj
    query = pregunta.query

    # Crear la especificación JSON a partir del objeto JSON proporcionado
    json_spec = JsonSpec(dict_=json_obj, max_value_length=4000)

    # Crear el agente JSON
    llm = OpenAI(temperature=0)
    json_toolkit = JsonToolkit(spec=json_spec)
    json_agent = create_json_agent(llm=llm, toolkit=json_toolkit, verbose=True)

    # Ejecutar el agente JSON para responder la pregunta
    response = json_agent.run(query)

    return {"question": query, "answer": response}

@app.post("/api/v0/qa/answer-txt")
def answerSearch(query_request: QueryRequest):
    loader = DirectoryLoader('files/' + query_request.user_id + "/txt/", glob=query_request.file_name)
    documents = loader.load()
    
    text_splitter = CharacterTextSplitter(chunk_size=2500, chunk_overlap=0)
    texts = text_splitter.split_documents(documents)

    docsearch = Chroma.from_documents(texts, embeddings)
    qa = RetrievalQA.from_chain_type(
        llm=OpenAI(),
        chain_type="stuff",
        retriever=docsearch.as_retriever()
    )

    question = query_request.query
    answer = qa.run(question)

    with driver.session() as session:
        create_nodes_in_neo4j(session, query_request.file_name, question, answer)

    return {"question": question, "answer": answer}


@app.post("/api/v1/neo/create-node")
def crear_nodo(request: NodoCreateRequest):
    etiqueta = request.etiqueta
    propiedades = request.propiedades

    query = f"CREATE (n:{etiqueta} $propiedades) RETURN n"
    
    session = driver.session()
    transaction = session.begin_transaction()
    
    try:
        resultado = transaction.run(query, propiedades=propiedades)
        nodo_creado = resultado.single()[0]
        
        transaction.commit()
        return {"nodo_creado": nodo_creado}
    except Exception as e:
        transaction.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        transaction.close()
        session.close()


@app.post("/api/v1/neo/create-relation")
def crear_relacion(request: RelacionCreateRequest):
    nodo1_etiqueta = request.nodo1_etiqueta
    nodo1_propiedades = request.nodo1_propiedades
    nodo2_etiqueta = request.nodo2_etiqueta
    nodo2_propiedades = request.nodo2_propiedades
    relacion_nombre = request.relacion_nombre
    relacion_propiedades = request.relacion_propiedades

    query = f"""
    MERGE (n1:{nodo1_etiqueta} {obtener_parametros_cypher(nodo1_propiedades)})
    MERGE (n2:{nodo2_etiqueta} {obtener_parametros_cypher(nodo2_propiedades)})
    MERGE (n1)-[r:{relacion_nombre} {obtener_parametros_cypher(relacion_propiedades)}]->(n2)
    RETURN r
    """

    session = driver.session()
    transaction = session.begin_transaction()

    try:
        resultado = transaction.run(query, **nodo1_propiedades, **nodo2_propiedades, **relacion_propiedades)
        relacion_creada = resultado.single()[0]

        transaction.commit()
        return {"relacion_creada": relacion_creada}
    except Exception as e:
        transaction.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        transaction.close()
        session.close()

@app.websocket("/ws/")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connections.append(websocket)

    try:
        while True:
            # Recibir mensaje del cliente WebSocket
            message = await websocket.receive_text()
            # Procesar el mensaje según tus necesidades
            # ...
            # Responder al cliente WebSocket
            await websocket.send_text("¡Pong!")
    except Exception as e:
        print(f"Ocurrió un error en la conexión WebSocket: {str(e)}")
    finally:
        connections.remove(websocket)

@app.websocket("/ws/answer-csv")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connections.append(websocket)

    try:
        while True:
            consulta = await websocket.receive_text()
            consulta_json = json.loads(consulta)

            file_path = os.path.join("files/" + consulta_json["user_id"] + "/csv", consulta_json["file_name"])
            if not os.path.exists(file_path):
                await websocket.send_json({"error": "El archivo no existe."})
                continue

            llm = OpenAI(temperature=0)
            loader = CSVLoader(file_path)
            data = loader.load()

            answers = []

            with driver.session() as session:
                tasks = []
                for question in consulta_json["questions"]:
                    agent = create_csv_agent(llm, file_path, verbose=True)  # Crear un nuevo agente para cada pregunta
                    task = process_question_csv(session, agent, question)
                    tasks.append(task)

                # Esperar a que se completen todas las solicitudes concurrentes
                completed_tasks = await asyncio.gather(*tasks)

                for result in completed_tasks:
                    create_nodes_in_neo4j(session, consulta_json["file_name"], result["question"], result["answer"])
                    answers.append(result)

            await websocket.send_json({"answers": answers})

    except WebSocketDisconnect:
        connections.remove(websocket)

@app.websocket("/ws/answer-txt")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    while True:
        try:
            # Recibir datos del cliente
            query_request = await websocket.receive_json()
            
            # Procesar la solicitud del cliente
            loader = DirectoryLoader('files/' + query_request["user_id"] + "/txt/", glob=query_request["file_name"])
            documents = loader.load()

            text_splitter = CharacterTextSplitter(chunk_size=2500, chunk_overlap=0)
            texts = text_splitter.split_documents(documents)

            docsearch = Chroma.from_documents(texts, embeddings)
            qa = RetrievalQA.from_chain_type(
                llm=OpenAI(),
                chain_type="stuff",
                retriever=docsearch.as_retriever()
            )

            question = query_request["query"]
            answer = qa.run(question)

            with driver.session() as session:
                create_nodes_in_neo4j(session, query_request["file_name"], question, answer)

            response = {"question": question, "answer": answer}
            
            # Enviar la respuesta al cliente
            await websocket.send_json(response)
            
        except WebSocketDisconnect:
            break

@app.websocket("/ws/answer-pdf")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    while True:
        try:
            # Recibir datos del cliente
            query_request = await websocket.receive_json()
            
            # Procesar la solicitud del cliente
            file_name_txt = query_request["file_name"].replace(".pdf", ".txt")

            loader = DirectoryLoader('files/' + query_request["user_id"] + "/txt/", glob=file_name_txt)
            documents = loader.load()

            text_splitter = CharacterTextSplitter(chunk_size=2500, chunk_overlap=0)
            texts = text_splitter.split_documents(documents)

            docsearch = Chroma.from_documents(texts, embeddings)
            qa = RetrievalQA.from_chain_type(
                llm=OpenAI(),
                chain_type="stuff",
                retriever=docsearch.as_retriever()
            )

            question = query_request["query"]
            answer = qa.run(question)

            with driver.session() as session:
                create_nodes_in_neo4j(session, query_request["file_name"], question, answer)

            response = {"question": question, "answer": answer}
            
            # Enviar la respuesta al cliente
            await websocket.send_json(response)
            
        except WebSocketDisconnect:
            break


def convert_pdf_to_txt(pdf_path):
    with open(pdf_path, "rb") as file:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text.encode("utf-8")

# Función para crear una pregunta y su respuesta con relaciones en Neo4j
def create_nodes_in_neo4j(session, file_name, question, answer):
    timestamp = datetime.now().timestamp() 
    
    session.run(
        """
        MATCH (f:File {unique_filename: $file_name})
        CREATE (f)<-[:DOCUMENT_QUESTION]-(p:Question {contenido: $question, timestamp: $timestamp})
        CREATE (p)-[:DOCUMENT_ANSWER]->(r:Answer {answer: $answer, timestamp: $timestamp})
        """,
        file_name=file_name,
        question=question,
        answer=answer,
        timestamp=timestamp
    )

# Función para crear un nodo "Person" en Neo4j
def create_user_node(tx, user_id, first_name, last_name):
    tx.run(
        """
        MERGE (p:Person {user_id: $user_id})
        SET p.first_name = $first_name, p.last_name = $last_name
        """,
        user_id=user_id,
        first_name=first_name,
        last_name=last_name
    )

# Función para buscar un nodo "Person" en Neo4j
def find_user_node(tx, user_id):
    result = tx.run("MATCH (p:Person {user_id: $user_id}) RETURN p", user_id=user_id)
    return result.single() is not None

# Función para crear un nodo "File" en Neo4j y establecer la relación entre el usuario y el archivo
def create_file_node(tx, user_id, original_filename, unique_filename, file_type):
    tx.run(
        """
        MATCH (p:Person {user_id: $user_id})
        MERGE (f:File {original_filename: $original_filename, unique_filename: $unique_filename})
        MERGE (t:FileType {type: $file_type})<-[:HAS_FILES_TYPE]-(p)
        MERGE (f)-[:DOCUMENT_TYPE]->(t)
        """,
        user_id=user_id,
        original_filename=original_filename,
        unique_filename=unique_filename,
        file_type=file_type
    )

def obtener_parametros_cypher(propiedades):
    return "{" + ", ".join(f"{clave}: ${clave}" for clave in propiedades.keys()) + "}"



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
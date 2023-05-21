from typing import List
from fastapi import FastAPI, File, UploadFile, Body
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain import OpenAI
from langchain.document_loaders.csv_loader import CSVLoader
from neo4j import GraphDatabase, basic_auth
from langchain.agents import create_csv_agent
import os
import uuid

load_dotenv()

app = FastAPI()

# Configurar la conexión a Neo4j
neo4j_uri = os.getenv("NEO4J_URI")
neo4j_user = os.getenv("NEO4J_USER")
neo4j_password = os.getenv("NEO4J_PASSWORD")
driver = GraphDatabase.driver(neo4j_uri, auth=basic_auth(neo4j_user, neo4j_password))

class Query(BaseModel):
    question: str

class User(BaseModel):
    user_id: str
    first_name: str
    last_name: str

class Consulta(BaseModel):
    query: Query
    file_name: str


@app.post("/users/")
def create_user(user_info: User):
    user_id = user_info.user_id
    first_name = user_info.first_name
    last_name = user_info.last_name
    
    with driver.session() as session:
        session.write_transaction(create_user_node, user_id, first_name, last_name)
    
    return {"status": "Usuario creado correctamente."}

@app.post("/upload_csv/")
async def upload_csv(user_id: str = Body(...), file: UploadFile = File(...)):
    # Verificar si el usuario existe en Neo4j
    with driver.session() as session:
        result = session.read_transaction(find_user_node, user_id)
    
    if not result:
        return {"error": "El usuario no existe."}
    
    # Verificar la extensión del archivo
    if file.filename.endswith(".csv"):
        # Generar un nombre único para el archivo
        unique_filename = str(uuid.uuid4()) + ".csv"
        
        # Crear la ruta completa para guardar el archivo
        file_path = os.path.join("files", unique_filename)
        
        # Leer y guardar el archivo
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Crear la relación entre el usuario y el archivo en Neo4j
        with driver.session() as session:
            session.write_transaction(create_file_node, user_id, file.filename, unique_filename)
        
        return {"user_id": user_id, "filename": unique_filename, "original_filename": file.filename, "status": "Archivo cargado correctamente."}
    else:
        return {"error": "Formato de archivo inválido. Solo se permiten archivos CSV."}

@app.post("/consultas")
def run_query(consulta: Consulta):
    # Verificar si el archivo existe
    file_path = os.path.join("files", consulta.file_name)
    if not os.path.exists(file_path):
        return {"error": "El archivo no existe."}

    llm = OpenAI(temperature=0)
    loader = CSVLoader(file_path)
    data = loader.load()

    agent = create_csv_agent(llm, file_path, verbose=True)

    # Ejecutar la consulta y guardar la pregunta y respuesta en nodos individuales en Neo4j
    with driver.session() as session:
        response = agent.run(consulta.query.question)
        session.run(
            """
            MATCH (f:File {unique_filename: $file_name})
            CREATE (f)<-[:PERTENECE_A]-(p:Pregunta {contenido: $question})
            CREATE (p)-[:TIENE_RESPUESTA]->(r:Respuesta {answer: $answer})
            """,
            file_name=consulta.file_name,
            question=consulta.query.question,
            answer=response
        )

    return {"question": consulta.query.question, "answer": response}

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
def create_file_node(tx, user_id, original_filename, unique_filename):
    tx.run(
        """
        MATCH (p:Person {user_id: $user_id})
        CREATE (f:File {original_filename: $original_filename, unique_filename: $unique_filename})
        CREATE (f)-[:PERTENECE_A]->(p)
        """,
        user_id=user_id,
        original_filename=original_filename,
        unique_filename=unique_filename
    )
    
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
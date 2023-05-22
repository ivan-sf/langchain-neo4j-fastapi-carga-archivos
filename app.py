import uuid
import os
from typing import List
from fastapi import FastAPI, File, UploadFile, Body
from pydantic import BaseModel
from dotenv import load_dotenv
from neo4j import GraphDatabase, basic_auth
from datetime import datetime
from langchain import OpenAI
from langchain.document_loaders.csv_loader import CSVLoader
from langchain.agents import create_csv_agent
from langchain.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.chains import RetrievalQA
import PyPDF2

load_dotenv()

app = FastAPI()

# Configurar la conexión a Neo4j
neo4j_uri = os.getenv("NEO4J_URI")
neo4j_user = os.getenv("NEO4J_USER")
neo4j_password = os.getenv("NEO4J_PASSWORD")
driver = GraphDatabase.driver(neo4j_uri, auth=basic_auth(neo4j_user, neo4j_password))
embeddings = OpenAIEmbeddings()

class Query(BaseModel):
    question: str

class User(BaseModel):
    user_id: str
    first_name: str
    last_name: str

class Consulta(BaseModel):
    query: Query
    user_id: str
    file_name: str

class QueryRequest(BaseModel):
    query: str
    user_id: str
    file_name: str


@app.post("/users/")
def create_user(user_info: User):
    user_id = user_info.user_id
    first_name = user_info.first_name
    last_name = user_info.last_name
    
    with driver.session() as session:
        session.write_transaction(create_user_node, user_id, first_name, last_name)
    
    return {"status": "Usuario creado correctamente."}

def convert_pdf_to_txt(pdf_path):
    with open(pdf_path, "rb") as file:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text.encode("utf-8")

@app.post("/upload_file/")
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
    
    # Generar un nombre único para el archivo
    unique_filename = str(uuid.uuid4())
    file_path = os.path.join(directory, unique_filename + extension)
    
    # Leer y guardar el archivo
    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)
    
    # Convertir el PDF a texto y guardarlo en un archivo TXT
    if extension.lower() == ".pdf":
        txt_directory = f"files/{user_id}/txt"
        if not os.path.exists(txt_directory):
            os.makedirs(txt_directory)
        txt_file_path = os.path.join(txt_directory, unique_filename + ".txt")
        txt_content = convert_pdf_to_txt(file_path)
        with open(txt_file_path, "wb") as txt_file:
            txt_file.write(txt_content)
    
    # Crear la relación entre el usuario y el archivo en Neo4j
    with driver.session() as session:
        session.write_transaction(create_file_node, user_id, file.filename, unique_filename, extension.lower())
    
    return {"user_id": user_id, "filename": unique_filename, "original_filename": file.filename, "status": "Archivo cargado correctamente."}

@app.post("/answer-csv")
def run_query(consulta: Consulta):
    # Verificar si el archivo existe
    file_path = os.path.join("files/"+consulta.user_id+"/csv", consulta.file_name)
    if not os.path.exists(file_path):
        return {"error": "El archivo no existe."}

    llm = OpenAI(temperature=0)
    loader = CSVLoader(file_path)
    data = loader.load()

    agent = create_csv_agent(llm, file_path, verbose=True)

    # Ejecutar la consulta y guardar la pregunta y respuesta en nodos individuales en Neo4j
    with driver.session() as session:
        response = agent.run(consulta.query.question)
        create_nodes_in_neo4j(session, consulta.file_name, consulta.query.question, response)

    return {"question": consulta.query.question, "answer": response}


@app.post("/answer-txt")
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



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
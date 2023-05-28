import os
import json
import asyncio
import yaml
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from api.models.models import Query, QueryCsv, QueryRequest, QueryJson
from api.utils.neo4j import driver 
from datetime import datetime
from langchain import OpenAI
from langchain.agents import create_csv_agent, create_json_agent
from langchain.agents.agent_toolkits import JsonToolkit
from langchain.chains import RetrievalQA
from langchain.document_loaders.csv_loader import CSVLoader
from langchain.document_loaders import DirectoryLoader, TextLoader
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain.tools.json.tool import JsonSpec
from langchain.vectorstores import Chroma
from neo4j import GraphDatabase, basic_auth
from pydantic import BaseModel
from typing import List

# Crea un enrutador para agrupar los endpoints
router = APIRouter(prefix="/api/v1/qa")
embeddings = OpenAIEmbeddings()


@router.post("/answer-pdf", tags=["Q-A"])
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
    

@router.post("/answer-csv", tags=["Q-A"])
def run_query(consulta: QueryCsv):
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




# Definir el endpoint para responder preguntas sobre un archivo CSV
@router.post("/answer-yml", tags=["Q-A"])
def responder_pregunta(consulta: QueryRequest):
    # Verificar si el archivo existe
    file_path = os.path.join("files/"+consulta.user_id+"/yml", consulta.file_name)
    if not os.path.exists(file_path):
        file_path = os.path.join("files/"+consulta.user_id+"/yaml", consulta.file_name)
        if not os.path.exists(file_path):
            return {"error": "El archivo no existe."}

    # Cargar la especificación JSON del archivo YAML
    with open(file_path) as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
    json_spec = JsonSpec(dict_=data, max_value_length=4000)

    # Crear el agente JSON
    llm = OpenAI(temperature=0)
    json_toolkit = JsonToolkit(spec=json_spec)
    agent = create_json_agent(llm=llm, toolkit=json_toolkit, verbose=True)

    # response = agent.run(consulta.query)
    # Ejecutar el agente JSON para responder la pregunta
    with driver.session() as session:
        response = agent.run(consulta.query)
        create_nodes_in_neo4j(session, consulta.file_name, consulta.query, response)

    return {"question": consulta.query, "answer": response}


# Definir el endpoint para responder preguntas sobre un objeto JSON
@router.post("/answer-json", tags=["Q-A"])
def responder_pregunta(pregunta: QueryJson):
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
    # Crear nodos en Neo4j
    

    return {"question": query, "answer": response}


# Definir el endpoint para responder preguntas sobre un objeto JSON
@router.post("/answer-json-file", tags=["Q-A"])
def responder_pregunta(pregunta: QueryRequest):
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
    # Crear nodos en Neo4j
    

    return {"question": query, "answer": response}


@router.post("/answer-txt", tags=["Q-A"])
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


async def process_question_csv(session, agent, question):
    response = agent.run(question)
    # Realiza las operaciones necesarias con la respuesta, como guardarla en la base de datos o enviarla al cliente
    return {"question": question, "answer": response}
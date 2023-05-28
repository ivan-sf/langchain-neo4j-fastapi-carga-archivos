import os
from langchain.tools import Tool
from langchain.agents import initialize_agent, Tool, AgentType
from langchain.utilities import GoogleSearchAPIWrapper, GoogleSerperAPIWrapper
from dotenv import load_dotenv
from fastapi import APIRouter
from api.models.google import QueryGoogle
from langchain.llms import OpenAI

router = APIRouter(prefix="/api/v1/google")

@router.post("/search", tags=["Google"])
def responder_pregunta(query:QueryGoogle):
    search = GoogleSearchAPIWrapper(k=query.number_results)
    tool = Tool(
        name = "Google Search",
        description="Buscar en Google y retorna el primer resultado.",
        # description="Buscar en Google resultados recientes.",
        func=search.run
    )
    response = tool.run(query.question)
    return {"response":response}

@router.post("/google-serper-api", tags=["Google"])
def responder_pregunta(query:QueryGoogle):
    search = GoogleSerperAPIWrapper(k=query.number_results)
    response = search.run(query.question)
    return {"response":response}

@router.post("/agent-google-serper-openai", tags=["Google"])
def responder_pregunta(query:QueryGoogle):
    llm = OpenAI(temperature=0)
    search = GoogleSerperAPIWrapper()
    tools = [
        Tool(
            name="Intermediate Answer",
            func=search.run,
            description="útil para cuando necesita preguntar con la búsqueda"
        )
    ]

    self_ask_with_search = initialize_agent(tools, llm, agent=AgentType.SELF_ASK_WITH_SEARCH, verbose=True)
    response = self_ask_with_search.run(query.question)

    return {"response": response}

import os
from langchain.tools import Tool
from langchain.agents import initialize_agent, Tool, AgentType
from langchain.utilities import GoogleSearchAPIWrapper, GoogleSerperAPIWrapper
from fastapi import APIRouter
from api.models.google import QueryGoogle
from api.models.models import Query
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


from langchain.chat_models import ChatOpenAI
from langchain.experimental.plan_and_execute import PlanAndExecute, load_agent_executor, load_chat_planner
from langchain.llms import OpenAI
from langchain import SerpAPIWrapper
from langchain.agents.tools import Tool
from langchain import LLMMathChain

@router.post("/planner-serpapi", tags=["Google"])
def responder_pregunta(query:Query):
    search = SerpAPIWrapper()
    llm = OpenAI(temperature=0)
    llm_math_chain = LLMMathChain.from_llm(llm=llm, verbose=True)
    tools = [
        Tool(
            name = "Search",
            func=search.run,
            description="useful for when you need to answer questions about current events"
        ),
        Tool(
            name="Calculator",
            func=llm_math_chain.run,
            description="useful for when you need to answer questions about math"
        ),
    ]
    model = ChatOpenAI(temperature=0)
    planner = load_chat_planner(model)
    executor = load_agent_executor(model, tools, verbose=True)
    agent = PlanAndExecute(planner=planner, executor=executor, verbose=True)
    response = agent.run(query.question)
    return {"response":response}

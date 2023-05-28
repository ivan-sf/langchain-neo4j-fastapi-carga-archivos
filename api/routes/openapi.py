import os
from typing import List, Optional
from langchain.chains import LLMChain
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.requests import Requests
from langchain.tools import APIOperation, OpenAPISpec
from langchain.agents import AgentType, Tool, initialize_agent
from langchain.agents.agent_toolkits import NLAToolkit
from fastapi import APIRouter
from api.models.models import Query

router = APIRouter(prefix="/api/v1/openapi")

@router.post("/answer-clothing", tags=["Openapi"])
def responder_pregunta(query:Query):
    llm = OpenAI(temperature=0, max_tokens=700) # You can swap between different core LLM's here.
    speak_toolkit = NLAToolkit.from_llm_and_url(llm, "https://api.speak.com/openapi.yaml")
    klarna_toolkit = NLAToolkit.from_llm_and_url(llm, "https://www.klarna.com/us/shopping/public/openai/v0/api-docs/")

    # Slightly tweak the instructions from the default agent
    openapi_format_instructions = """
    Use the following format:

    Question: the input question you must answer
    Thought: you should always think about what to do
    Action: the action to take, should be one of [{tool_names}]
    Action Input: what to instruct the AI Action representative.
    Observation: The Agent's response
    ... (this Thought/Action/Action Input/Observation can repeat N times)
    Thought: I now know the final answer. User can't see any of my observations, API responses, links, or tools.
    Final Answer: the final answer to the original input question with the right amount of detail

    When responding with your Final Answer, remember that the person you are responding to CANNOT see any of your Thought/Action/Action Input/Observations, so if there is any relevant information there you need to include it explicitly in your response, always answer in spanish.
    """

    natural_language_tools = speak_toolkit.get_tools() + klarna_toolkit.get_tools()
    mrkl = initialize_agent(natural_language_tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, 
                            verbose=True, agent_kwargs={"format_instructions":openapi_format_instructions})

    response = mrkl.run(query.question)
    return {"response":response}


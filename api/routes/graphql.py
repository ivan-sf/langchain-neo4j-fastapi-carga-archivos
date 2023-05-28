from langchain import OpenAI
from langchain.agents import load_tools, initialize_agent, AgentType
from langchain.utilities import GraphQLAPIWrapper
from dotenv import load_dotenv
from fastapi import APIRouter
from api.models.openai import QueryGrapQL

load_dotenv()
llm = OpenAI(temperature=0)
router = APIRouter(prefix="/api/v1/qa")

@router.post("/answer-graphql-be4collect-users", tags=["Q-A"])
def responder_pregunta(query:QueryGrapQL):
    url = query.api_url
    tools = load_tools(["graphql"], graphql_endpoint="https://spacex-production.up.railway.app/", llm=llm)
    agent = initialize_agent(tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True)
    graphql_fields = """

        query Dragons {
            dragons {
                active
                crew_capacity
                description
                dry_mass_kg
                dry_mass_lb
                first_flight
                id
                name
                orbit_duration_yr
                sidewall_angle_deg
                type
                wikipedia
            }
        }

    """

    suffix = query.question
    agent_res = agent.run(suffix + graphql_fields)

    return {"question": suffix, "answer": agent_res}


@router.post("/answer-graphql-spacex-dragons", tags=["Q-A"])
def responder_pregunta(query:QueryGrapQL):
    tools = load_tools(["graphql"], graphql_endpoint="https://be4collect-graphql-apollo.herokuapp.com/", llm=llm)
    agent = initialize_agent(tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True)
    graphql_fields = """

    query UserCollects {
        userCollects {
            name
            last_name
            belongsToCompanies {
                name
            }
        }
    }


    """

    suffix = query.question
    agent_res = agent.run(suffix + graphql_fields)

    return {"question": suffix, "answer": agent_res}

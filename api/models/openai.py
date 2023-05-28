from pydantic import BaseModel

class Query(BaseModel):
    question: str
    user_id: str

class Generate(BaseModel):
    generate: str
    times: int
    user_id: str


class CreateCompletionRequest(BaseModel):
    model: str
    prompt: str
    max_tokens: int
    temperature: float


class CreateCompletionResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: list[dict]
    usage: dict

class QueryGrapQL(BaseModel):
    question: str
    user_id: str
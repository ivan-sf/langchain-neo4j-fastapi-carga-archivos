from pydantic import BaseModel

class QueryGoogle(BaseModel):
    question: str
    number_results: int
    user_id: str

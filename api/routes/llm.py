import json
from fastapi import APIRouter, Body, File, UploadFile
from api.models.openai import Query, Generate,CreateCompletionRequest, CreateCompletionResponse
from langchain.llms import OpenAI
import openai

router = APIRouter(prefix="/api/v1/llm")

@router.post("/basic-prompt/", tags=["LLM"])
async def promp_basic(query:Query):
    llm = OpenAI(temperature=0.9)
    response = llm(query.question)
    return {"response": response}

@router.post("/estimate-tokens/", tags=["LLM"])
async def promp_basic(query:Query):
    llm = OpenAI(n=2, best_of=2)
    response = llm.get_num_tokens(query.question)
    return {"response": response}

@router.post("/generate/", tags=["LLM"])
async def promp_basic(query:Generate):
    llm = OpenAI(n=2, best_of=2)
    response = llm.generate([query.generate]*query.times)
    return {"response": response, "tokens": response.llm_output}


@router.post("/completions", response_model=CreateCompletionResponse, tags=["LLM"])
async def create_completion(request: CreateCompletionRequest):
    completion = openai.Completion.create(
        model=request.model,
        prompt=request.prompt,
        max_tokens=request.max_tokens,
        temperature=request.temperature
    )

    response = {
        "id": completion.id,
        "object": completion.object,
        "created": completion.created,
        "model": completion.model,
        "choices": [
            {
                "text": choice.text,
                "index": choice.index,
                "logprobs": choice.logprobs,
                "finish_reason": choice.finish_reason
            } for choice in completion.choices
        ],
        "usage": {
            "prompt_tokens": completion.usage.prompt_tokens,
            "completion_tokens": completion.usage.completion_tokens,
            "total_tokens": completion.usage.total_tokens
        }
    }

    return response

    # text-davinci-003
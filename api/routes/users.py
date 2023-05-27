from api.models.models import User
from fastapi import APIRouter
from api.utils.neo4j_utils import create_user_node
from api.utils.neo4j import driver

router = APIRouter()

router = APIRouter(prefix="/api/v1/users")

@router.post("/create", tags=["Users"])
def create_user(user_info: User):
    user_id = user_info.user_id
    first_name = user_info.first_name
    last_name = user_info.last_name
    
    with driver.session() as session:
        session.write_transaction(create_user_node, user_id, first_name, last_name)
    
    return {"status": "Usuario creado correctamente."}



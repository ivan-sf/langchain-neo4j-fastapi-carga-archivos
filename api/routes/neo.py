from api.models.models import NodoCreateRequest, RelacionCreateRequest
from fastapi import APIRouter
from api.utils.neo4j import driver
from api.utils.neo4j_utils import get_params_cypher

router = APIRouter()

router = APIRouter(prefix="/api/v1/neo")

@router.post("/create-node", tags=["Neo4j"])
def crear_nodo(request: NodoCreateRequest):
    etiqueta = request.etiqueta
    propiedades = request.propiedades

    query = f"CREATE (n:{etiqueta} $propiedades) RETURN n"
    
    session = driver.session()
    transaction = session.begin_transaction()
    
    try:
        resultado = transaction.run(query, propiedades=propiedades)
        nodo_creado = resultado.single()[0]
        
        transaction.commit()
        return {"nodo_creado": nodo_creado}
    except Exception as e:
        transaction.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        transaction.close()
        session.close()


@router.post("/create-relation", tags=["Neo4j"])
def crear_relacion(request: RelacionCreateRequest):
    nodo1_etiqueta = request.nodo1_etiqueta
    nodo1_propiedades = request.nodo1_propiedades
    nodo2_etiqueta = request.nodo2_etiqueta
    nodo2_propiedades = request.nodo2_propiedades
    relacion_nombre = request.relacion_nombre
    relacion_propiedades = request.relacion_propiedades

    query = f"""
    MERGE (n1:{nodo1_etiqueta} {get_params_cypher(nodo1_propiedades)})
    MERGE (n2:{nodo2_etiqueta} {get_params_cypher(nodo2_propiedades)})
    MERGE (n1)-[r:{relacion_nombre} {get_params_cypher(relacion_propiedades)}]->(n2)
    RETURN r
    """

    session = driver.session()
    transaction = session.begin_transaction()

    try:
        resultado = transaction.run(query, **nodo1_propiedades, **nodo2_propiedades, **relacion_propiedades)
        relacion_creada = resultado.single()[0]

        transaction.commit()
        return {"relacion_creada": relacion_creada}
    except Exception as e:
        transaction.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        transaction.close()
        session.close()


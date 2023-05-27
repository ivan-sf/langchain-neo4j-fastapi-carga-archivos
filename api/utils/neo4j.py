import os
from neo4j import GraphDatabase, basic_auth
from dotenv import load_dotenv
# Configurar la conexión a Neo4j
load_dotenv()
neo4j_uri = os.getenv("NEO4J_URI")
neo4j_user = os.getenv("NEO4J_USER")
neo4j_password = os.getenv("NEO4J_PASSWORD")

class Neo4jDriver:
    def __init__(self, uri, user, password):
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def __enter__(self):
        return self._driver.session()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._driver.close()

# Crear una instancia del controlador de Neo4j
driver = GraphDatabase.driver(neo4j_uri, auth=basic_auth(neo4j_user, neo4j_password))

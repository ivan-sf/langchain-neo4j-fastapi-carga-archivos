def find_user_node(tx, user_id):
    result = tx.run("MATCH (p:Person {user_id: $user_id}) RETURN p", user_id=user_id)
    return result.single() is not None

def create_file_node(tx, user_id, original_filename, unique_filename, file_type):
    tx.run(
        """
        MATCH (p:Person {user_id: $user_id})
        MERGE (f:File {original_filename: $original_filename, unique_filename: $unique_filename})
        MERGE (t:FileType {type: $file_type})<-[:HAS_FILES_TYPE]-(p)
        MERGE (f)-[:DOCUMENT_TYPE]->(t)
        """,
        user_id=user_id,
        original_filename=original_filename,
        unique_filename=unique_filename,
        file_type=file_type
    )


# Función para crear un nodo "Person" en Neo4j
def create_user_node(tx, user_id, first_name, last_name):
    tx.run(
        """
        MERGE (p:Person {user_id: $user_id})
        SET p.first_name = $first_name, p.last_name = $last_name
        """,
        user_id=user_id,
        first_name=first_name,
        last_name=last_name
    )


def get_params_cypher(propiedades):
    return "{" + ", ".join(f"{clave}: ${clave}" for clave in propiedades.keys()) + "}"
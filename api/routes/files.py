import os
import uuid
import PyPDF2
from fastapi import APIRouter, Body, File, UploadFile
from api.utils.neo4j import driver
from api.utils.file_utils import convert_pdf_to_txt
from api.utils.neo4j_utils import find_user_node, create_file_node

router = APIRouter(prefix="/api/v1/files")

@router.post("/upload_file/", tags=["Files"])
async def upload_file(user_id: str = Body(...), file: UploadFile = File(...)):
    # Verificar si el usuario existe en Neo4j
    with driver.session() as session:
        result = session.read_transaction(find_user_node, user_id)

    if not result:
        return {"error": "El usuario no existe."}

    # Obtener la extensión del archivo
    extension = os.path.splitext(file.filename)[1].lower()

    allowed_extensions = [".csv", ".txt", ".pdf", ".yml", ".yaml", ".json"]
    if extension not in allowed_extensions:
        return {"error": "Formato de archivo inválido. Solo se permiten archivos CSV, TXT, PDF, YAML o JSON."}

    # Guardar el archivo en una carpeta específica según la extensión
    directory = f"files/{user_id}/{extension[1:]}"
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Generar un nombre único para el archivo con la extensión original
    unique_filename = str(uuid.uuid4()) + os.path.splitext(file.filename)[1]
    file_path = os.path.join(directory, unique_filename)

    # Leer y guardar el archivo
    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    # Convertir el PDF a texto y guardarlo en un archivo TXT
    if extension == ".pdf":
        txt_directory = f"files/{user_id}/txt"
        if not os.path.exists(txt_directory):
            os.makedirs(txt_directory)
        txt_file_path = os.path.join(txt_directory, unique_filename.replace(".pdf", ".txt"))
        txt_content = convert_pdf_to_txt(file_path)
        with open(txt_file_path, "wb") as txt_file:
            txt_file.write(txt_content)

    # Crear la relación entre el usuario y el archivo en Neo4j
    with driver.session() as session:
        session.write_transaction(create_file_node, user_id, file.filename, unique_filename, extension)

    return {
        "user_id": user_id,
        "filename": unique_filename,
        "original_filename": file.filename,
        "status": "Archivo cargado correctamente."
    }

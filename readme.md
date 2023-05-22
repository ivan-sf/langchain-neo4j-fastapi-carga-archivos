# API de Preguntas y Respuestas

Esta API permite realizar preguntas y obtener respuestas basadas en archivos CSV y TXT. Utiliza Neo4j como base de datos para almacenar las preguntas y respuestas.

## Instalación

1. Clona este repositorio:

   ```bash
   git clone git@github.com:ivan-sf/langchain-neo4j-fastapi-carga-archivos.git` 

2.  Instala las dependencias:
    
    `pip install -r requirements.txt` 
    
3.  Configura las variables de entorno:
    
    Crea un archivo `.env` en el directorio raíz y define las siguientes variables:

    ```bash 
    OPENAI_API_KEY=<OPENAI_API_KEY>
    NEO4J_URI=<URI_DE_NEO4J>
    NEO4J_USER=<USUARIO_DE_NEO4J>
    NEO4J_PASSWORD=<CONTRASEÑA_DE_NEO4J>` 
    

## Uso

1.  Inicia el servidor de desarrollo:
       
    `uvicorn app:app --reload` 
    
2.  Accede a la documentación de la API en tu navegador:
        
    `http://localhost:8000/docs` 
    

## Endpoints

-   `POST /users/`: Crea un nuevo usuario.
-   `POST /upload_file/`: Carga un archivo CSV o TXT.
-   `POST /answer-csv`: Realiza una pregunta en un archivo CSV y obtiene la respuesta.
-   `POST /answer-txt`: Realiza una pregunta en un archivo TXT y obtiene la respuesta.
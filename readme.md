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
    

### Endpoints:

- `/:` Este endpoint responde con un saludo básico en formato JSON.

- `/api/v1/users/create:` Este endpoint recibe información de un usuario en formato JSON, crea un nuevo usuario en una base de datos y devuelve un mensaje de éxito.

- `/api/v1/files/upload_file/:` Este endpoint permite subir archivos al servidor. Recibe un ID de usuario y un archivo, lo guarda en una ubicación específica y guarda la información en una base de datos.

- `/api/v1/qa/answer-csv:` Este endpoint recibe una consulta en formato JSON sobre un archivo CSV. Lee el archivo, ejecuta la consulta utilizando un modelo de lenguaje y devuelve la respuesta.

- `/api/v1/qa/answer-yml:` Este endpoint recibe una consulta en formato JSON sobre un archivo YAML. Lee el archivo, busca la respuesta en base a la consulta utilizando un modelo de lenguaje y la estructura del YAML, y devuelve la respuesta.

- `/api/v1/qa/answer-pdf:` Este endpoint recibe una consulta en formato JSON sobre un archivo PDF. Lee el archivo, busca la respuesta en base a la consulta utilizando un modelo de lenguaje y devuelve la respuesta.

- `/api/v0/qa/answer-json:` Este endpoint recibe una pregunta en formato JSON sobre un objeto JSON. Busca la respuesta dentro del objeto utilizando un modelo de lenguaje y devuelve la respuesta.

- `/api/v0/qa/answer-txt:` Este endpoint recibe una consulta en formato JSON sobre un archivo de texto. Lee el archivo, busca la respuesta en base a la consulta utilizando un modelo de lenguaje y devuelve la respuesta.

- `/api/v1/neo/create-node:` Este endpoint crea un nuevo nodo en una base de datos Neo4j.

- `/api/v1/neo/create-relation:` Este endpoint crea una nueva relación entre nodos en una base de datos Neo4j.


### Websocket Endpoints:

- `/ws/:` Endpoint principal del websocket que acepta conexiones y responde con "¡Pong!" a los mensajes del cliente.

- `/ws/answer-csv:` Endpoint que recibe consultas en formato JSON sobre un archivo CSV, procesa las consultas y devuelve las respuestas en formato JSON.

- `/ws/answer-txt:` Endpoint que recibe consultas en formato JSON sobre un archivo de texto, procesa las consultas y devuelve las respuestas en formato JSON.

- `/ws/answer-pdf:` Endpoint que recibe consultas en formato JSON sobre un archivo PDF, procesa las consultas y devuelve las respuestas en formato JSON.


## JSON ejemplo

### Crear nodo
```
{
  "etiqueta": "Persona",
  "propiedades": {
    "nombre": "Juan",
    "edad": 30,
    "ciudad": "Madrid"
  }
} 
```
### Crear relacion
```
{
  "nodo1_etiqueta": "Persona",
  "nodo1_propiedades": {
    "nombre_persona": "Juan",
    "edad_persona": 30
  },
  "nodo2_etiqueta": "Empresa",
  "nodo2_propiedades": {
    "nombre_empresa": "Empresa A",
    "direccion_empresa": "Calle Principal"
  },
  "relacion_nombre": "TRABAJA_EN",
  "relacion_propiedades": {
    "puesto": "Desarrollador",
    "fecha_inicio": "2022-01-01"
  }
}
```

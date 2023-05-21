# API de carga de archivos y consultas - Documentación

La API de carga de archivos y consultas es una aplicación basada en FastAPI que permite a los usuarios cargar archivos CSV y realizar consultas sobre ellos utilizando un modelo de lenguaje natural. Los datos se almacenan en una base de datos Neo4j y se gestionan a través de diferentes endpoints.

## Configuración

Antes de comenzar a utilizar la API, asegúrate de configurar correctamente la conexión a la base de datos Neo4j. Esto se puede hacer a través de un archivo `.env`, donde se deben especificar los siguientes valores:

    OPENAI_API_KEY='API_KEY_OPENAI'
    NEO4J_URI='URI_NEO4J' 	
    NEO4J_USER='USER_NEO4J'
    NEO4J_PASSWORD='PW_NEO4J'

Asegúrate de ajustar los valores de la URI de Neo4j, el nombre de usuario y la contraseña según tu configuración.

## Endpoints disponibles

### Crear usuario

Este endpoint permite crear un nuevo usuario en la base de datos Neo4j.

- Ruta: `/users/`
- Método: `POST`
- Parámetros:
    - `user_id` (cadena): ID único del usuario.
    - `first_name` (cadena): Nombre del usuario.
    - `last_name` (cadena): Apellido del usuario.
- Respuesta exitosa:
    - Código de estado: 200 (OK)
    - Cuerpo de respuesta: `{"status": "Usuario creado correctamente."}`

### Cargar archivo CSV

Este endpoint permite cargar un archivo CSV y vincularlo a un usuario existente en la base de datos Neo4j.

- Ruta: `/upload_csv/`
- Método: `POST`
- Parámetros:
    - `user_id` (cadena): ID del usuario al que se vinculará el archivo.
    - `file` (archivo): Archivo CSV a cargar.
- Respuesta exitosa:
    - Código de estado: 200 (OK)
    - Cuerpo de respuesta: Información sobre el archivo cargado, incluyendo el `user_id`, `filename` (nombre único del archivo generado), `original_filename` (nombre original del archivo cargado) y `status` ("Archivo cargado correctamente.").

### Ejecutar consulta

Este endpoint permite ejecutar una consulta en un archivo CSV y guardar la pregunta y la respuesta en la base de datos Neo4j.

- Ruta: `/consultas`
- Método: `POST`
- Parámetros:
    - `query` (objeto JSON):
        - `question` (cadena): Pregunta a realizar.
    - `file_name` (cadena): Nombre único del archivo CSV en el que se ejecutará la consulta.
- Respuesta exitosa:
    - Código de estado: 200 (OK)
    - Cuerpo de respuesta: Información sobre la pregunta y la respuesta obtenida.

## Ejemplo de uso

### Crear usuario

    POST /users/
    { "user_id": "123", "first_name": "Juan", "last_name": "Pérez" }
    
### Cargar archivo CSV


    POST /upload_csv/?user_id=123
    Archivo a cargar: example.csv

### Ejecutar consulta

    POST /consultas
    { 
	    "query": 
		    {"question": "¿Cuál es el total de ventas?"},
		     "file_name": "example.csv" 
    }

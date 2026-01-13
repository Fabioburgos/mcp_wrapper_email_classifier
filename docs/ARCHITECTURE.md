# Documentación del Wrapper MCP para Email Classifier

## 1. Propósito del Wrapper (Adaptador MCP)

El propósito fundamental de este proyecto es actuar como un **adaptador (wrapper)** que conecta dos sistemas con arquitecturas diferentes:

1.  **Orquestador de Agentes (Moderno):** Un sistema basado en el Protocolo de Contexto del Modelo (MCP) y probablemente LangGraph. Este orquestador decide de forma inteligente cuándo y cómo procesar los emails que llegan.
2.  **Email Classifier (Legacy):** Un servicio existente (legacy) que se encarga de la lógica de negocio de clasificar un email. Este servicio se expone a través de una API HTTP RESTful.

El wrapper cumple las siguientes funciones:

-   **Expone una Herramienta MCP:** Presenta la funcionalidad del servicio legacy como una herramienta estándar (`tool`) dentro del ecosistema MCP. La herramienta se llama `process_business_email` y su definición (descripción, parámetros de entrada) está claramente especificada.
-   **Abstracción:** Oculta la complejidad de la comunicación con el servicio legacy. El orquestador no necesita saber que está llamando a una API HTTP; simplemente invoca una herramienta MCP.
-   **Traducción de Protocolos:** Actúa como un puente que traduce las llamadas del protocolo **JSON-RPC** (utilizado por MCP) a peticiones **HTTP POST** (utilizadas por el servicio `email_classifier`).

En resumen, el wrapper permite que un sistema moderno y modular (el orquestador) pueda reutilizar la lógica de un sistema más antiguo (el clasificador de emails) sin necesidad de modificar ninguno de los dos sistemas principales.

## 2. Transformación de JSON-RPC ↔ Proyecto

El flujo de transformación de datos es unidireccional en este caso: desde el orquestador hacia el servicio legacy.

1.  **Llamada JSON-RPC del Orquestador:** El orquestador envía una petición HTTP POST al endpoint `/mcp` del wrapper. El cuerpo de esta petición sigue el estándar JSON-RPC 2.0.

    ```json
    {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "process_business_email",
            "arguments": {
                "subscription_id": "sub-123-abc",
                "message_id": "AAMkADliN..."
            }
        },
        "id": 42
    }
    ```

2.  **Recepción y Parseo en el Wrapper (`handler.py`):**
    -   El `lambda_handler` en `handler.py` recibe esta petición.
    -   Identifica que el método es `tools/call`.
    -   Extrae el nombre de la herramienta (`process_business_email`) y sus argumentos (`subscription_id` y `message_id`) del objeto `params`.

3.  **Invocación de la Lógica del Proyecto (`tools/email_classifier.py`):**
    -   El handler llama a la función `invoke_email_classifier` dentro del módulo `tools.email_classifier`.
    -   A esta función se le pasan los valores `subscription_id` y `message_id` ya extraídos.

4.  **Transformación a HTTP POST:**
    -   La función `invoke_email_classifier` construye un nuevo payload (cuerpo de la petición), esta vez en formato JSON simple, para ser enviado al servicio legacy.
    -   Este payload contiene los mismos IDs que se recibieron originalmente.

    ```python
    # tools/email_classifier.py
    payload = {
        "subscription_id": subscription_id,
        "message_id": message_id
    }
    ```

5.  **Llamada al Servicio Legacy:**
    -   Utilizando la librería `httpx`, el wrapper realiza una petición `HTTP POST` a la URL del servicio `email_classifier` (obtenida de la variable de entorno `EMAIL_CLASSIFIER_URL`), enviando el `payload` recién creado.

6.  **Retorno de Respuesta:**
    -   El wrapper recibe la respuesta del servicio legacy.
    -   Finalmente, empaqueta este resultado en una respuesta JSON-RPC 2.0 y la devuelve al orquestador.

## 3. Configuración Necesaria

La configuración se divide en dos partes: la del propio wrapper y la del orquestador que lo va a consumir.

### Configuración del Wrapper

El wrapper necesita una única variable de entorno para funcionar:

-   `EMAIL_CLASSIFIER_URL`: La URL completa del endpoint del servicio legacy `email_classifier`.
    -   **Ejemplo:** `https://j3zu9ea3v7.execute-api.us-west-2.amazonaws.com/api/soma-email-classifier-2`

Esta variable se configura directamente en el entorno de ejecución (por ejemplo, en las variables de entorno de AWS Lambda).

### Configuración del Orquestador

El orquestador necesita saber dónde se encuentra el servidor MCP del wrapper. Esto se configura en su archivo `.env` o similar:

-   `MCP_SERVERS_CONFIG`: Un JSON que mapea nombres de servidores a sus configuraciones.
    -   **Ejemplo:**
        ```bash
        MCP_SERVERS_CONFIG={"classifier": {"transport": "streamable_http", "url": "https://<wrapper-url>/mcp"}}
        ```
    -   `classifier`: Es el nombre que el orquestador usará internamente para referirse a este wrapper.
    -   `<wrapper-url>`: Debe ser reemplazada por la URL pública del wrapper (por ejemplo, la Function URL de AWS Lambda).

## 4. Invocación desde el Orquestador

Para invocar la herramienta expuesta por el wrapper, el orquestador debe realizar una petición **HTTP POST** a la URL del wrapper con un cuerpo **JSON-RPC 2.0**.

-   **URL del Endpoint:** `https://<wrapper-url>/mcp`
-   **Método HTTP:** `POST`
-   **Headers:** `Content-Type: application/json`

### Cuerpo de la Petición (Request Body)

El cuerpo de la petición debe especificar:
-   `method`: `tools/call` para ejecutar una herramienta.
-   `params.name`: `process_business_email`, el nombre de la herramienta a invocar.
-   `params.arguments`: Un objeto con los parámetros definidos en el `inputSchema` de la herramienta:
    -   `subscription_id`: ID de la suscripción de Graph API, necesario para la autenticación y el contexto del tenant.
    -   `message_id`: ID del email específico que se debe procesar.

**Ejemplo completo de la invocación:**

```json
{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "process_business_email",
        "arguments": {
            "subscription_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
            "message_id": "AAMkADliNjEwNjYtZDA1Yy00M2YyLTg3Y2YtZGIzZTA4NzE4YzMwBGAAAAAAD3BSyLp3zQ7g6k4PLgUKcBwD3BSyLp3zQ7g6k4PLgUAAAAAABAAEAAA_3BSyLp3zQ7g6k4PLgUAAAAAABYAAAA="
        }
    },
    "id": 123
}
```

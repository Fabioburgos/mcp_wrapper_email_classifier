# MCP Wrapper - Email Classifier

Wrapper MCP que conecta el agente orquestador con el servicio email_classifier.

## ¿Qué hace?

Este wrapper actúa como **puente** entre dos servicios:

1. **Orquestador** (agente con LangGraph) - Decide cuándo procesar emails
2. **Email Classifier** (servicio legacy) - Procesa y clasifica emails

El wrapper:
- Expone una herramienta MCP llamada `process_business_email`
- Recibe requests JSON-RPC del orquestador
- Transforma el `message_id` en un payload simulado de Graph API
- Llama al email_classifier vía HTTP
- Retorna el resultado al orquestador

## Arquitectura

```
Orquestador (recibe webhook de Graph)
    ↓
    Decide invocar herramienta MCP
    ↓
MCP Wrapper (este servicio)
    ↓
    HTTP POST con payload simulado
    ↓
Email Classifier (procesa email)
```

## Configuración

### 1. Variables de Entorno del Wrapper

Configurar en AWS Lambda:

```bash
EMAIL_CLASSIFIER_URL=https://j3zu9ea3v7.execute-api.us-west-2.amazonaws.com/api/soma-email-classifier-2
```

### 2. Configuración del Orquestador

En el `.env` del orquestador:

```bash
MCP_SERVERS_CONFIG={"classifier": {"transport": "streamable_http", "url": "https://<wrapper-url>/mcp"}}
```

Reemplazar `<wrapper-url>` con la Function URL del wrapper.

## Despliegue

```bash
# 1. Build y deploy
make deploy

# 2. Configurar variable de entorno
aws lambda update-function-configuration \
  --function-name soma-mcp-wrapper-email-classifier-2 \
  --environment "Variables={EMAIL_CLASSIFIER_URL=https://j3zu9ea3v7.execute-api.us-west-2.amazonaws.com/api/soma-email-classifier-2}" \
  --region us-west-2

# 3. Obtener Function URL
aws lambda get-function-url-config \
  --function-name soma-mcp-wrapper-email-classifier-2 \
  --region us-west-2 \
  --query 'FunctionUrl' \
  --output text
```

## Estructura

```
mcp-wrapper-email-classifier/
├── handler.py                  # Lambda handler principal
├── mcp_server.py              # Servidor MCP
├── tools/
│   └── email_classifier.py    # Invocación HTTP al classifier
├── requirements.txt           # Dependencias
├── Dockerfile                 # Imagen Lambda
└── Makefile                   # Comandos de despliegue
```

## Flujo Completo

1. **Webhook de Graph API** → Orquestador
2. **Orquestador** analiza email y decide invocar `process_business_email`
3. **Orquestador** → HTTP POST a `/mcp` del wrapper
4. **Wrapper** recibe `message_id` y crea payload simulado:
   ```json
   {
     "value": [{
       "resource": "users/inbox/messages('AAMk...')",
       "resourceData": {"id": "AAMk..."}
     }]
   }
   ```
5. **Wrapper** → HTTP POST al email_classifier
6. **Email Classifier** procesa el email (clasifica, mueve carpetas, etc.)
7. **Wrapper** retorna resultado al orquestador

## Comandos Útiles

```bash
make help          # Ver todos los comandos
make deploy        # Despliegue completo
make logs          # Ver logs en tiempo real
make info          # Ver info de Lambda
```

## Notas Importantes

- El wrapper usa **httpx** para llamar al classifier (no boto3)
- Compatible con email_classifier desplegado en API Gateway
- El endpoint `/mcp` es usado por el orquestador
- Timeout configurado en 60 segundos por defecto
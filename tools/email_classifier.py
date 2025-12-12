import os
import json
import httpx
import logging

logger = logging.getLogger(__name__)

EMAIL_CLASSIFIER_URL = os.environ.get('EMAIL_CLASSIFIER_URL')

def get_tool_definition():
    """
    Retorna la definición de la herramienta MCP.
    """
    from mcp.types import Tool
    
    return Tool(
        name="process_business_email",
        description=(
            "Procesa y clasifica emails de negocios relacionados con usuarios y accesos.\n\n"
            
            "CASOS DE USO PRINCIPALES:\n"
            "• Solicitudes de alta/baja de usuarios\n"
            "• Desbloqueos de cuenta\n"
            "• Cambios de permisos o roles\n"
            "• Renovación de accesos VPN/sistemas\n"
            "• Creación de cuentas para nuevos empleados\n"
            "• Tickets de soporte relacionados con accesos\n\n"
            
            "PROCESO AUTOMÁTICO:\n"
            "1. Valida dominio autorizado y estado del email\n"
            "2. Clasifica usando IA (ALTA/BAJA/NO_CLASIFICABLE)\n"
            "3. Mueve a carpeta correspondiente\n"
            "4. Procesa según tipo detectado\n\n"
            
            "USAR CUANDO el email contiene:\n"
            "• Palabras: 'usuario', 'desbloqueo', 'acceso', 'crear', 'baja', 'alta'\n"
            "• Solicitudes de IT relacionadas con cuentas\n"
            "• Problemas de login o permisos\n\n"
            
            "NO USAR para:\n"
            "• Emails personales o saludos\n"
            "• Reportes de bugs de aplicaciones\n"
            "• Consultas generales sin relación a usuarios\n"
            "• Spam o marketing"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "subscription_id": {  # ← NUEVO
                    "type": "string",
                    "description": (
                        "OBLIGATORIO. ID de la suscripción de Microsoft Graph.\n"
                        "FUENTE: Usa el campo 'subscription_id' extraído de la notificación.\n"
                        "Este ID se usa para obtener las credenciales del cliente desde DynamoDB."
                    )
                },
                "message_id": {
                    "type": "string",
                    "description": (
                        "OBLIGATORIO. ID único del mensaje de Microsoft Graph.\n"
                        "FUENTE: Usa el campo 'message_id' del contexto.\n"
                        "Este ID identifica el email a procesar."
                    )
                }
            },
            "required": ["subscription_id", "message_id"]  # ← Ambos requeridos
        }
    )

async def invoke_email_classifier(subscription_id: str, message_id: str) -> dict:
    """
    Invoca el email_classifier vía HTTP.
    
    Args:
        subscription_id: ID de suscripción para obtener credenciales
        message_id: ID del mensaje a procesar
    """
    try:
        logger.info(f"Invocando Email Classifier: {EMAIL_CLASSIFIER_URL}")
        
        # Validaciones
        if not subscription_id:
            logger.error("subscription_id es None o vacío")
            return {
                'success': False,
                'error': 'subscription_id es requerido'
            }
        
        if not message_id:
            logger.error("message_id es None o vacío")
            return {
                'success': False,
                'error': 'message_id es requerido'
            }
        
        logger.info(f"Subscription ID: {subscription_id[:40]}...")
        logger.info(f"Message ID: {message_id[:20]}...")

        payload = {
            "subscription_id": subscription_id,  # ← NUEVO
            "value": [
                {
                    "resource": f"users/inbox/messages('{message_id}')",
                    "resourceData": {
                        "@odata.type": "#Microsoft.Graph.Message",
                        "id": message_id
                    },
                    "clientState": "orchestrator-invoked"
                }
            ]
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                EMAIL_CLASSIFIER_URL,
                json=payload,
                headers={'Content-Type': 'application/json'}
            )

        status_code = response.status_code
        logger.info(f"Response status: {status_code}")

        if status_code == 200:
            try:
                response_data = response.json()
                return {
                    'success': True,
                    'subscription_id': subscription_id,
                    'message_id': message_id,
                    'classifier_response': response_data
                }
            except json.JSONDecodeError:
                return {
                    'success': True,
                    'subscription_id': subscription_id,
                    'message_id': message_id,
                    'classifier_response': {'text': response.text}
                }
        else:
            try:
                error_data = response.json()
            except:
                error_data = {'error': response.text}

            return {
                'success': False,
                'subscription_id': subscription_id,
                'message_id': message_id,
                'error': error_data.get('error', f'HTTP {status_code}')
            }

    except httpx.TimeoutException:
        logger.error(f"Timeout invocando email_classifier después de 60s")
        return {
            'success': False,
            'subscription_id': subscription_id,
            'message_id': message_id,
            'error': 'Timeout después de 60 segundos'
        }
    except Exception as e:
        logger.error(f"Error invocando email_classifier: {e}", exc_info=True)
        return {
            'success': False,
            'subscription_id': subscription_id,
            'message_id': message_id,
            'error': str(e)
        }
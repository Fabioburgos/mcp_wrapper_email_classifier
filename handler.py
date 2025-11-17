# handler.py (WRAPPER)

import json
import logging
import asyncio
from tools.email_classifier import invoke_email_classifier, get_tool_definition

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """Handler MCP para invocación directa desde Lambda"""
    try:
        logger.info("=== MCP Wrapper Handler ===")
        
        method = event.get('method')
        params = event.get('params', {})
        msg_id = event.get('id', 1)
        
        logger.info(f"Method: {method}")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(handle_method(method, params, msg_id))
            return result
        finally:
            loop.close()
    
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32603, "message": str(e)}
        }


async def handle_method(method: str, params: dict, msg_id):
    """Maneja métodos MCP: tools/list y tools/call"""
    
    if method == "tools/list":
        logger.info("→ Listing tools")
        tool_def = get_tool_definition()
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": [{
                    "name": tool_def.name,
                    "description": tool_def.description,
                    "inputSchema": tool_def.inputSchema
                }]
            }
        }
    
    elif method == "tools/call":
        logger.info("→ Calling tool")
        tool_name = params.get('name')
        arguments = params.get('arguments', {})
        
        if tool_name != "process_business_email":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"Tool not found: {tool_name}"}
            }
        
        try:
            message_id = arguments.get('message_id')
            result = await invoke_email_classifier(message_id)
            
            if result["success"]:
                text_response = (
                    f"EMAIL PROCESADO EXITOSAMENTE\n\n"
                    f"Message ID: {message_id}\n\n"
                    f"El email ha sido:\n"
                    f"1. Validado\n2. Clasificado\n3. Movido a carpeta\n4. Procesado"
                )
            else:
                text_response = f"ERROR: {result.get('error', 'Unknown')}"
            
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"content": [{"type": "text", "text": text_response}]}
            }
        
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32603, "message": f"Tool execution failed: {str(e)}"}
            }
    
    else:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"}
        }
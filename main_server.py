# main_server.py - Servidor MCP Simplificado para Email (Proyecto GENIA)

import os
import json
import asyncio
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, EmailStr, Field
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno (principalmente para desarrollo local)
load_dotenv()

# --- Modelos Pydantic para la API ---
class EmailRecipient(BaseModel):
    email: EmailStr
    name: Optional[str] = None

class SMTPConfig(BaseModel):
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    use_tls: bool = True
    use_ssl: bool = False

class SendEmailParams(BaseModel):
    to_recipients: List[EmailRecipient]
    subject: str
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    from_address: Optional[EmailStr] = None
    from_name: Optional[str] = None
    smtp_config_override: Optional[SMTPConfig] = None
    # MODIFICACIÓN: Añadir campo para headers personalizados
    headers: Optional[Dict[str, str]] = None

class EmailRequest(BaseModel):
    role: str = Field(default="user", description="Rol del solicitante, para compatibilidad conceptual con MCP.")
    content: SendEmailParams
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadatos adicionales de la solicitud.")

class SuccessResponse(BaseModel):
    message: str
    details: Optional[Dict[str, Any]] = None

class ErrorDetail(BaseModel):
    type: str
    msg: str

class ErrorResponse(BaseModel):
    error: ErrorDetail

# --- Aplicación FastAPI ---
app = FastAPI(
    title="GENIA Simplified MCP Server - Email",
    description="Servidor simplificado para enviar correos electrónicos, siguiendo el patrón de los servidores MCP de OpenAI y Twilio.",
    version="1.0.0"
)

# --- Lógica de Envío de Correo ---
def _send_email_logic(params: SendEmailParams):
    logger.info(f"Iniciando lógica de envío de correo para: {params.to_recipients}")

    if params.smtp_config_override:
        smtp_cfg = params.smtp_config_override
        actual_from_address = params.from_address or smtp_cfg.username
        actual_from_name = params.from_name
        logger.info("Utilizando configuración SMTP proporcionada en la solicitud (override).")
    else:
        logger.info("Utilizando configuración SMTP por defecto del servidor (GENIA - Brevo).")
        smtp_cfg = SMTPConfig(
            host=os.getenv("SMTP_HOST_DEFAULT", "smtp-relay.brevo.com"),
            port=int(os.getenv("SMTP_PORT_DEFAULT", 587)),
            username=os.getenv("SMTP_USERNAME_DEFAULT"),
            password=os.getenv("SMTP_PASSWORD_DEFAULT"),
            use_tls=os.getenv("SMTP_USE_TLS_DEFAULT", "true").lower() == "true",
            use_ssl=os.getenv("SMTP_USE_SSL_DEFAULT", "false").lower() == "true"
        )
        # Usar el remitente que sabemos que funciona correctamente
        actual_from_address = params.from_address or os.getenv("DEFAULT_FROM_EMAIL", "mendezchristhian1@9055258.brevosend.com")
        actual_from_name = params.from_name or os.getenv("DEFAULT_FROM_NAME", "GENIA WhatsApp")

    if not smtp_cfg.host:
        logger.error("Host SMTP no configurado.")
        raise ValueError("Host SMTP no configurado.")
    if not smtp_cfg.username or not smtp_cfg.password:
        logger.error("Credenciales SMTP (usuario/contraseña) no configuradas o incompletas.")
        raise ValueError("Credenciales SMTP (usuario/contraseña) no configuradas.")
    if not actual_from_address:
        logger.error("Dirección de remitente no determinada.")
        raise ValueError("No se pudo determinar la dirección del remitente.")
    if not params.to_recipients:
        logger.error("No se especificaron destinatarios.")
        raise ValueError("No se especificaron destinatarios.")
    if not (params.body_text or params.body_html):
        logger.error("Se debe proporcionar body_text o body_html.")
        raise ValueError("Se debe proporcionar body_text o body_html.")

    msg = MIMEMultipart("alternative")
    if actual_from_name:
        msg["From"] = f"{actual_from_name} <{actual_from_address}>"
    else:
        msg["From"] = actual_from_address
    
    recipient_emails = [r.email for r in params.to_recipients]
    msg["To"] = ", ".join(recipient_emails)
    msg["Subject"] = params.subject

    # MODIFICACIÓN: Añadir headers personalizados si existen
    if params.headers:
        logger.info(f"Añadiendo headers personalizados: {params.headers}")
        for header_name, header_value in params.headers.items():
            msg[header_name] = header_value
    else:
        # Añadir headers predeterminados para mejorar entregabilidad
        default_headers = {
            "X-Priority": "1",
            "X-MSMail-Priority": "High",
            "Importance": "High"
        }
        logger.info(f"Añadiendo headers personalizados: {default_headers}")
        for header_name, header_value in default_headers.items():
            msg[header_name] = header_value

    if params.body_text:
        msg.attach(MIMEText(params.body_text, "plain"))
    if params.body_html:
        msg.attach(MIMEText(params.body_html, "html"))

    try:
        logger.info(f"Intentando enviar correo a: {recipient_emails} desde {actual_from_address} usando host {smtp_cfg.host}:{smtp_cfg.port}")
        
        server: smtplib.SMTP
        if smtp_cfg.use_ssl:
            logger.info("Conectando vía SMTP_SSL.")
            server = smtplib.SMTP_SSL(smtp_cfg.host, smtp_cfg.port)
        else:
            logger.info("Conectando vía SMTP.")
            server = smtplib.SMTP(smtp_cfg.host, smtp_cfg.port)
        
        server.set_debuglevel(1) # Habilitar debug para smtplib

        if smtp_cfg.use_tls and not smtp_cfg.use_ssl:
            logger.info("Ejecutando STARTTLS.")
            server.starttls()
        
        logger.info(f"Autenticando con usuario: {smtp_cfg.username}")
        server.login(smtp_cfg.username, smtp_cfg.password)
        
        logger.info("Enviando correo...")
        server.sendmail(actual_from_address, recipient_emails, msg.as_string())
        server.quit()
        logger.info("Correo enviado exitosamente y conexión cerrada.")
    except smtplib.SMTPException as e:
        logger.exception(f"Error SMTP específico al enviar correo: {e}")
        raise ValueError(f"Error SMTP: {str(e)}")
    except Exception as e:
        logger.exception(f"Error general al enviar correo: {e}")
        raise ValueError(f"Error general: {str(e)}")

# --- Endpoint FastAPI ---
@app.post("/mcp/send_email", response_model=SuccessResponse, responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def send_email_endpoint(request_data: EmailRequest = Body(...)):
    logger.info(f"Recibida solicitud para /mcp/send_email. Metadata: {request_data.metadata}")
    try:
        _send_email_logic(request_data.content)
        recipient_emails_str = ", ".join([r.email for r in request_data.content.to_recipients])
        return SuccessResponse(message=f"Correo enviado exitosamente a {recipient_emails_str}")
    except ValueError as ve:
        logger.warning(f"Error de validación o lógica de negocio en la solicitud: {ve}")
        raise HTTPException(status_code=400, detail={"error": {"type": "value_error", "msg": str(ve)}})
    except Exception as e:
        logger.exception("Error interno del servidor al procesar la solicitud de envío de correo.")
        return HTTPException(status_code=500, detail={"error": {"type": "internal_server_error", "msg": str(e)}})

@app.get("/")
async def root():
    return {"message": "Servidor MCP Simplificado para Email (GENIA) activo. Endpoint (POST) en /mcp/send_email"}

# Para ejecución con Render (o local con uvicorn main:app --reload)
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8004))
    logger.info(f"Iniciando servidor MCP de Email en http://0.0.0.0:{port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=bool(os.getenv("UVICORN_RELOAD", False)))

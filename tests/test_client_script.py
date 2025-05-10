# /home/ubuntu/project_genia_transfer/mcp_email_server/tests/test_client_script.py

import requests
import json
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env en el directorio del script de prueba o el directorio del servidor
# Esto es útil si el script se ejecuta desde su propio directorio o si el .env está en el dir del servidor
dotenv_path_script_dir = os.path.join(os.path.dirname(__file__), '.env')
dotenv_path_server_dir = os.path.join(os.path.dirname(__file__), '..', '.env') # Sube un nivel al directorio del servidor

if os.path.exists(dotenv_path_script_dir):
    load_dotenv(dotenv_path_script_dir)
    print(f"Cargado .env desde {dotenv_path_script_dir}")
elif os.path.exists(dotenv_path_server_dir):
    load_dotenv(dotenv_path_server_dir)
    print(f"Cargado .env desde {dotenv_path_server_dir}")
else:
    print("ADVERTENCIA: No se encontró el archivo .env en el directorio del script ni en el directorio del servidor.")

# URL del servidor MCP de Email (local)
SERVER_URL = "http://localhost:8004/mcp/send_email"

# Credenciales SMTP de prueba (simulando un usuario final)
# Estas deberían ser reemplazadas por credenciales de un servicio de email de prueba real si se quiere ver el correo llegar.
# Por ahora, usaremos las de Brevo de GENIA también para este caso, pero pasadas explícitamente.
TEST_SMTP_HOST = os.getenv("SMTP_HOST_DEFAULT", "smtp-relay.brevo.com")
TEST_SMTP_PORT = int(os.getenv("SMTP_PORT_DEFAULT", 587))
TEST_SMTP_USERNAME = os.getenv("SMTP_USERNAME_DEFAULT") # Tu email de Brevo
TEST_SMTP_PASSWORD = os.getenv("SMTP_PASSWORD_DEFAULT") # Tu clave SMTP de Brevo
TEST_SMTP_USE_TLS = os.getenv("SMTP_USE_TLS_DEFAULT", "true").lower() == "true"
TEST_SMTP_USE_SSL = os.getenv("SMTP_USE_SSL_DEFAULT", "false").lower() == "true"

# Dirección de correo para pruebas (asegúrate de que puedes recibir correos aquí)
TEST_RECIPIENT_EMAIL = "christhian.sanchez.contacto@gmail.com" # Cambia esto a un email de prueba real
TEST_SENDER_EMAIL_USER = TEST_SMTP_USERNAME # El remitente cuando se usan credenciales de usuario
# TEST_SENDER_EMAIL_GENIA = os.getenv("DEFAULT_FROM_EMAIL", "genia@example.com") # Remitente por defecto de GENIA
# Se cambió directamente en el payload para usar el remitente verificado de Brevo

def print_response(response):
    print(f"Status Code: {response.status_code}")
    try:
        print(f"Response JSON: {response.json()}")
    except requests.exceptions.JSONDecodeError:
        print(f"Response Text: {response.text}")
    print("---")

def test_send_email_default_credentials():
    print("Prueba 1: Enviando correo con credenciales por defecto del servidor (GENIA - Brevo)...")
    payload = {
        "role": "system_internal",
        "content": {
            "to_recipients": [
                {"email": TEST_RECIPIENT_EMAIL, "name": "Usuario de Prueba Genia"}
            ],
            "subject": "Prueba de Correo MCP (Credenciales por Defecto de GENIA)",
            "body_text": "Este es un correo de prueba enviado usando las credenciales por defecto del servidor MCP de email de GENIA.",
            "body_html": "<h1>Prueba de Correo MCP</h1><p>Este es un correo de prueba enviado usando las credenciales por defecto del servidor MCP de email de GENIA (Brevo).</p>",
            "from_address": "mendezchristhian1@gmail.com", # Remitente verificado para Brevo
            "from_name": "GENIA Plataforma"
        },
        "metadata": {"test_case": "default_credentials", "source": "test_client_script"}
    }
    try:
        response = requests.post(SERVER_URL, json=payload, timeout=30)
        print_response(response)
    except requests.exceptions.RequestException as e:
        print(f"Error en la solicitud: {e}")
        print("---")

def test_send_email_user_credentials():
    print("Prueba 2: Enviando correo con credenciales SMTP de usuario (override)...")
    
    if not TEST_SMTP_USERNAME or not TEST_SMTP_PASSWORD:
        print("SALTANDO PRUEBA 2: Las credenciales SMTP de prueba (TEST_SMTP_USERNAME/PASSWORD) no están configuradas en las variables de entorno.")
        print("Asegúrate de que SMTP_USERNAME_DEFAULT y SMTP_PASSWORD_DEFAULT estén configuradas si quieres probar este caso con las credenciales de Brevo.")
        print("---")
        return

    payload = {
        "role": "user_request",
        "content": {
            "to_recipients": [
                {"email": TEST_RECIPIENT_EMAIL, "name": "Usuario de Prueba SMTP Override"}
            ],
            "subject": "Prueba de Correo MCP (Credenciales de Usuario Override)",
            "body_text": "Este es un correo de prueba enviado usando credenciales SMTP específicas proporcionadas en la solicitud (override).",
            "body_html": "<h1>Prueba de Correo MCP</h1><p>Este es un correo de prueba enviado usando credenciales SMTP específicas proporcionadas en la solicitud (override).</p>",
            "from_address": TEST_SENDER_EMAIL_USER, # El email del usuario, que debe ser un remitente verificado si usa Brevo
            "from_name": "Usuario Específico",
            "smtp_config_override": {
                "host": TEST_SMTP_HOST,
                "port": TEST_SMTP_PORT,
                "username": TEST_SMTP_USERNAME,
                "password": TEST_SMTP_PASSWORD,
                "use_tls": TEST_SMTP_USE_TLS,
                "use_ssl": TEST_SMTP_USE_SSL
            }
        },
        "metadata": {"test_case": "user_credentials_override", "source": "test_client_script"}
    }
    try:
        response = requests.post(SERVER_URL, json=payload, timeout=30)
        print_response(response)
    except requests.exceptions.RequestException as e:
        print(f"Error en la solicitud: {e}")
        print("---")

if __name__ == "__main__":
    print(f"Iniciando pruebas contra el servidor MCP de Email en {SERVER_URL}\n")
    
    # Verificar que las variables de entorno para las credenciales por defecto de GENIA (Brevo) estén cargadas
    # Estas son necesarias para la Prueba 1 y como fallback para la Prueba 2 si se usan las mismas credenciales.
    if not os.getenv("SMTP_USERNAME_DEFAULT") or not os.getenv("SMTP_PASSWORD_DEFAULT"):
        print("ADVERTENCIA: Las variables de entorno SMTP_USERNAME_DEFAULT y SMTP_PASSWORD_DEFAULT no están configuradas.")
        print("La prueba con credenciales por defecto del servidor (Brevo) podría fallar o no enviar correos reales.")
        print("Asegúrate de que el archivo .env en el directorio del servidor esté correctamente configurado y que el servidor lo esté leyendo.")
        print("Si el servidor se ejecuta en un entorno donde .env no se carga automáticamente, estas variables deben estar disponibles en el entorno de ejecución del servidor.")
        print("---")
    
    test_send_email_default_credentials()
    test_send_email_user_credentials()
    print("Pruebas finalizadas.")


# /home/ubuntu/project_genia_transfer/mcp_email_server/tests/test_email_tool.py

import asyncio
import os
import unittest
from unittest.mock import patch, AsyncMock, MagicMock

from dotenv import load_dotenv
from mcp import Request, Response, Metadata # Assuming Role is part of mcp.Message or similar
from mcp.message.content import TextContent # Assuming TextContent is here
from mcp.message.message import Message, Role # Corrected import for Role

from pydantic import ValidationError

# Asegurarse de que el directorio raíz del proyecto esté en el PYTHONPATH
# para que se puedan importar módulos del proyecto como main_server
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main_server import send_email_tool, SendEmailParams # Importar la herramienta y el modelo

# Cargar variables de entorno para pruebas
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

class TestSendEmailTool(unittest.TestCase):

    def setUp(self):
        self.mock_context = MagicMock() # Mock para Context
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def run_async(self, coro):
        return self.loop.run_until_complete(coro)

    # --- Pruebas con Credenciales por Defecto del Servidor (GENIA - Brevo) ---
    @patch('main_server.smtplib.SMTP_SSL') # Mock SMTP_SSL para el caso de SSL
    @patch('main_server.smtplib.SMTP') # Mock SMTP para el caso estándar/TLS
    @patch.dict(os.environ, {
        "SMTP_HOST_DEFAULT": "smtp.genia-default.com",
        "SMTP_PORT_DEFAULT": "587",
        "SMTP_USERNAME_DEFAULT": "genia_user@default.com",
        "SMTP_PASSWORD_DEFAULT": "genia_default_pass",
        "DEFAULT_FROM_EMAIL": "noreply@genia.systems",
        "DEFAULT_FROM_NAME": "GENIA Systems"
    })
    def test_send_email_default_creds_text_only(self, mock_smtp_constructor, mock_smtp_ssl_constructor):
        mock_smtp_instance = mock_smtp_constructor.return_value.__enter__.return_value
        mock_smtp_instance.login = MagicMock()
        mock_smtp_instance.sendmail = MagicMock()
        mock_smtp_instance.starttls = MagicMock()
        mock_smtp_instance.ehlo = MagicMock()

        params = SendEmailParams(
            to_address="recipient@example.com",
            subject="Test Default Creds",
            body_text="This is a test using default server credentials."
            # No smtp_host, smtp_port, smtp_user, smtp_password proporcionados
        )
        request_mock = Request(method_name="send_email", metadata=Metadata.from_tool_input(params.model_dump(exclude_none=True)))
        
        response_message = self.run_async(send_email_tool(request_mock, self.mock_context, params))

        self.assertEqual(response_message.role, Role.ASSISTANT) # MCP standard role
        self.assertIsInstance(response_message.content[0], TextContent)
        self.assertIn("Correo enviado exitosamente a recipient@example.com", response_message.content[0].text)
        
        mock_smtp_constructor.assert_called_once_with(host="smtp.genia-default.com", port=587)
        mock_smtp_instance.login.assert_called_once_with("genia_user@default.com", "genia_default_pass")
        mock_smtp_instance.sendmail.assert_called_once()
        args, _ = mock_smtp_instance.sendmail.call_args
        self.assertEqual(args[0], "noreply@genia.systems")
        self.assertEqual(args[1], ["recipient@example.com"])
        self.assertIn("Subject: Test Default Creds", args[2])
        self.assertIn("From: GENIA Systems <noreply@genia.systems>", args[2])

    # --- Pruebas con Credenciales Proporcionadas por el Usuario ---
    @patch('main_server.smtplib.SMTP_SSL')
    @patch('main_server.smtplib.SMTP')
    def test_send_email_user_creds_html_only_tls(self, mock_smtp_constructor, mock_smtp_ssl_constructor):
        mock_smtp_instance = mock_smtp_constructor.return_value.__enter__.return_value
        mock_smtp_instance.login = MagicMock()
        mock_smtp_instance.sendmail = MagicMock()
        mock_smtp_instance.starttls = MagicMock()
        mock_smtp_instance.ehlo = MagicMock()

        params = SendEmailParams(
            to_address=["user_rec1@example.com", "user_rec2@example.com"],
            subject="Test User SMTP Creds",
            body_html="<h1>User SMTP Test</h1>",
            smtp_host="user.smtp.com",
            smtp_port=587,
            smtp_user="user@custom.com",
            smtp_password="user_pass_123",
            smtp_use_tls=True,
            smtp_use_ssl=False,
            from_address="sender@custom.com",
            from_name="Custom User Sender"
        )
        request_mock = Request(method_name="send_email", metadata=Metadata.from_tool_input(params.model_dump(exclude_none=True)))

        response_message = self.run_async(send_email_tool(request_mock, self.mock_context, params))

        self.assertEqual(response_message.role, Role.ASSISTANT)
        self.assertIsInstance(response_message.content[0], TextContent)
        self.assertIn("Correo enviado exitosamente a user_rec1@example.com, user_rec2@example.com", response_message.content[0].text)
        
        mock_smtp_constructor.assert_called_once_with(host="user.smtp.com", port=587)
        mock_smtp_instance.starttls.assert_called_once() # TLS se usa
        mock_smtp_ssl_constructor.assert_not_called() # SSL no se usa
        mock_smtp_instance.login.assert_called_once_with("user@custom.com", "user_pass_123")
        mock_smtp_instance.sendmail.assert_called_once()
        args, _ = mock_smtp_instance.sendmail.call_args
        self.assertEqual(args[0], "sender@custom.com")
        self.assertEqual(args[1], ["user_rec1@example.com", "user_rec2@example.com"])
        self.assertIn("Subject: Test User SMTP Creds", args[2])
        self.assertIn("From: Custom User Sender <sender@custom.com>", args[2])

    @patch('main_server.smtplib.SMTP_SSL')
    @patch('main_server.smtplib.SMTP')
    def test_send_email_user_creds_ssl_only(self, mock_smtp_constructor, mock_smtp_ssl_constructor):
        mock_smtp_ssl_instance = mock_smtp_ssl_constructor.return_value.__enter__.return_value
        mock_smtp_ssl_instance.login = MagicMock()
        mock_smtp_ssl_instance.sendmail = MagicMock()
        mock_smtp_ssl_instance.ehlo = MagicMock() # ehlo también se llama en SSL

        params = SendEmailParams(
            to_address="user_ssl@example.com",
            subject="Test User SMTP SSL",
            body_text="SSL Test",
            smtp_host="user.smtpssl.com",
            smtp_port=465,
            smtp_user="user_ssl@custom.com",
            smtp_password="user_ssl_pass",
            smtp_use_tls=False, # Importante: TLS debe ser False si SSL es True
            smtp_use_ssl=True,
            from_address="sender_ssl@custom.com"
        )
        request_mock = Request(method_name="send_email", metadata=Metadata.from_tool_input(params.model_dump(exclude_none=True)))

        response_message = self.run_async(send_email_tool(request_mock, self.mock_context, params))

        self.assertEqual(response_message.role, Role.ASSISTANT)
        mock_smtp_ssl_constructor.assert_called_once_with(host="user.smtpssl.com", port=465)
        mock_smtp_constructor.assert_not_called() # SMTP estándar no se usa
        mock_smtp_ssl_instance.login.assert_called_once_with("user_ssl@custom.com", "user_ssl_pass")
        mock_smtp_ssl_instance.sendmail.assert_called_once()

    # --- Pruebas de Casos de Error Existentes (adaptadas si es necesario) ---
    def test_send_email_missing_body(self):
        params = SendEmailParams(to_address="r@e.com", subject="S")
        request_mock = Request(method_name="send_email", metadata=Metadata.from_tool_input(params.model_dump(exclude_none=True)))
        response_message = self.run_async(send_email_tool(request_mock, self.mock_context, params))
        self.assertEqual(response_message.role, Role.ERROR)
        self.assertIn("Se debe proporcionar body_text o body_html", response_message.content[0].text)

    @patch.dict(os.environ, {
        "SMTP_HOST_DEFAULT": "smtp.genia-default.com",
        "SMTP_PORT_DEFAULT": "587",
        "SMTP_USERNAME_DEFAULT": "", # Credencial faltante
        "SMTP_PASSWORD_DEFAULT": ""
    })
    def test_send_email_missing_default_smtp_credentials(self):
        params = SendEmailParams(to_address="r@e.com", subject="S", body_text="B")
        request_mock = Request(method_name="send_email", metadata=Metadata.from_tool_input(params.model_dump(exclude_none=True)))
        response_message = self.run_async(send_email_tool(request_mock, self.mock_context, params))
        self.assertEqual(response_message.role, Role.ERROR)
        self.assertIn("Credenciales SMTP por defecto del servidor no configuradas", response_message.content[0].text)

    @patch('main_server.smtplib.SMTP')
    @patch.dict(os.environ, {
        "SMTP_HOST_DEFAULT": "test.smtp.com",
        "SMTP_PORT_DEFAULT": "587",
        "SMTP_USERNAME_DEFAULT": "testuser",
        "SMTP_PASSWORD_DEFAULT": "testpass"
    })
    def test_send_email_smtp_exception_default_creds(self, mock_smtp_constructor):
        mock_smtp_instance = mock_smtp_constructor.return_value.__enter__.return_value
        mock_smtp_instance.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Authentication credentials invalid")
        mock_smtp_instance.starttls = MagicMock()
        mock_smtp_instance.ehlo = MagicMock()

        params = SendEmailParams(to_address="r@e.com", subject="S", body_text="B")
        request_mock = Request(method_name="send_email", metadata=Metadata.from_tool_input(params.model_dump(exclude_none=True)))
        response_message = self.run_async(send_email_tool(request_mock, self.mock_context, params))

        self.assertEqual(response_message.role, Role.ERROR)
        self.assertIn("Error SMTP al enviar correo", response_message.content[0].text)
        self.assertIn("Authentication credentials invalid", response_message.content[0].text)

    @patch('main_server.smtplib.SMTP')
    def test_send_email_smtp_exception_user_creds(self, mock_smtp_constructor):
        mock_smtp_instance = mock_smtp_constructor.return_value.__enter__.return_value
        mock_smtp_instance.login.side_effect = smtplib.SMTPConnectError(500, "Connection refused")
        mock_smtp_instance.starttls = MagicMock()
        mock_smtp_instance.ehlo = MagicMock()

        params = SendEmailParams(
            to_address="r@e.com", subject="S", body_text="B",
            smtp_host="user.fail.com", smtp_port=587, smtp_user="u", smtp_password="p"
        )
        request_mock = Request(method_name="send_email", metadata=Metadata.from_tool_input(params.model_dump(exclude_none=True)))
        response_message = self.run_async(send_email_tool(request_mock, self.mock_context, params))

        self.assertEqual(response_message.role, Role.ERROR)
        self.assertIn("Error SMTP al enviar correo", response_message.content[0].text)
        self.assertIn("Connection refused", response_message.content[0].text)

    def test_pydantic_model_validation(self):
        with self.assertRaises(ValidationError):
            SendEmailParams(subject="Test Subject", body_text="This is a test email.")
        
        with self.assertRaises(ValidationError):
            SendEmailParams(to_address="r@e.com", body_text="This is a test email.")

if __name__ == '__main__':
    unittest.main()


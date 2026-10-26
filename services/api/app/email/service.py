"""
Email Service using Resend (Hito 6 - AUTH-03)

Envío de emails transaccionales para password reset.
"""

import resend
from ..config import settings

# Configurar Resend API key
resend.api_key = settings.resend_api_key


def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """
    Enviar email de reset de contraseña.

    Args:
        to_email: Email del destinatario
        reset_token: Token JWT de reset

    Returns:
        True si envío exitoso, False si error
    """
    reset_url = f"{settings.frontend_url}/reset-password?token={reset_token}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #f8f9fa; padding: 30px; border-radius: 10px;">
            <h1 style="color: #d97706; margin-bottom: 20px;">Restablecer Contraseña</h1>

            <p style="font-size: 16px; margin-bottom: 20px;">
                Has solicitado restablecer tu contraseña en Brasaland ATS.
            </p>

            <p style="font-size: 16px; margin-bottom: 20px;">
                Haz clic en el siguiente botón para crear una nueva contraseña:
            </p>

            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_url}"
                   style="background-color: #ea580c; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">
                    Restablecer Contraseña
                </a>
            </div>

            <p style="font-size: 14px; color: #666; margin-top: 30px;">
                Este enlace expirará en 30 minutos.
            </p>

            <p style="font-size: 14px; color: #666;">
                Si no solicitaste este cambio, puedes ignorar este email.
            </p>

            <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">

            <p style="font-size: 12px; color: #999; text-align: center;">
                Brasaland ATS · Sistema de Personas y Cultura
            </p>
        </div>
    </body>
    </html>
    """

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": to_email,
            "subject": "Restablecer contraseña - Brasaland ATS",
            "html": html_content
        })
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

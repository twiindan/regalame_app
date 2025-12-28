import os
import resend
from dotenv import load_dotenv

load_dotenv()

# Configuración de Resend
resend.api_key = os.getenv("RESEND_API_KEY")

async def send_email(subject: str, email_to: str, body_html: str):
    """
    Envía un email utilizando la API de Resend (HTTP).
    Ideal para entornos donde los puertos SMTP están bloqueados (como Railway).
    """
    # El remitente debe estar verificado en Resend o usar el dominio de onboarding
    sender = os.getenv("MAIL_FROM", "onboarding@resend.dev")
    
    try:
        # Nota: resend-python es síncrono, pero la llamada HTTP es muy rápida.
        params = {
            "from": sender,
            "to": [email_to],
            "subject": subject,
            "html": body_html,
        }
        
        email = resend.Emails.send(params)
        print(f"✅ Email enviado con Resend a {email_to}. ID: {email.get('id')}")
        return True
    except Exception as e:
        print(f"❌ Error enviando email con Resend a {email_to}: {e}")
        return False

async def send_invitation_email(email: str, group_name: str, group_code: str):
    """
    Wrapper para enviar la invitación al grupo.
    """
    html = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
        <h2 style="color: #4F46E5;">¡Invitación a Amigo Invisible!</h2>
        <p>Te han invitado a unirte al grupo <strong>{group_name}</strong> en Regálame.</p>
        <p>Tu código de acceso es:</p>
        <div style="background: #F3F4F6; padding: 15px; border-radius: 10px; text-align: center; margin: 20px 0;">
            <h1 style="color: #4F46E5; letter-spacing: 5px; margin: 0; font-family: monospace;">{group_code}</h1>
        </div>
        <p>Entra en <a href="https://regalame.app/">Regálame</a> y únete para participar.</p>
        <hr style="border: none; border-top: 1px solid #EEE; margin: 20px 0;">
        <p style="font-size: 12px; color: #666;">Si no esperabas este correo, puedes ignorarlo.</p>
    </div>
    """
    
    subject = f"Invitación al grupo {group_name} 🎁"
    await send_email(subject, email, html)

async def send_wishlist_share_email(to_email: str, owner_name: str, public_url: str):
    """
    Envía la lista de deseos a un destinatario.
    """
    subject = f"{owner_name} ha compartido su Lista de Deseos contigo 🎁"
    html = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; color: #333; line-height: 1.6;">
        <p>Hola,</p>
        <p><b>{owner_name}</b> ha creado una lista de regalos en Regálame y quiere compartirla contigo.</p>
        <p>Entra aquí para ver qué le gusta (y acertar seguro):</p>
        <p style="margin: 20px 0;">
            <a href="{public_url}" style="background-color: #EC4899; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">Ver Lista de Deseos</a>
        </p>
        <p style="font-size: 14px; color: #555;">O copia este enlace: <br> <a href="{public_url}">{public_url}</a></p>
        <br>
        <p>¡Un saludo!<br>El equipo de Regálame</p>
    </div>
    """
    await send_email(subject, to_email, html)
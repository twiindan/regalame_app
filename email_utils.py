import os
from dotenv import load_dotenv
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr

load_dotenv()

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME", ""),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD", ""),
    MAIL_FROM=os.getenv("MAIL_FROM", "noreply@regalame.app"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

async def send_invitation_email(email: EmailStr, group_name: str, group_code: str):
    html = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px;">
        <h2>¡Invitación a Amigo Invisible!</h2>
        <p>Te han invitado a unirte al grupo <strong>{group_name}</strong>.</p>
        <p>Tu código de acceso es:</p>
        <h1 style="color: #4F46E5; letter-spacing: 5px;">{group_code}</h1>
        <p>Entra en la aplicación y únete para participar.</p>
    </div>
    """

    message = MessageSchema(
        subject=f"Invitación al grupo {group_name}",
        recipients=[email],
        body=html,
        subtype=MessageType.html
    )

    fm = FastMail(conf)
    await fm.send_message(message)
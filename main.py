from contextlib import asynccontextmanager
from typing import Optional, List
import os
import uuid
from datetime import datetime, date

from fastapi import FastAPI, Depends, Request, Form, HTTPException, status, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlmodel import Session, select, or_

from database import create_db_and_tables, get_session
from models import User, Group, GroupMember, Wish, GroupExclusion, Message
from security import get_password_hash, verify_password
from services import scrape_metadata, generate_amazon_link, perform_draw, get_recommended_gifts
from email_utils import send_invitation_email

# --- Configuración Inicial ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ya no necesitamos create_db_and_tables() si usamos Alembic, 
    # pero no hace daño dejarlo para el setup inicial o tests.
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

# Configurar SessionMiddleware (usar variable de entorno para producción)
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-change-me")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Montar estáticos y plantillas
app.mount("/static", StaticFiles(directory="static", html=True), name="static")
templates = Jinja2Templates(directory="templates")

# --- Dependencias ---

def get_current_user(request: Request, session: Session = Depends(get_session)) -> Optional[User]:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return session.get(User, user_id)

def require_user(request: Request, user: Optional[User] = Depends(get_current_user)) -> User:
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required")
    return user

# --- SEO & Tech ---

@app.get("/robots.txt", response_class=HTMLResponse)
async def robots_txt():
    domain = os.getenv("DOMAIN_URL", "https://regalame.app")
    content = f"""User-agent: *
Disallow: /group/
Allow: /p/
Allow: /
Sitemap: {domain}/sitemap.xml
"""
    return HTMLResponse(content, media_type="text/plain")

@app.get("/sitemap.xml", response_class=HTMLResponse)
async def sitemap_xml(session: Session = Depends(get_session)):
    domain = os.getenv("DOMAIN_URL", "https://regalame.app")
    
    # Obtener usuarios recientes (limitado a 1000 para MVP)
    users = session.exec(select(User).limit(1000)).all()
    
    urls = []
    # Home
    urls.append(f"""
    <url>
        <loc>{domain}/</loc>
        <changefreq>daily</changefreq>
        <priority>1.0</priority>
    </url>
    """)
    
    # Perfiles públicos
    for user in users:
        urls.append(f"""
        <url>
            <loc>{domain}/p/{user.id}</loc>
            <changefreq>weekly</changefreq>
            <priority>0.8</priority>
        </url>
        """)
        
    sitemap_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    {"".join(urls)}
</urlset>
"""
    return HTMLResponse(sitemap_content, media_type="application/xml")

# --- Rutas de Auth ---

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, user: Optional[User] = Depends(get_current_user)):
    if user:
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse(request, "index.html", {"user": user})

@app.post("/register", response_class=HTMLResponse)
async def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    name: str = Form(...),
    session: Session = Depends(get_session)
):
    # Verificar si existe
    existing_user = session.exec(select(User).where(User.email == email)).first()
    if existing_user:
        return templates.TemplateResponse(request, "partials/registration_error.html", {"error": "El email ya está registrado"})
    
    hashed_pwd = get_password_hash(password)
    new_user = User(email=email, hashed_password=hashed_pwd, name=name)
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    
    # Login automático
    request.session["user_id"] = new_user.id
    
    # HTMX Redirect para evitar nesting
    from fastapi import Response
    response = Response(status_code=200)
    response.headers["HX-Redirect"] = "/dashboard"
    return response

@app.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session)
):
    user = session.exec(select(User).where(User.email == email)).first()
    if not user or not verify_password(password, user.hashed_password):
         return templates.TemplateResponse(request, "partials/login_error.html", {"error": "Credenciales inválidas"})
    
    request.session["user_id"] = user.id
    
    # HTMX Redirect para evitar nesting
    from fastapi import Response
    response = Response(status_code=200)
    response.headers["HX-Redirect"] = "/dashboard"
    return response

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request, 
    user: User = Depends(require_user),
    session: Session = Depends(get_session)
):
    recommendations = get_recommended_gifts(3)
    return templates.TemplateResponse(request, "dashboard.html", {
        "user": user, 
        "recommendations": recommendations
    })

# --- Rutas de Grupos ---

@app.post("/create-group", response_class=HTMLResponse)
async def create_group(
    request: Request,
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    emails: str = Form(None),
    budget: str = Form(None),
    event_date: str = Form(None),
    user: User = Depends(require_user),
    session: Session = Depends(get_session)
):
    code = str(uuid.uuid4())[:8].upper()
    
    date_obj = None
    if event_date:
        try:
            date_obj = datetime.strptime(event_date, "%Y-%m-%d").date()
        except ValueError:
            pass 

    new_group = Group(
        name=name, 
        code=code, 
        admin_id=user.id,
        budget=budget,
        event_date=date_obj
    )
    session.add(new_group)
    session.commit()
    session.refresh(new_group)
    
    member = GroupMember(group_id=new_group.id, user_id=user.id)
    session.add(member)
    session.commit()
    
    if emails:
        email_list = [e.strip() for e in emails.split(",") if e.strip()]
        for email in email_list:
            background_tasks.add_task(send_invitation_email, email, new_group.name, new_group.code)
            
    return RedirectResponse(url=f"/group/{new_group.id}", status_code=303)

@app.post("/group/{group_id}/update-logistics", response_class=HTMLResponse)
async def update_group_logistics(
    request: Request,
    group_id: int,
    budget: str = Form(None),
    event_date: str = Form(None),
    user: User = Depends(require_user),
    session: Session = Depends(get_session)
):
    group = session.get(Group, group_id)
    if not group or group.admin_id != user.id:
        return HTMLResponse("Forbidden", status_code=403)

    group.budget = budget
    if event_date:
        try:
            group.event_date = datetime.strptime(event_date, "%Y-%m-%d").date()
        except ValueError:
            pass
    else:
        group.event_date = None
        
    session.add(group)
    session.commit()
    session.refresh(group)
    
    return RedirectResponse(url=f"/group/{group_id}", status_code=303)

@app.get("/join/{code}", response_class=HTMLResponse)
async def join_page(code: str, request: Request, user: Optional[User] = Depends(get_current_user)):
    if not user:
        # Guardar intención y redirigir a login (simplificado)
        return templates.TemplateResponse(request, "join.html", {"code": code, "user": None, "message": "Por favor, inicia sesión para unirte."})
    return templates.TemplateResponse(request, "join.html", {"code": code, "user": user})

@app.post("/join/{code}", response_class=HTMLResponse)
async def join_action(
    request: Request, 
    code: str, 
    user: User = Depends(require_user),
    session: Session = Depends(get_session)
):
    group = session.exec(select(Group).where(Group.code == code)).first()
    if not group:
        return templates.TemplateResponse(request, "partials/join_error.html", {"error": "Código inválido"})
    
    # Verificar si ya es miembro
    if any(m.id == user.id for m in group.members):
        return RedirectResponse(url=f"/group/{group.id}", status_code=303)
        
    new_member = GroupMember(group_id=group.id, user_id=user.id)
    session.add(new_member)
    session.commit()
    
    return RedirectResponse(url=f"/group/{group.id}", status_code=303)

@app.get("/group/{group_id}", response_class=HTMLResponse)
async def group_dashboard(
    request: Request,
    group_id: int,
    user: User = Depends(require_user),
    session: Session = Depends(get_session)
):
    group = session.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=404)
    
    # Verificar membresía
    membership = session.exec(select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == user.id)).first()
    if not membership:
        raise HTTPException(status_code=403, detail="No eres miembro")
    
    giftee = None
    giftee_wishes = []
    
    if membership.giftee_id:
        giftee = session.get(User, membership.giftee_id)
        giftee_wishes = giftee.wishes if giftee else []
    
    # Buscar quién es mi Santa (quién me tiene asignado como giftee)
    my_santa_member = session.exec(select(GroupMember).where(
        GroupMember.group_id == group_id, 
        GroupMember.giftee_id == user.id
    )).first()
    my_santa_id = my_santa_member.user_id if my_santa_member else None
        
    return templates.TemplateResponse(request, "group.html", {
        "user": user,
        "group": group,
        "giftee": giftee,
        "giftee_wishes": giftee_wishes,
        "my_santa_id": my_santa_id,
        "is_admin": group.admin_id == user.id
    })

@app.post("/group/{group_id}/invite", response_class=HTMLResponse)
async def invite_to_group(
    request: Request,
    group_id: int,
    background_tasks: BackgroundTasks,
    emails: str = Form(...),
    user: User = Depends(require_user),
    session: Session = Depends(get_session)
):
    group = session.get(Group, group_id)
    if not group: 
        return HTMLResponse("Grupo no encontrado", status_code=404)
        
    email_list = [e.strip() for e in emails.split(",") if e.strip()]
    for email in email_list:
        background_tasks.add_task(send_invitation_email, email, group.name, group.code)
        
    return templates.TemplateResponse(request, "partials/invitation_sent_message.html", {"count": len(email_list)})

@app.post("/group/{group_id}/draw", response_class=HTMLResponse)
async def draw_group(
    request: Request,
    group_id: int,
    user: User = Depends(require_user),
    session: Session = Depends(get_session)
):
    group = session.get(Group, group_id)
    if group.admin_id != user.id:
        raise HTTPException(status_code=403, detail="Solo el admin puede sortear")
        
    try:
        perform_draw(group_id, session)
        return RedirectResponse(url=f"/group/{group_id}", status_code=303)
    except ValueError as e:
        return HTMLResponse(f"<div class='text-red-500 bg-red-900/20 p-4 rounded-lg mt-4'>{str(e)}</div>")

# --- Rutas de Exclusiones (Vetos) ---

@app.post("/group/{group_id}/exclusions", response_class=HTMLResponse)
async def add_exclusion(
    request: Request,
    group_id: int,
    giver_id: int = Form(...),
    forbidden_id: int = Form(...),
    user: User = Depends(require_user),
    session: Session = Depends(get_session)
):
    group = session.get(Group, group_id)
    if not group or group.admin_id != user.id:
        return HTMLResponse("Acceso denegado", status_code=403)
        
    if giver_id == forbidden_id:
        return HTMLResponse("No tiene sentido vetarse a uno mismo", status_code=400)
        
    existing = session.exec(select(GroupExclusion).where(
        GroupExclusion.group_id == group_id,
        GroupExclusion.giver_id == giver_id,
        GroupExclusion.forbidden_giftee_id == forbidden_id
    )).first()
    
    if not existing:
        new_exclusion = GroupExclusion(group_id=group_id, giver_id=giver_id, forbidden_giftee_id=forbidden_id)
        session.add(new_exclusion)
        session.commit()
    
    session.expire(group)
    return templates.TemplateResponse(request, "partials/exclusion_list.html", {"group": group})

@app.delete("/group/{group_id}/exclusions/{exclusion_id}", response_class=HTMLResponse)
async def delete_exclusion(
    request: Request,
    group_id: int,
    exclusion_id: int,
    user: User = Depends(require_user),
    session: Session = Depends(get_session)
):
    group = session.get(Group, group_id)
    if not group or group.admin_id != user.id:
        return HTMLResponse("Acceso denegado", status_code=403)
        
    exclusion = session.get(GroupExclusion, exclusion_id)
    if exclusion:
        session.delete(exclusion)
        session.commit()
        
    return HTMLResponse("") 

# --- Rutas de Deseos ---

@app.post("/wishes", response_class=HTMLResponse)
async def add_wish(
    request: Request,
    content: str = Form(...),
    user: User = Depends(require_user),
    session: Session = Depends(get_session)
):
    content = content.strip()
    is_url = content.startswith("http://") or content.startswith("https://")
    
    new_wish = Wish(user_id=user.id, title=content) 
    
    if is_url:
        metadata = scrape_metadata(content)
        new_wish.title = metadata["title"]
        new_wish.image_url = metadata["image_url"]
        new_wish.url = generate_amazon_link(content)
    else:
        new_wish.url = generate_amazon_link(content)
    
    session.add(new_wish)
    session.commit()
    session.refresh(new_wish)
    
    return templates.TemplateResponse(request, "partials/wish_item.html", {"wish": new_wish, "user": user, "readonly": False})

@app.post("/wishes/{wish_id}/toggle-reserve", response_class=HTMLResponse)
async def toggle_reserve(
    request: Request,
    wish_id: int,
    user: User = Depends(require_user),
    session: Session = Depends(get_session)
):
    wish = session.get(Wish, wish_id)
    if not wish:
        return HTMLResponse("No encontrado", status_code=404)
    
    if wish.user_id == user.id:
        return HTMLResponse("No puedes reservar tu propio deseo", status_code=400)
    
    if wish.reserved_by_id == user.id:
        wish.reserved_by_id = None
    elif wish.reserved_by_id is None:
        wish.reserved_by_id = user.id
    else:
        return HTMLResponse("Ya reservado por otro", status_code=400)
        
    session.add(wish)
    session.commit()
    session.refresh(wish)
    
    return templates.TemplateResponse(request, "partials/reserve_button.html", {"wish": wish, "user": user})

@app.delete("/wishes/{wish_id}")
async def delete_wish(
    wish_id: int,
    user: User = Depends(require_user),
    session: Session = Depends(get_session)
):
    wish = session.get(Wish, wish_id)
    if not wish:
        return HTMLResponse(status_code=404)
    if wish.user_id != user.id:
        return HTMLResponse("Forbidden", status_code=403)
    
    session.delete(wish)
    session.commit()
    
    return HTMLResponse("")

# --- Perfil Público ---

@app.get("/p/{user_id}", response_class=HTMLResponse)
async def public_profile(
    request: Request,
    user_id: int,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user)
):
    profile_user = session.get(User, user_id)
    if not profile_user:
        raise HTTPException(status_code=404)
        
    return templates.TemplateResponse(request, "public_profile.html", {
        "profile_user": profile_user,
        "current_user": current_user
    })

# --- Chat Anónimo ---

@app.get("/group/{group_id}/chat/{other_user_id}", response_class=HTMLResponse)
async def get_chat(
    request: Request,
    group_id: int,
    other_user_id: int,
    user: User = Depends(require_user),
    session: Session = Depends(get_session)
):
    # Verificar membresía
    if not session.exec(select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == user.id)).first():
        return HTMLResponse("Acceso denegado", status_code=403)

    other_user = session.get(User, other_user_id)
    if not other_user:
        return HTMLResponse("Usuario no encontrado", status_code=404)

    # Lógica de Anonimato
    # 1. ¿Soy yo el Santa de él? (Yo veo su nombre, él ve "Santa")
    am_i_santa = session.exec(select(GroupMember).where(
        GroupMember.group_id == group_id,
        GroupMember.user_id == user.id,
        GroupMember.giftee_id == other_user_id
    )).first() is not None

    # 2. ¿Es él mi Santa? (Yo veo "Santa", él ve mi nombre)
    is_he_santa = session.exec(select(GroupMember).where(
        GroupMember.group_id == group_id,
        GroupMember.user_id == other_user_id,
        GroupMember.giftee_id == user.id
    )).first() is not None

    messages = session.exec(
        select(Message)
        .where(
            Message.group_id == group_id,
            or_(
                (Message.sender_id == user.id) & (Message.receiver_id == other_user_id),
                (Message.sender_id == other_user_id) & (Message.receiver_id == user.id)
            )
        )
        .order_by(Message.timestamp)
    ).all()

    return templates.TemplateResponse(request, "partials/chat_box.html", {
        "group_id": group_id,
        "current_user": user,
        "other_user": other_user,
        "messages": messages,
        "am_i_santa": am_i_santa,
        "is_he_santa": is_he_santa
    })

@app.post("/group/{group_id}/chat/{other_user_id}", response_class=HTMLResponse)
async def send_chat_message(
    request: Request,
    group_id: int,
    other_user_id: int,
    content: str = Form(...),
    user: User = Depends(require_user),
    session: Session = Depends(get_session)
):
    if not content.strip():
        # Retornar vacío o error si está vacío, pero para HTMX mejor no hacer nada o devolver el chat
        pass
    
    new_msg = Message(
        group_id=group_id,
        sender_id=user.id,
        receiver_id=other_user_id,
        content=content
    )
    session.add(new_msg)
    session.commit()
    
    # Redirigir al GET para renderizar la caja actualizada
    # (Podemos llamar a la función directamente pero es mejor un redirect interno o re-render)
    # Para simplicidad y reusar lógica, llamamos a la lógica de GET (o hacemos redirect HTMX)
    
    # Opción A: Redirect (HTMX lo sigue y carga el contenido en el target)
    from fastapi import Response
    response = Response(status_code=200)
    response.headers["HX-Trigger"] = "newMessage" # Opcional: para scrollear
    
    # Re-renderizamos llamando al template directamente con los datos actualizados
    # Esto ahorra un roundtrip de red
    return await get_chat(request, group_id, other_user_id, user, session)
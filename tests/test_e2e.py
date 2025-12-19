import re
import time
from playwright.sync_api import Page, Browser, expect

# Helper para emails únicos
def generate_unique_email(prefix="user"):
    return f"{prefix}_{int(time.time())}_{id(prefix)}@example.com"

def test_wishlist_and_logistics(page: Page):
    # 1. Registro
    page.goto("http://localhost:8000/")
    page.get_by_text("Registrarse").click()
    page.locator("#register-form input[name='name']").fill("Tester Logística")
    page.locator("#register-form input[name='email']").fill(generate_unique_email("logis"))
    page.locator("#register-form input[name='password']").fill("pass")
    page.locator("#register-form button[type='submit']").click()
    
    # Esperar a estar en dashboard
    page.wait_for_url(re.compile(r".*/dashboard"))
    
    # 2. Crear Grupo con Logística
    page.locator("input[name='name']").first.fill("Grupo Completo")
    page.locator("input[name='budget']").fill("50€")
    page.locator("input[name='event_date']").fill("2024-12-25")
    page.locator("button", has_text="Crear Grupo").click()
    
    # Esperar redirección al grupo
    page.wait_for_url(re.compile(r".*/group/\d+"))
    
    # Verificar que aparecen los "pills" de logística
    expect(page.locator("text=50€")).to_be_visible()
    
    # Volver al dashboard
    page.goto("http://localhost:8000/dashboard")
    
    # 3. Añadir Deseos
    # Texto
    page.locator("input[name='content']").fill("Calcetines Molones")
    page.locator("button", has_text="Añadir").click()
    expect(page.locator("text=Calcetines Molones")).to_be_visible()
    
    # 4. Borrar Deseo
    card = page.locator(".glass-panel", has_text="Calcetines Molones")
    page.once("dialog", lambda dialog: dialog.accept())
    card.locator("button", has_text="Eliminar").click()
    
    # Verificar que desaparece
    expect(page.locator("text=Calcetines Molones")).not_to_be_visible()


def test_multi_user_draw_flow(browser: Browser):
    # --- CONTEXTO ADMIN ---
    context_admin = browser.new_context()
    page_admin = context_admin.new_page()
    
    page_admin.goto("http://localhost:8000/")
    page_admin.get_by_text("Registrarse").click()
    page_admin.locator("#register-form input[name='name']").fill("Admin User")
    page_admin.locator("#register-form input[name='email']").fill(generate_unique_email("admin"))
    page_admin.locator("#register-form input[name='password']").fill("pass")
    page_admin.locator("#register-form button[type='submit']").click()
    
    page_admin.wait_for_url(re.compile(r".*/dashboard"))
    
    # Crear Grupo
    page_admin.locator("input[name='name']").first.fill("Sorteo Final")
    page_admin.locator("button", has_text="Crear Grupo").click()
    
    page_admin.wait_for_url(re.compile(r".*/group/\d+"))
    
    # Obtener Código
    code_locator = page_admin.locator(".font-mono.tracking-wider")
    expect(code_locator).to_be_visible()
    group_code = code_locator.inner_text().strip()
    
    # --- CONTEXTO MEMBER (User B) ---
    context_member = browser.new_context()
    page_member = context_member.new_page()
    
    page_member.goto("http://localhost:8000/")
    page_member.get_by_text("Registrarse").click()
    page_member.locator("#register-form input[name='name']").fill("Member User")
    page_member.locator("#register-form input[name='email']").fill(generate_unique_email("member"))
    page_member.locator("#register-form input[name='password']").fill("pass")
    page_member.locator("#register-form button[type='submit']").click()
    
    page_member.wait_for_url(re.compile(r".*/dashboard"))
    
    # Unirse con el código
    page_member.locator("input[name='code']").fill(group_code)
    page_member.locator("button i.ph-arrow-right").click() 
    
    # Confirmar unión
    page_member.wait_for_url(re.compile(r".*/join/.*"))
    page_member.locator("button", has_text="Confirmar").click()
    
    # Verificar que está en el grupo
    page_member.wait_for_url(re.compile(r".*/group/\d+"))
    expect(page_member.locator("text=Sorteo Final")).to_be_visible()
    
    # --- VUELTA A ADMIN ---
    page_admin.reload()
    expect(page_admin.locator("text=Member User")).to_be_visible()
    
    # REALIZAR SORTEO
    page_admin.locator("button", has_text="Realizar Sorteo").click()
    
    # Verificar resultados
    expect(page_admin.locator("h2", has_text="Tienes que regalar a:")).to_be_visible()
    
    page_member.reload()
    expect(page_member.locator("h2", has_text="Tienes que regalar a:")).to_be_visible()
    
    context_admin.close()
    context_member.close()

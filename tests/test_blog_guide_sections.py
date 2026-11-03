def test_post_with_guide_renders_sections_and_headings(client):
    from blog_config import BLOG_POSTS
    BLOG_POSTS.append({
        "slug": "guide-fixture",
        "title": "Guía fixture",
        "description": "Post de prueba",
        "guide": [
            {"heading": "Sección uno", "paragraphs": ["Párrafo uno.", "Párrafo dos."]},
            {"heading": "Sección dos", "paragraphs": ["Otro párrafo."]},
        ],
        "hero_image": None,
    })
    try:
        response = client.get("/blog/guide-fixture")
        assert response.status_code == 200
        body = response.text
        assert "Sección uno" in body
        assert "Párrafo dos." in body
        assert "Sección dos" in body
    finally:
        BLOG_POSTS.pop()

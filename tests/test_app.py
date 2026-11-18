import re
from pathlib import Path
import pytest
from app import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-which-is-not-for-production',
        'DATABASE_URL': f'sqlite:///{tmp_path / "test.db"}',
        'ADMIN_PASSWORD': 'correct-horse-battery-staple',
        'PUZZLE_ANSWER': '0417',
    })
    return app.test_client()


def test_home_and_health(client):
    assert client.get('/').status_code == 200
    assert '異常檔案'.encode() in client.get('/').data
    assert client.get('/health').json == {'status': 'ok'}


def test_posts_and_lookup(client):
    response = client.get('/api/posts')
    assert response.status_code == 200
    assert len(response.json['posts']) == 3
    assert client.get('/api/posts/first-record').status_code == 200
    assert client.get('/api/posts/not-real').status_code == 404


def test_puzzle_validation(client):
    def guess(answer):
        return client.post('/api/puzzle/verify', json={'answer': answer})
    assert guess('0417').json['success'] is True
    assert guess('0000').json['success'] is False
    assert guess('abcd').status_code == 400
    assert client.post('/api/puzzle/verify', data='0417').status_code == 415
    assert client.get('/api/puzzle/verify').status_code == 405


def test_admin_permissions_and_csrf(client):
    assert client.get('/admin/dashboard').status_code == 302
    res = client.get('/admin')
    csrf = re.search(r'name="csrf" value="([^"]+)"', res.data.decode()).group(1)
    invalid = client.post('/admin', data={'password': 'incorrect', 'csrf': csrf})
    assert '密碼錯誤'.encode() in invalid.data
    valid = client.post('/admin', data={'password': 'correct-horse-battery-staple', 'csrf': csrf})
    assert valid.status_code == 302
    assert valid.headers['Location'].endswith('/admin/dashboard')
    assert client.get('/admin/dashboard').status_code == 200
    assert client.post('/admin/posts/new', data={}).status_code == 400


def test_admin_crud(client):
    res = client.get('/admin')
    csrf = re.search(r'name="csrf" value="([^"]+)"', res.data.decode()).group(1)
    client.post('/admin', data={'password': 'correct-horse-battery-staple', 'csrf': csrf})
    csrf = re.search(r'name="csrf" value="([^"]+)"', client.get('/admin/dashboard').data.decode()).group(1)
    content = {'csrf': csrf, 'slug': 'test-post', 'title': '測試文章', 'category': '生活',
               'excerpt': '測試摘要', 'content': '<script>alert(1)</script>', 'created_at': '2026-11-18',
               'published': 'on'}
    res = client.post('/admin/posts/new', data=content)
    assert res.status_code == 302
    items = client.get('/api/posts').json['posts']
    post = next(p for p in items if p['slug'] == 'test-post')
    assert post['title'] == '測試文章'
    # User-generated content is returned as text, then inserted with textContent by frontend.
    assert post['content'] == '<script>alert(1)</script>'
    res = client.post('/admin/posts/new', data={**content, 'slug': 'BAD SLUG'})
    assert res.status_code == 400
    res = client.post(f"/admin/posts/{post['id']}/delete", data={'csrf': csrf})
    assert res.status_code == 302
    assert client.get('/api/posts/test-post').status_code == 404


def test_security_headers(client):
    response = client.get('/')
    assert "script-src 'self'" in response.headers['Content-Security-Policy']
    assert response.headers['X-Frame-Options'] == 'DENY'

import pytest 
from httpx import AsyncClient 
from tests.conftest import auth_header , create_test_user , login_user

@pytest.mark.anyio
async def test_get_posts_empty(client:AsyncClient):
    response = await client.get("/api/posts")

    assert response.status_code == 200
    data = response.json()
    assert data["posts"] ==[]
    assert data["total"] ==0
    assert data["has_more"] is False 

@pytest.mark.anyio
async def test_get_post_not_found(client:AsyncClient):
    response = await client.get("/api/posts/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Post Not found"

@pytest.mark.anyio
async def test_create_post_success(client:AsyncClient):
    user = await create_test_user(client)
    token = await login_user(client)
    headers = auth_header(token)

    response = await client.post(
        "/api/posts",
        json={"title":"My first post","content":"This is the content of test post"},
        headers=headers,
        )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "My first post"
    assert data["content"] == "This is the content of test post"
    assert data["user_id"] == user["id"]
    assert "id" in data 
    assert "date_posted" in data
    assert data["author"]["username"] == "testuserone"

@pytest.mark.anyio
async def test_create_post_unauthorized_user(client:AsyncClient):
    response = await client.post(
        "/api/posts",
        json={
            "title":"Test Post",
            "content":"Test content"
        },
)

    assert response.status_code == 401
    assert response.json()["detail"]=="Not authenticated"

@pytest.mark.anyio
async def test_update_post_success(
    client : AsyncClient
):
    await create_test_user(client)
    token = await login_user(client)
    headers = auth_header(token)

    response = await client.post(
        "/api/posts",
        json={"title":"Test POST","content": "Original content"},
        headers= headers,
    )

    post_id = response.json()["id"]

    response = await client.patch(
        f"/api/posts/{post_id}",
        json={"title":"New title"},
        headers = headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New title"
    assert data["content"] == "Original content"

@pytest.mark.anyio
async def test_post_update_by_wrong_user(client:AsyncClient):
    await create_test_user(client,username="user1",email="user1@example.com")
    token1 = await login_user(client,email="user1@example.com")

    response = await client.post(
        "/api/posts",
        json={"title":"user 1's post", "content" : "Only user 1 can edit this"},
        headers= auth_header(token1),
    )

    post_id = response.json()["id"]

    await create_test_user(client,username="user2",email="user2@example.com")
    token2 = await login_user(client,email="user2@example.com")

    response = await client.patch(
        f"/api/posts/{post_id}",
        json={"title":"hacked title"},
        headers=auth_header(token2),
    )

    assert response.status_code ==403
    assert response.json()["detail"] == "Not authorized to update post"

@pytest.mark.anyio 
async def test_get_posts_with_pagination(client : AsyncClient):
    await create_test_user(client)
    token = await login_user(client)
    headers = auth_header(token)

    for i in range(15):
        response = await client.post(
            "/api/posts",
            json={
                "title" : f"Post number = {i}", "content" : f"content for post {i}"
            },
            headers = headers 
        )
        assert response.status_code == 201

    response = await client.get("/api/posts")
    assert response.status_code == 200 
    data = response.json()
    assert data["total"] == 15
    assert len(data["posts"]) == 10
    assert data["has_more"] is True

    response = await client.get("/api/posts?limit=2")
    assert response.status_code == 200 
    data = response.json()
    assert data["total"] == 15
    assert len(data["posts"]) == 2
    assert data["has_more"] is True

    response = await client.get("/api/posts?skip=2&limit=2")
    assert response.status_code == 200 
    data = response.json()
    assert data["total"] == 15
    assert len(data["posts"]) == 2
    assert data["skip"] == 2
    assert data["limit"] == 2 
    assert data["has_more"] is True

import requests

url = "http://localhost:8000"

# Test get access token
def test_get_access_token():
    response = requests.post(f"{url}/token?grant_type=client_credentials&client_id={client_id}&client_secret={client_secret}")
    assert response.status_code == 200
    assert response.json()["access_token"] != ""

# Test get all posts
def test_get_all_posts():
    response = requests.get(f"{url}/page/{page_id}/posts?access_token={access_token}")
    assert response.status_code == 200
    assert len(response.json()) > 0

# Test get post details
def test_get_post_details():
    response = requests.get(f"{url}/post/{post_id}?access_token={access_token}")
    assert response.status_code == 200
    assert response

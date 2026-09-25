import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app({'TESTING': True})
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        yield client


def test_home_page_loads(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Boarding House Management' in response.data


def test_rooms_page_loads(client):
    response = client.get('/rooms')
    assert response.status_code == 200
    assert b'Rooms' in response.data


def test_residents_page_loads(client):
    response = client.get('/residents')
    assert response.status_code == 200
    assert b'Residents' in response.data


def test_delete_resident_and_payment(client):
    room_response = client.post('/rooms', data={
        'room_number': 'C-301',
        'monthly_rent': '9500',
        'status': 'available',
        'notes': 'New room'
    }, follow_redirects=True)
    assert room_response.status_code == 200

    resident_response = client.post('/residents', data={
        'name': 'Test Resident',
        'phone': '01799999999',
        'room_id': '5',
        'move_in': '2026-09-20',
        'monthly_rent': '9500',
        'status': 'active'
    }, follow_redirects=True)
    assert resident_response.status_code == 200

    delete_response = client.post('/residents/3/delete', follow_redirects=True)
    assert delete_response.status_code == 200
    assert b'Test Resident' not in delete_response.data

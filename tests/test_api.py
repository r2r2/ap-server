import pytest

from core.server.server import Server


app = Server('test_app').sanic_app
pytestmark = pytest.mark.asyncio


class TestAuthentication:

    async def test_authentication_ok(self):
        data = {
                    "username": "root",
                    "password": "123456"
               }
        request, resp = await app.asgi_client.post("/auth", json=data)
        assert request.method.lower() == "post"
        assert resp.status == 200

    async def test_authentication_not_ok(self):
        data = {
                    "username": "NOTVALID",
                    "password": "NOTVALID"
               }
        request, resp = await app.asgi_client.post("/auth", json=data)
        assert request.method.lower() == "post"
        assert resp.status == 401


class TestSystemUser:

    async def test_get_users_returns_200(self):
        request, resp = await app.asgi_client.get('/users')
        assert request.method.lower() == "get"
        assert resp.status == 200

    async def test_users_get_by_id_returns_200(self):
        request, resp = await app.asgi_client.get('/users/1')
        assert request.method.lower() == "get"
        assert resp.status == 200


class TestClaim:

    async def test_get_claims_returns_200(self):
        request, resp = await app.asgi_client.get('/claims')
        assert request.method.lower() == "get"
        assert resp.status == 200

    async def test_claims_get_by_id_returns_200(self):
        request, resp = await app.asgi_client.get('/claims/1')
        assert request.method.lower() == "get"
        assert resp.status == 200


class TestVisitor:

    async def test_get_visitors_returns_200(self):
        request, resp = await app.asgi_client.get('/visitors')
        assert request.method.lower() == "get"
        assert resp.status == 200

    async def test_visitors_get_by_id_returns_200(self):
        request, resp = await app.asgi_client.get('/visitors/1')
        assert request.method.lower() == "get"
        assert resp.status == 200


class TestPassport:

    async def test_get_passports_returns_200(self):
        request, resp = await app.asgi_client.get('/passports')
        assert request.method.lower() == "get"
        assert resp.status == 200

    async def test_passports_get_by_id_returns_200(self):
        request, resp = await app.asgi_client.get('/passports/1')
        assert request.method.lower() == "get"
        assert resp.status == 200


class TestMilitaryId:

    async def test_get_militaryids_returns_200(self):
        request, resp = await app.asgi_client.get('/militaryids')
        assert request.method.lower() == "get"
        assert resp.status == 200

    async def test_militaryids_get_by_id_returns_200(self):
        request, resp = await app.asgi_client.get('/militaryids/1')
        assert request.method.lower() == "get"
        assert resp.status == 200


class TestVisitSession:

    async def test_get_visitsessions_returns_200(self):
        request, resp = await app.asgi_client.get('/visitsessions')
        assert request.method.lower() == "get"
        assert resp.status == 200

    async def test_visitsessions_get_by_id_returns_200(self):
        request, resp = await app.asgi_client.get('/visitsessions/1')
        assert request.method.lower() == "get"
        assert resp.status == 200


class TestDriveLicense:

    async def test_get_drivelicenses_returns_200(self):
        request, resp = await app.asgi_client.get('/drivelicenses')
        assert request.method.lower() == "get"
        assert resp.status == 200

    async def test_drivelicenses_get_by_id_returns_200(self):
        request, resp = await app.asgi_client.get('/drivelicenses/1')
        assert request.method.lower() == "get"
        assert resp.status == 200


class TestPass:

    async def test_get_passes_returns_200(self):
        request, resp = await app.asgi_client.get('/passes')
        assert request.method.lower() == "get"
        assert resp.status == 200

    async def test_passes_get_by_id_returns_200(self):
        request, resp = await app.asgi_client.get('/passes/1')
        assert request.method.lower() == "get"
        assert resp.status == 200


class TestTransport:

    async def test_get_transports_returns_200(self):
        request, resp = await app.asgi_client.get('/transports')
        assert request.method.lower() == "get"
        assert resp.status == 200

    async def test_transports_get_by_id_returns_200(self):
        request, resp = await app.asgi_client.get('/transports/1')
        assert request.method.lower() == "get"
        assert resp.status == 200


class TestBlackList:

    async def test_get_blacklist_returns_200(self):
        request, resp = await app.asgi_client.get('/blacklist')
        assert request.method.lower() == "get"
        assert resp.status == 200

    async def test_blacklist_get_by_id_returns_200(self):
        request, resp = await app.asgi_client.get('/blacklist/1')
        assert request.method.lower() == "get"
        assert resp.status == 200


class TestZone:

    async def test_get_zone_returns_200(self):
        request, resp = await app.asgi_client.get('/zone')
        assert request.method.lower() == "get"
        assert resp.status == 200

    async def test_zone_get_by_id_returns_200(self):
        request, resp = await app.asgi_client.get('/zone/1')
        assert request.method.lower() == "get"
        assert resp.status == 200


class TestClaimWay:

    async def test_get_claimway_returns_200(self):
        request, resp = await app.asgi_client.get('/claimway')
        assert request.method.lower() == "get"
        assert resp.status == 200

    async def test_claimway_get_by_id_returns_200(self):
        request, resp = await app.asgi_client.get('/claimway/1')
        assert request.method.lower() == "get"
        assert resp.status == 200


class TestClaimToZone:

    async def test_get_claimtozone_returns_200(self):
        request, resp = await app.asgi_client.get('/claimtozone')
        assert request.method.lower() == "get"
        assert resp.status == 200

    async def test_claimtozone_get_by_id_returns_200(self):
        request, resp = await app.asgi_client.get('/claimtozone/1')
        assert request.method.lower() == "get"
        assert resp.status == 200


class TestParkingPlace:

    async def test_get_parkingplace_returns_200(self):
        request, resp = await app.asgi_client.get('/parkingplace')
        assert request.method.lower() == "get"
        assert resp.status == 200

    async def test_parkingplace_get_by_id_returns_200(self):
        request, resp = await app.asgi_client.get('/parkingplace/1')
        assert request.method.lower() == "get"
        assert resp.status == 200


class TestParking:

    async def test_get_parking_returns_200(self):
        request, resp = await app.asgi_client.get('/parking')
        assert request.method.lower() == "get"
        assert resp.status == 200

    async def test_parking_get_by_id_returns_200(self):
        request, resp = await app.asgi_client.get('/parking/1')
        assert request.method.lower() == "get"
        assert resp.status == 200


class TestRole:

    async def test_get_role_returns_200(self):
        request, resp = await app.asgi_client.get('/role')
        assert request.method.lower() == "get"
        assert resp.status == 200

    async def test_role_get_by_id_returns_200(self):
        request, resp = await app.asgi_client.get('/role/1')
        assert request.method.lower() == "get"
        assert resp.status == 200


async def test_incorrect_url_returns_404():
    request, resp = await app.asgi_client.get('/hello_world')
    assert request.method.lower() == "get"
    assert resp.status == 404



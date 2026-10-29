import httpx
import pytest

from hetzner.client import FetchError, fetch_servers

PAYLOAD = {"server": [{"Id": 7, "Hardware": {}, "Prices": {}, "Details": {}, "Timer": {}}]}


@pytest.mark.asyncio
async def test_fetch_parses_response():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=PAYLOAD))
    async with httpx.AsyncClient(transport=transport) as client:
        servers = await fetch_servers(client, "https://example.invalid/sb.json")
    assert servers[0].id == 7


@pytest.mark.asyncio
async def test_fetch_retries_then_raises():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(500)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(FetchError):
            await fetch_servers(client, "https://example.invalid/sb.json", retries=3, backoff=0)
    assert calls["n"] == 3

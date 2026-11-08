import time

import httpx
from agno.models.nvidia import Nvidia

from src.agents.members import Pacer, make_model
from src.metrics import load_yaml

OK = {"id": "1", "object": "chat.completion", "created": 1, "model": "x",
      "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "hi"}}]}


def call(handler, retries):
    client = httpx.Client(transport=httpx.MockTransport(handler), event_hooks={"request": [Pacer(6000)]})
    model = Nvidia(id="x", api_key="test", max_retries=retries, http_client=client)
    return model.get_client().chat.completions.create(model="x", messages=[{"role": "user", "content": "q"}])


def test_pacer_spaces_requests():
    pacer, times = Pacer(1200), []  # 50 ms apart
    for _ in range(3):
        pacer()
        times.append(time.monotonic())
    assert times[2] - times[0] >= 0.09


def test_retries_429_and_connection_errors():
    seen = []

    def handler(request):
        seen.append(request)
        if len(seen) == 1:
            return httpx.Response(429, headers={"retry-after": "0"}, json={})
        if len(seen) == 2:
            raise httpx.ConnectError("down")
        return httpx.Response(200, json=OK)

    assert call(handler, retries=2).choices[0].message.content == "hi"
    assert len(seen) == 3


def test_nvidia_models_share_one_paced_client():
    settings = load_yaml("settings.yaml")
    leader, writer = (make_model("nvidia", "x", label, settings) for label in ("leader", "writer"))
    assert leader.http_client is writer.http_client
    assert leader.max_retries == settings["nvidia_max_retries"]

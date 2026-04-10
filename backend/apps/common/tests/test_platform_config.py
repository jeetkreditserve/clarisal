from types import SimpleNamespace

from clarisal.settings.base import configure_optional_sentry


class FakeEnv:
    def __init__(self, values):
        self.values = values

    def __call__(self, key, default=""):
        return self.values.get(key, default)

    def float(self, key, default=0.0):
        return float(self.values.get(key, default))


def test_configure_optional_sentry_initializes_sdk_when_dsn_exists():
    captured = {}

    def fake_init(**kwargs):
        captured.update(kwargs)

    fake_env = FakeEnv(
        {
            "SENTRY_DSN": "https://examplePublicKey@o0.ingest.sentry.io/0",
            "SENTRY_TRACES_SAMPLE_RATE": "0.25",
            "ENVIRONMENT": "production",
            "GIT_SHA": "abc123",
        }
    )

    configured = configure_optional_sentry(fake_env, SimpleNamespace(init=fake_init))

    assert configured is True
    assert captured == {
        "dsn": "https://examplePublicKey@o0.ingest.sentry.io/0",
        "traces_sample_rate": 0.25,
        "environment": "production",
        "release": "abc123",
        "integrations": [],
    }


def test_configure_optional_sentry_is_noop_without_dsn():
    configured = configure_optional_sentry(FakeEnv({}), SimpleNamespace(init=lambda **kwargs: None))

    assert configured is False


def test_api_health_endpoint_returns_status_and_version(client, monkeypatch):
    monkeypatch.setenv("GIT_SHA", "health-sha")

    response = client.get("/api/health/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": "health-sha",
    }

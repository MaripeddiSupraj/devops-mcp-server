from types import SimpleNamespace

from app.tools import cicd_tools


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_failed_jobs_fetches_multiple_pages(monkeypatch):
    monkeypatch.setattr(cicd_tools, "settings", SimpleNamespace(github_max_pages=3))

    calls = []

    def fake_get(url, headers=None, params=None, timeout=None):
        calls.append(params["page"])
        if params["page"] == 1:
            jobs = [{"conclusion": "success", "name": "build", "steps": []}] * cicd_tools.GITHUB_PER_PAGE
            return _FakeResponse({"jobs": jobs})
        return _FakeResponse(
            {
                "jobs": [
                    {
                        "conclusion": "failure",
                        "name": "tests",
                        "completed_at": "2026-03-05T00:00:00Z",
                        "steps": [{"name": "unit", "conclusion": "failure"}],
                        "html_url": "https://example/jobs/1",
                    }
                ]
            }
        )

    monkeypatch.setattr(cicd_tools.requests, "get", fake_get)

    result = cicd_tools.get_github_failed_jobs("acme", "repo", 1)

    assert result["status"] == "success"
    assert len(result["failed_jobs"]) == 1
    assert result["failed_jobs"][0]["job_name"] == "tests"
    assert calls == [1, 2]

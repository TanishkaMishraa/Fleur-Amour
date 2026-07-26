"""
AuraFit AI Facial Analysis — Integration tests.
Uses FastAPI TestClient with the full app (real pipeline, no S3).
The /analyze/upload endpoint accepts direct multipart upload, so no S3
or Celery required — ideal for CI.

Because the real MediaPipe FaceMesh model runs on a flat-colour image that
contains no human face, the pipeline will return success=False with
error_code=NO_FACE_DETECTED. Integration tests therefore verify:
  - HTTP response codes and envelope format are correct.
  - The error response matches our API contract.
  - Health and readiness probes return 200.
"""
from __future__ import annotations

import io
import pytest
from fastapi.testclient import TestClient
from PIL import Image


@pytest.fixture(scope="module")
def client():
    """
    Module-scoped TestClient — loads MediaPipe once for the entire module.
    Model warm-up may take 2-5s in CI; scope=module amortises the cost.
    """
    from app.main import create_app
    app = create_app()
    with TestClient(app) as c:
        yield c


def _make_jpeg(size: tuple[int, int] = (300, 300), color=(120, 100, 110)) -> bytes:
    """Return a minimal JPEG image as bytes."""
    buf = io.BytesIO()
    Image.new("RGB", size, color=color).save(buf, format="JPEG", quality=85)
    return buf.getvalue()


class TestHealthEndpoints:

    def test_health_returns_200(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "service" in body
        assert "version" in body
        assert isinstance(body["model_loaded"], bool)
        assert isinstance(body["gpu_available"], bool)

    def test_ready_returns_200_when_pipeline_loaded(self, client: TestClient) -> None:
        resp = client.get("/ready")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"


class TestAnalyzeUploadEndpoint:

    def test_valid_jpeg_returns_response_envelope(self, client: TestClient) -> None:
        """A valid JPEG with no face should return success=False with NO_FACE_DETECTED."""
        jpeg = _make_jpeg()
        resp = client.post(
            "/analyze/upload",
            files={"file": ("selfie.jpg", jpeg, "image/jpeg")},
        )
        assert resp.status_code == 200
        body = resp.json()
        # Response must always follow the SyncAnalyzeResponse envelope
        assert "success" in body
        assert "task_id" in body
        # A flat-colour synthetic image has no face — expect pipeline failure
        if not body["success"]:
            assert body["error"] is not None
            assert body["error"]["error_code"] in {
                "NO_FACE_DETECTED", "QUALITY_CHECK_FAILED", "ANALYZER_FAILED",
            }
            assert isinstance(body["error"]["retryable"], bool)

    def test_unsupported_mimetype_rejected(self, client: TestClient) -> None:
        resp = client.post(
            "/analyze/upload",
            files={"file": ("doc.pdf", b"%PDF fake content", "application/pdf")},
        )
        assert resp.status_code == 415

    def test_oversized_file_rejected(self, client: TestClient) -> None:
        """File exceeding 10MB should be rejected with 413."""
        oversized = b"\x00" * (10 * 1024 * 1024 + 1)
        resp = client.post(
            "/analyze/upload",
            files={"file": ("big.jpg", oversized, "image/jpeg")},
        )
        assert resp.status_code == 413

    def test_png_accepted(self, client: TestClient) -> None:
        """PNG (not just JPEG) should be accepted by the upload endpoint."""
        buf = io.BytesIO()
        Image.new("RGB", (200, 200), color=(100, 120, 110)).save(buf, format="PNG")
        png_bytes = buf.getvalue()
        resp = client.post(
            "/analyze/upload",
            files={"file": ("photo.png", png_bytes, "image/png")},
        )
        # Should not be 415 or 413 — any analysis result is fine
        assert resp.status_code == 200

    def test_task_id_always_present(self, client: TestClient) -> None:
        """task_id should be in every response (needed for client polling)."""
        jpeg = _make_jpeg()
        resp = client.post(
            "/analyze/upload",
            files={"file": ("selfie.jpg", jpeg, "image/jpeg")},
        )
        body = resp.json()
        assert "task_id" in body
        assert isinstance(body["task_id"], str)
        assert len(body["task_id"]) > 0

    def test_error_response_is_serialisable(self, client: TestClient) -> None:
        """The error envelope must be JSON-serialisable (no Python types leaking)."""
        import json
        jpeg = _make_jpeg()
        resp = client.post(
            "/analyze/upload",
            files={"file": ("selfie.jpg", jpeg, "image/jpeg")},
        )
        # This will raise if any value is not JSON-serialisable
        json.dumps(resp.json())

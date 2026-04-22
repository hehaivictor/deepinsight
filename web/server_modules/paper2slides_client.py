from __future__ import annotations

from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin

import requests


class Paper2SlidesClient:
    """Thin client for the Paper2Slides external service API."""

    def __init__(self, base_url: str, api_token: str = "", timeout: int = 30):
        self.base_url = str(base_url or "").rstrip("/")
        self.api_token = str(api_token or "").strip()
        self.timeout = max(1, int(timeout or 30))

    def is_configured(self) -> bool:
        return bool(self.base_url)

    def _url(self, path: str) -> str:
        return urljoin(f"{self.base_url}/", path.lstrip("/"))

    def _headers(self) -> dict[str, str]:
        if not self.api_token:
            return {}
        return {"Authorization": f"Bearer {self.api_token}"}

    def create_presentation(
        self,
        source_path: Path,
        *,
        profile: str = "consulting_exec_cn",
        content: str = "paper",
        output_type: str = "slides",
        style: str = "academic",
        style_prompt: str = "",
        length: str = "medium",
        fast_mode: bool = False,
    ) -> dict[str, Any]:
        with open(source_path, "rb") as file_handle:
            files = {
                "files": (
                    source_path.name,
                    file_handle,
                    "text/markdown" if source_path.suffix.lower() in {".md", ".markdown"} else "application/octet-stream",
                )
            }
            data = {
                "profile": profile,
                "content": content,
                "output_type": output_type,
                "style": style,
                "style_prompt": style_prompt,
                "length": length,
                "fast_mode": "true" if fast_mode else "false",
            }
            response = requests.post(
                self._url("/api/v1/presentations"),
                headers=self._headers(),
                files=files,
                data=data,
                timeout=self.timeout,
            )
        response.raise_for_status()
        return response.json()

    def get_status(self, job_id: str) -> dict[str, Any]:
        response = requests.get(
            self._url(f"/api/v1/presentations/{job_id}"),
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def get_result(self, job_id: str) -> tuple[Optional[dict[str, Any]], bool]:
        response = requests.get(
            self._url(f"/api/v1/presentations/{job_id}/result"),
            headers=self._headers(),
            timeout=self.timeout,
        )
        if response.status_code == 202:
            try:
                return response.json(), False
            except ValueError:
                return {"status": "processing"}, False
        response.raise_for_status()
        return response.json(), True

    def cancel(self, job_id: str) -> dict[str, Any]:
        response = requests.post(
            self._url(f"/api/v1/presentations/{job_id}/cancel"),
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()


def select_primary_artifact_url(result: dict[str, Any]) -> str:
    def _clean_url(value: Any) -> str:
        return str(value or "").strip()

    def _looks_like_pdf_url(value: Any) -> bool:
        url = _clean_url(value)
        if not url:
            return False
        normalized = url.split("?", 1)[0].split("#", 1)[0].lower()
        return normalized.endswith(".pdf")

    def _artifact_url(artifact: dict[str, Any]) -> str:
        for key in ("url", "download_url", "preview_url"):
            url = _clean_url(artifact.get(key))
            if url:
                return url
        return ""

    def _artifact_is_pdf(artifact: Any) -> bool:
        if not isinstance(artifact, dict):
            return False
        type_text = str(artifact.get("type") or artifact.get("kind") or "").strip().lower()
        if "pdf" in type_text:
            return True
        for key in ("media_type", "content_type", "mime_type"):
            if "pdf" in str(artifact.get(key) or "").strip().lower():
                return True
        for key in ("url", "download_url", "preview_url", "relative_path", "path", "filename", "name"):
            if _looks_like_pdf_url(artifact.get(key)):
                return True
        return False

    if not isinstance(result, dict):
        return ""

    for key in ("pdf_url", "ppt_url", "presentation_url", "download_url"):
        url = _clean_url(result.get(key))
        if _looks_like_pdf_url(url):
            return url

    primary = result.get("primary_artifact")
    if _artifact_is_pdf(primary):
        return _artifact_url(primary)

    artifacts = result.get("artifacts")
    if not isinstance(artifacts, list):
        return ""
    for artifact in artifacts:
        if _artifact_is_pdf(artifact):
            url = _artifact_url(artifact)
            if url:
                return url
    return ""

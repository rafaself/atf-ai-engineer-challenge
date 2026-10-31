"""Default tests never contact a real model, even if credentials are present."""

import pytest
from pydantic_ai import models


@pytest.fixture(autouse=True)
def forbid_live_model_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", False)

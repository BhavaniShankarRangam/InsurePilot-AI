import os
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="insurepilot-test-"))
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = f"sqlite:///{(_tmp / 'test.db').as_posix()}"
os.environ["UPLOAD_DIR"] = str(_tmp / "uploads")
os.environ["LLM_PROVIDER"] = "mock"
os.environ["SEED_DEMO"] = "true"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.session import SessionLocal, init_db  # noqa: E402
from app.demo.seed import seed_demo  # noqa: E402
from app.main import app  # noqa: E402

init_db()


@pytest.fixture(scope="session")
def demo_user_id() -> str:
    with SessionLocal() as db:
        return seed_demo(db).id


@pytest.fixture()
def db():
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture()
def portfolio(db, demo_user_id):
    from app.services.portfolio import load_portfolio

    return load_portfolio(db, demo_user_id)


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def authed(client):
    r = client.post("/auth/demo")
    assert r.status_code == 200
    client.headers.update({"X-InsurePilot-Client": "web"})
    return client

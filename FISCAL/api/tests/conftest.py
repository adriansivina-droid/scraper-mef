import pytest

from app import ipc


@pytest.fixture(autouse=True)
def sin_internet_para_el_ipc(monkeypatch):
    """Las pruebas no consultan al BCRP: la API del IPC «no responde» salvo que una prueba la reemplace."""
    def falla(*a, **k):
        raise ConnectionError("sin red en las pruebas")
    monkeypatch.setattr(ipc, "de_bcrp", falla)

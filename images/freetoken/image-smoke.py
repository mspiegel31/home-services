import subprocess
import sysconfig
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from freetoken.server.control_api import register_control_routes

subprocess.run(
    ['cc', '-x', 'c', '-fsyntax-only', '-I' + sysconfig.get_paths()['include'], '-'],
    input=b'#include <Python.h>\n',
    check=True,
)

state = SimpleNamespace(
    maintenance_state='loading',
    fatal_error=None,
    config=SimpleNamespace(served_model_name='image-smoke'),
)
app = FastAPI(version='0.2.0')
register_control_routes(app, lambda: state)
with TestClient(app) as client:
    for maintenance, expected in [('loading', 503), ('serving', 200), ('rebuilding', 503), ('failed', 503)]:
        state.maintenance_state = maintenance
        response = client.get('/health')
        assert response.status_code == expected, (maintenance, response.status_code, response.text)
    state.maintenance_state = 'serving'
    state.fatal_error = 'backend worker failed'
    response = client.get('/health')
    assert response.status_code == 503 and response.json()['status'] == 'error'
print('FREETOKEN_IMAGE_SMOKE_OK: Python JIT headers compile; health gates loading, rebuilds and backend failure')

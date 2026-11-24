"""Pruebas unitarias de la API de notas (se ejecutan en la etapa 'Pruebas unitarias' de Jenkins)."""


def test_inicio_lista_endpoints(cliente):
    r = cliente.get("/")
    assert r.status_code == 200
    assert r.get_json()["servicio"] == "api-notas"
    assert "POST /notas" in r.get_json()["endpoints"]


def test_salud_ok_cuando_hay_bd(cliente):
    r = cliente.get("/salud")
    assert r.status_code == 200
    assert r.get_json()["db"] == "ok"


def test_salud_503_cuando_la_bd_no_responde(cliente, bd):
    bd.caida = True
    r = cliente.get("/salud")
    assert r.status_code == 503
    assert r.get_json()["db"] == "error"


def test_crear_nota_devuelve_201_y_el_id(cliente):
    r = cliente.post("/notas", json={"texto": "Hola desde Jenkins"})
    assert r.status_code == 201
    cuerpo = r.get_json()
    assert cuerpo["id"] == 1
    assert cuerpo["texto"] == "Hola desde Jenkins"


def test_crear_nota_quita_espacios(cliente):
    r = cliente.post("/notas", json={"texto": "   con espacios   "})
    assert r.get_json()["texto"] == "con espacios"


def test_crear_nota_sin_texto_da_400(cliente):
    assert cliente.post("/notas", json={}).status_code == 400
    assert cliente.post("/notas", json={"texto": "   "}).status_code == 400
    assert cliente.post("/notas", data="no es json").status_code == 400


def test_listar_y_consultar_notas(cliente):
    cliente.post("/notas", json={"texto": "primera"})
    cliente.post("/notas", json={"texto": "segunda"})

    lista = cliente.get("/notas").get_json()
    assert [n["texto"] for n in lista] == ["primera", "segunda"]

    r = cliente.get("/notas/2")
    assert r.status_code == 200
    assert r.get_json()["texto"] == "segunda"


def test_nota_inexistente_da_404(cliente):
    r = cliente.get("/notas/99")
    assert r.status_code == 404

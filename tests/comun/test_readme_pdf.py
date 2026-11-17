from pathlib import Path

from roboadvisor.comun.readme_pdf import REPO_URL, _absolutos


def test_los_enlaces_relativos_pasan_a_absolutos(tmp_path):
    raiz = tmp_path
    (raiz / "entregas" / "taller-1").mkdir(parents=True)
    (raiz / "src").mkdir()
    md = "[a](Taller1_Informe.pdf) [b](../../src/) [c](https://x.org) [d](#seccion)"
    out = _absolutos(md, raiz / "entregas" / "taller-1", Path(raiz))
    assert f"({REPO_URL}/blob/master/entregas/taller-1/Taller1_Informe.pdf)" in out
    assert f"({REPO_URL}/tree/master/src)" in out
    assert "(https://x.org)" in out and "(#seccion)" in out

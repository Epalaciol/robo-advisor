"""Demo manual del motor financiero (E04) sobre el panel sintético de pruebas.

Imprime pesos, Sharpe del tangente y el portafolio completo (y*) para
A = 8, 6, 4, 3, 1. No usa Supabase ni datos reales.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from roboadvisor.core.markowitz import cal, min_varianza, tangente  # noqa: E402
from roboadvisor.core.portafolio_completo import componer  # noqa: E402
from roboadvisor.core.retornos import estimar  # noqa: E402
from tests.conftest import generar_panel_sintetico  # noqa: E402

W_MAX = 0.40


def main() -> None:
    panel = generar_panel_sintetico()
    est = estimar(panel, rf=0.02, ventana_meses=60, min_meses=36)

    print(f"Estimación: {est.n_meses} meses, rf={est.rf:.2%}, fecha_fin={est.fecha_fin.date()}")

    port_min_var = min_varianza(est, W_MAX)
    print("\nMínima varianza:")
    print(port_min_var.w.round(4))
    print(f"  retorno={port_min_var.retorno:.2%} sigma={port_min_var.sigma:.2%}")

    port_tangente = tangente(est, W_MAX)
    print("\nTangente (óptimo de riesgo):")
    print(port_tangente.w.round(4))
    print(
        f"  retorno={port_tangente.retorno:.2%} sigma={port_tangente.sigma:.2%} "
        f"sharpe={port_tangente.sharpe:.3f}"
    )
    if port_tangente.advertencia:
        print(f"  advertencia: {port_tangente.advertencia}")

    pendiente, intercepto = cal(port_tangente, est.rf)
    print(f"\nCAL: E(r) = {intercepto:.4f} + {pendiente:.4f}·sigma")

    print("\nPortafolio completo por perfil (A):")
    for a in (8, 6, 4, 3, 1):
        completo = componer(port_tangente, est.rf, a)
        print(
            f"  A={a}: y*={completo.y:.3f} retorno={completo.retorno:.2%} "
            f"sigma={completo.sigma:.2%} utilidad={completo.utilidad:.4f}"
        )


if __name__ == "__main__":
    main()

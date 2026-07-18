"""Aylık sepet güncellemesi — GitHub Actions tarafından otomatik çalıştırılır
(.github/workflows/rebalance.yml). Elle de çalıştırılabilir:
    python scripts/rebalance.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from analyzer.portfolio import TRACKED_TIER, rebalance
from analyzer.universe import get_universe


def main() -> int:
    universe, is_live, seed_date = get_universe(TRACKED_TIER)
    if not universe:
        print("BIST evreni alınamadı (canlı ve yedek ikisi de başarısız), çıkılıyor.")
        return 1

    if not is_live:
        print(f"Uyarı: canlı kaynak alınamadı, {seed_date} tarihli yedek liste kullanıldı.")

    diff = rebalance(universe)
    print(f"Sat: {diff['sat']}")
    print(f"Ekle: {diff['ekle']}")
    print(f"Tut: {diff['tut']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

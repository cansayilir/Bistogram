"""AI Sepeti günlük güncellemesi — GitHub Actions tarafından otomatik
çalıştırılır (.github/workflows/ai_basket_update.yml). Elle de çalıştırılabilir:
    python scripts/update_ai_basket.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from analyzer.ai_basket import update_ai_basket
from analyzer.scoring import compute_scores
from analyzer.universe import get_universe

TIER = "BIST 100"


def main() -> int:
    universe, is_live, seed_date = get_universe(TIER)
    if not universe:
        print("BIST evreni alınamadı (canlı ve yedek ikisi de başarısız), çıkılıyor.")
        return 1

    if not is_live:
        print(f"Uyarı: canlı kaynak alınamadı, {seed_date} tarihli yedek liste kullanıldı.")

    scores = compute_scores(universe)
    if scores.empty:
        print("Puanlama için veri alınamadı, çıkılıyor.")
        return 1

    state = update_ai_basket(scores)
    print(f"Aktif pozisyon: {len(state['active'])}, Kapanan işlem (toplam): {len(state['closed'])}")
    for symbol, pos in state["active"].items():
        print(f"  {symbol}: giriş {pos['giris_fiyati']:.2f}, hedef {pos['hedef_satis_fiyati']:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

import json
from datetime import date
from pathlib import Path

from analyzer.basket import compute_momentum_table

STATE_PATH = Path(__file__).parent.parent / "data" / "basket_state.json"

TRACKED_TIER = "BIST 100"
TOP_FRAC = 0.2


def select_basket(universe: list[str], top_frac: float = TOP_FRAC) -> list[str]:
    table = compute_momentum_table(universe)
    if table.empty:
        return []
    basket_size = max(1, round(len(table) * top_frac))
    return table.head(basket_size)["Hisse"].tolist()


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {"basket": [], "last_rebalanced": None, "history": []}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def diff_basket(old_basket: list[str], new_basket: list[str]) -> dict:
    old_set, new_set = set(old_basket), set(new_basket)
    return {
        "tut": sorted(old_set & new_set),
        "ekle": sorted(new_set - old_set),
        "sat": sorted(old_set - new_set),
    }


def rebalance(universe: list[str], top_frac: float = TOP_FRAC) -> dict:
    """Sepeti güncel momentum sıralamasına göre yeniden kurar, öncekiyle
    kıyaslayıp neyin satılıp neyin eklendiğini kaydeder. `data/basket_state.json`
    git'e commit'lenerek kalıcı hale getiriliyor (bkz. scripts/rebalance.py ve
    .github/workflows/rebalance.yml — ayda bir otomatik çalışır).
    """
    state = load_state()
    new_basket = select_basket(universe, top_frac)
    diff = diff_basket(state["basket"], new_basket)
    today = date.today().isoformat()
    state["history"].append({"date": today, **diff})
    state["basket"] = new_basket
    state["last_rebalanced"] = today
    save_state(state)
    return diff

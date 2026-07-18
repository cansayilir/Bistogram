import borsapy as bp
import pandas as pd

from analyzer.basket import fetch_prices

SYSTEM_PROMPT = """Sen BIST (Borsa İstanbul) hisseleri için bir analiz asistanısın.
Sana verilen ham veriyi (haberler, temel finansal göstergeler, fiyat performansı)
kullanarak dengeli, dürüst bir durum değerlendirmesi yapıyorsun.

Kurallar:
- ASLA kesin yön tahmini yapma ("kesinlikle yükselecek/düşecek" gibi ifadeler kullanma).
- Olumlu senaryo, olumsuz senaryo ve dikkat edilmesi gereken riskleri ayrı ayrı anlat.
- Verilen veri eksik veya belirsizse bunu açıkça söyle, boşluğu varsayımla doldurma.
- Sade, jargonsuz Türkçe kullan — okuyan kişi finans uzmanı değil.
- Bu bir yatırım tavsiyesi değildir; bunu yanıtının bir yerinde açıkça belirt.
- Kısa ve öz ol: 4-6 paragraf yeterli.
"""


def gather_stock_context(symbol: str) -> dict:
    ticker = bp.Ticker(symbol)

    try:
        news = ticker.news
        news_items = [
            f"- {row['Date']}: {row['Title']}" for _, row in news.head(10).iterrows()
        ]
    except Exception:
        news_items = []

    try:
        income = ticker.income_stmt
        financial_summary = income.head(6).to_string()
    except Exception:
        financial_summary = "Temel finansal veri alınamadı."

    try:
        prices = fetch_prices([symbol], period="18mo")
        col = f"{symbol}.IS"
        series = prices[col].dropna()
        current_price = series.iloc[-1]
        year_ago_price = series.iloc[0]
        yearly_return = (current_price / year_ago_price - 1) * 100
        price_summary = (
            f"Güncel fiyat: {current_price:.2f} TL, "
            f"~18 ay önceki fiyat: {year_ago_price:.2f} TL, "
            f"getiri: %{yearly_return:.1f}"
        )
    except Exception:
        price_summary = "Fiyat verisi alınamadı."

    return {
        "symbol": symbol,
        "news": news_items,
        "financial_summary": financial_summary,
        "price_summary": price_summary,
    }


def build_prompt(context: dict) -> str:
    news_block = "\n".join(context["news"]) if context["news"] else "Haber bulunamadı."
    return f"""Hisse: {context['symbol']}

## Fiyat performansı
{context['price_summary']}

## Son haberler / KAP açıklamaları
{news_block}

## Temel finansal göstergeler (son yıllar)
{context['financial_summary']}

Bu bilgilere dayanarak {context['symbol']} hissesi için bir durum değerlendirmesi yap.
"""


def stream_commentary(symbol: str, client):
    """client: anthropic.Anthropic örneği. Metin parçalarını üretir (Streamlit
    st.write_stream ile uyumlu)."""
    context = gather_stock_context(symbol)
    prompt = build_prompt(context)

    with client.messages.stream(
        model="claude-opus-4-8",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        yield from stream.text_stream

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
- Türkiye yüksek enflasyon ortamında olduğu için, TL bazlı gelir/kâr büyümesinden
  bahsederken bunun nominal olduğunu, enflasyon düşülünce gerçek büyümenin çok daha
  düşük (hatta negatif) olabileceğini belirt — sadece "gelirler X kat arttı" deyip
  bunu tek başına olumlu bir sinyal gibi sunma.
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

    key_income_lines = [
        "Satış Gelirleri",
        "Satışların Maliyeti (-)",
        "BRÜT KAR (ZARAR)",
        "FAALİYET KARI (ZARARI)",
        "DÖNEM KARI (ZARARI)",
    ]
    try:
        income = ticker.income_stmt
        available = [line for line in key_income_lines if line in income.index]
        financial_summary = (
            income.loc[available].to_string() if available else income.head(10).to_string()
        )
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


MODEL = "gemini-3.5-flash"


def stream_commentary(symbol: str, client):
    """client: google.genai.Client örneği. Metin parçalarını üretir (Streamlit
    st.write_stream ile uyumlu)."""
    from google.genai import types

    context = gather_stock_context(symbol)
    prompt = build_prompt(context)

    for chunk in client.models.generate_content_stream(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
    ):
        if chunk.text:
            yield chunk.text

import os

import altair as alt
import pandas as pd
import streamlit as st
from google import genai

from analyzer.ai_basket import load_state as load_ai_basket_state
from analyzer.backtest import run_momentum_backtest
from analyzer.basket import compute_momentum_table, fetch_prices, to_yf_ticker
from analyzer.commentary import build_prompt, gather_stock_context, stream_llm_response
from analyzer.ipo import get_ipo_table
from analyzer.portfolio import TRACKED_TIER, load_state
from analyzer.universe import UNIVERSE_OPTIONS, get_universe

st.set_page_config(page_title="Bistogram", page_icon="📊")

st.title("Bistogram")
st.caption("BIST için sıfırdan, kendi yöntemlerimizle geliştirilen analiz sistemi")

st.header("Takip Edilen Sepet")
st.write(
    f"Bu, sürekli takip edilen tek resmi sepet — {TRACKED_TIER} evreninde, ayda bir "
    "otomatik olarak yeniden hesaplanıyor (GitHub Actions ile). Aşağıdaki 'Sepet "
    "Motoru' bölümü farklı evrenleri anlık keşfetmek için, ama zaman içindeki "
    "değişimi (sat/ekle/tut) sadece burası takip ediyor."
)

portfolio_state = load_state()

if not portfolio_state["basket"]:
    st.info("Henüz ilk otomatik güncelleme çalışmadı — burada gösterilecek bir şey yok.")
else:
    st.caption(f"Son güncelleme: {portfolio_state['last_rebalanced']}")
    last_change = portfolio_state["history"][-1]

    col1, col2, col3 = st.columns(3)
    col1.metric("Sepette tutulan", len(portfolio_state["basket"]))
    col2.metric("Bu ay eklenen", len(last_change["ekle"]))
    col3.metric("Bu ay satılan", len(last_change["sat"]))

    if last_change["ekle"]:
        st.success("Ekle: " + ", ".join(last_change["ekle"]))
    if last_change["sat"]:
        st.error("Sat: " + ", ".join(last_change["sat"]))
    if last_change["tut"]:
        st.info("Tut: " + ", ".join(last_change["tut"]))

    with st.expander("Güncel tam sepet listesi"):
        st.write(", ".join(sorted(portfolio_state["basket"])))

st.divider()

tier = st.selectbox("Hisse evreni", list(UNIVERSE_OPTIONS.keys()), index=1)
st.caption(
    "BIST 500 ve BIST TÜM daha geniş evren oldukları için ilk yüklemede "
    "yaklaşık 1 dakika sürebilir (sonraki ziyaretlerde önbellekten hızlı gelir)."
)


@st.cache_data(ttl=6 * 60 * 60, show_spinner="BIST listesi alınıyor...")
def get_universe_cached(tier: str):
    return get_universe(tier)


universe, is_live, seed_date = get_universe_cached(tier)

if not universe:
    st.error(
        "BIST hisse listesi hem canlı kaynaktan hem yedekten alınamadı. "
        "Lütfen daha sonra tekrar dene."
    )
    st.stop()
if not is_live:
    st.info(
        f"Not: Borsa İstanbul'un canlı kaynağına şu an ulaşılamadı (zaman zaman "
        f"oluyor), {seed_date} tarihli yedek listeye düşüldü. Hisse sayısı "
        "büyük ölçüde güncel olsa da birkaç değişiklik kaçırılmış olabilir."
    )

st.header("Sepet Motoru — Momentum Sıralaması")
st.write(
    f"Aşağıdaki tablo, {tier} evrenindeki hisseleri son 1 yıllık performansına göre "
    "sıralıyor (en son 1 ay hariç tutuluyor — kısa vadeli gürültüyü azaltmak için). "
    "En üstteki hisseler bu ölçüye göre son dönemde en güçlü performans gösterenler."
)
st.warning(
    "Bu anlık sıralama bir alım-satım önerisi değil — aşağıdaki 'Geçmiş Test' "
    "bölümü bu mantığın uzun vadede ne kadar işe yaradığını (yaramadığını) gösteriyor."
)


@st.cache_data(ttl=6 * 60 * 60, show_spinner="BIST verileri çekiliyor...")
def get_momentum_table(universe: list[str]):
    return compute_momentum_table(universe)


momentum_table = get_momentum_table(universe)

if momentum_table.empty:
    st.error("Veri çekilemedi, lütfen daha sonra tekrar deneyin.")
else:
    format_spec = {"12-1 Ay Getiri (%)": "{:.1f}", "Güncel Fiyat": "{:.2f}"}

    top_n = 10
    st.subheader(f"En güçlü {top_n} hisse")
    st.dataframe(momentum_table.head(top_n).style.format(format_spec))
    st.caption(
        "Listedeki bazı hisselerde çok yüksek getiri yakın zamanlı halka arz "
        "sonrası gerçek bir rallinin sonucu olabilir — şüpheli gördüğün bir "
        "rakamı ayrıca doğrulaman iyi olur, ama sırf büyük diye elenmiyor."
    )

    with st.expander("Tüm sıralamayı gör"):
        st.dataframe(momentum_table.style.format(format_spec))

st.divider()
st.header("Geçmiş Test (2006 — bugün)")
st.write(
    f"Bu sepet mantığını {tier} evreninde geçmişe uyguladık: 2006'dan bugüne, "
    "her ay yeniden sıralayıp en güçlü %20'lik dilimi tutmuş olsaydık ne olurdu? "
    "(2005 öncesi, Yeni Türk Lirası geçiş dönemi civarında veride gerçek "
    "olmayan bir fiyat sıçraması bulundu — bu yüzden test 2006'dan başlıyor, "
    "aşağıdaki notta detayı var.)"
)


@st.cache_data(ttl=24 * 60 * 60, show_spinner="Geçmiş test çalıştırılıyor...")
def get_backtest(universe: list[str]):
    return run_momentum_backtest(universe)


monthly, summary = get_backtest(universe)

if not summary:
    st.error("Geçmiş test için yeterli veri yok.")
else:
    col1, col2, col3 = st.columns(3)
    col1.metric("Test edilen ay sayısı", summary["ay_sayisi"])
    col2.metric("Sepetin BIST ortalamasını geçtiği aylar", f"%{summary['kazanma_orani'] * 100:.0f}")
    col3.metric("Aylık ortalama fark", f"%{summary['ortalama_fark'] * 100:.2f}")

    chart_df = monthly[["Tarih", "Sepet Kümülatif", "Benchmark Kümülatif"]].melt(
        "Tarih", var_name="Seri", value_name="Değer"
    )
    chart_df["Seri"] = chart_df["Seri"].replace(
        {"Sepet Kümülatif": "Sepet", "Benchmark Kümülatif": "Benchmark"}
    )
    color_scale = alt.Scale(domain=["Sepet", "Benchmark"], range=["#2a78d6", "#008300"])

    chart = (
        alt.Chart(chart_df)
        .mark_line(strokeWidth=2)
        .encode(
            x=alt.X("Tarih:T", title=None),
            y=alt.Y(
                "Değer:Q",
                title="Büyüme katsayısı (log ölçek, 1 = başlangıç)",
                scale=alt.Scale(type="log"),
            ),
            color=alt.Color("Seri:N", scale=color_scale, legend=alt.Legend(title=None)),
            tooltip=["Tarih:T", "Seri:N", alt.Tooltip("Değer:Q", format=".1f")],
        )
        .properties(height=350)
        .interactive()
    )
    st.altair_chart(chart, use_container_width=True)

    st.warning(
        "Dürüst değerlendirme: bu sonuç 'kesinlikle işe yarıyor' diyebileceğimiz "
        "kadar güçlü değil — aydan aya çok dalgalanıyor, ortada bir sonuç. Önemli "
        "bir not: bu testi ilk çalıştırdığımızda çok daha güçlü bir sonuç çıkmıştı, "
        "ama araştırınca bunun bir kısmının 2005'teki TL geçişiyle ilgili bir veri "
        "hatasından kaynaklandığını bulduk. Bu, o hata düzeltildikten sonraki, "
        "daha zayıf ama daha güvenilir sonuç."
    )

    with st.expander("Teknik detaylar"):
        st.write(f"Medyan aylık fark: %{summary['medyan_fark'] * 100:.2f}")
        st.write(
            f"t-istatistiği: {summary['t_stat']:.2f} "
            "(genelde ≥2 olması 'şansla açıklanamaz' için kabul edilen bir eşik — "
            "bu sonuç bu eşiğin altında kalıyor)"
        )
        st.write(
            f"20 yıl sonunda 1 birim: Sepet → {summary['sepet_kumulatif_son']:.0f}x, "
            f"Benchmark → {summary['benchmark_kumulatif_son']:.0f}x "
            "(mutlak büyüklükler TL'nin bu dönemdeki yüksek enflasyonu nedeniyle "
            "abartılı görünüyor — asıl bakılması gereken ikisi arasındaki fark)"
        )

st.divider()
st.header("Halka Arz Menüsü")
st.write(
    "Borsa İstanbul'un resmi 'BIST Halka Arz' listesindeki hisseler — ilk işlem "
    "gününden bugüne performansları ile. Henüz AI yorumu / emsal kıyaslaması yok, "
    "bu ilk sürüm sadece ham listeyi gösteriyor."
)
st.caption(
    "Not: 'İlk Fiyat', gerçek halka arz fiyatı değil, yfinance'te bulunan ilk "
    "işlem günü kapanış fiyatı — ilk gün primi/iskontosunu içerebilir."
)


@st.cache_data(ttl=6 * 60 * 60, show_spinner="Halka arz listesi hazırlanıyor...")
def get_ipo_table_cached():
    return get_ipo_table()


ipo_table, ipo_is_live, ipo_seed_date = get_ipo_table_cached()

if not ipo_is_live and not ipo_table.empty:
    st.info(f"Not: canlı kaynağa ulaşılamadı, {ipo_seed_date} tarihli yedek liste kullanıldı.")

if ipo_table.empty:
    st.error("Halka arz listesi alınamadı, lütfen daha sonra tekrar dene.")
else:
    display_table = ipo_table.copy()
    display_table["İlk Günden Getiri (%)"] = display_table["İlk Günden Getiri (%)"].apply(
        lambda v: "Yeni (henüz tek gün verisi var)" if pd.isna(v) else f"{v:.1f}"
    )
    st.dataframe(display_table)

st.divider()
st.header("AI Hisse Yorumu")
st.write(
    "Bir hisse kodu gir, güncel haberler + temel finansal göstergeler + fiyat "
    "performansını kullanarak AI'dan bir durum değerlendirmesi al."
)
st.caption(
    "Bu bir yatırım tavsiyesi ya da tahmin değil — olumlu/olumsuz senaryoları ve "
    "riskleri anlatan bir özet. Kaynak veri: KAP açıklamaları ve temel oranlar."
)

api_key = st.secrets.get("GEMINI_API_KEY") if hasattr(st, "secrets") else None
api_key = api_key or os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.warning(
        "Bu özellik ücretsiz bir Google Gemini API anahtarı gerektiriyor, henüz "
        "ayarlanmamış. `aistudio.google.com` üzerinden ücretsiz bir anahtar al, "
        "sonra Streamlit Cloud'da: uygulama ayarları → Secrets → "
        '`GEMINI_API_KEY = "..."` ekle. Yerelde: `.streamlit/secrets.toml` '
        "dosyasına aynı satırı ekle."
    )
else:
    symbol_input = st.text_input("Hisse kodu (örn. THYAO)", "").strip().upper()
    if st.button("Yorum al") and symbol_input:
        client = genai.Client(api_key=api_key)

        with st.spinner(f"{symbol_input} için haberler, finansal tablo ve fiyat verisi toplanıyor..."):
            context = gather_stock_context(symbol_input)
            prompt = build_prompt(context)

        response_stream = stream_llm_response(prompt, client)
        with st.spinner("Gemini yorum üretiyor..."):
            first_chunk = next(response_stream, None)

        if first_chunk is None:
            st.error("Yorum üretilemedi, lütfen tekrar dene.")
        else:
            def _prepend(first, rest):
                yield first
                yield from rest

            st.write_stream(_prepend(first_chunk, response_stream))

st.divider()
st.header("AI Sepeti (Deneysel)")
st.write(
    "Momentum sepetinden farklı, ikinci bir sistem: her BIST 100 hissesini "
    "momentum (40), kâr trendi (20), değerleme (20) ve haber/KAP temizliği (20) "
    "açısından 100 üzerinden puanlıyor, buna göre bir hedef alım fiyatı "
    "belirliyor. Fiyat bu hedefe düşünce sepete giriyor, hedef satış fiyatına "
    "ulaşınca çıkıp sonucu kaydediyor. Günde bir otomatik güncelleniyor."
)
st.warning(
    "DÜRÜST UYARI: Momentum bileşeni 2006-2026 verisiyle test edildi (zayıf "
    "ama pozitif bir sinyal). İlk denemede eklenen bir 'trend' bileşeni "
    "(200 günlük ortalamaya yakınlık) test edilince momentumu güçlendirmek "
    "yerine anlamlı şekilde kötüleştirdiği görüldü ve kaldırıldı. Kâr trendi, "
    "değerleme ve haber bileşenleri ise henüz geçmiş veriyle test edilemedi "
    "(tarihsel veri kaynağımız yok) — sadece ileriye dönük izleniyor."
)

ai_state = load_ai_basket_state()

if ai_state.get("last_updated"):
    st.caption(f"Son güncelleme: {ai_state['last_updated']}")

if ai_state["active"]:
    st.subheader(f"Aktif Pozisyonlar ({len(ai_state['active'])})")
    active_symbols = list(ai_state["active"].keys())
    current_prices = fetch_prices(active_symbols, period="5d")

    rows = []
    for symbol, pos in ai_state["active"].items():
        col = to_yf_ticker(symbol)
        current_price = (
            current_prices[col].dropna().iloc[-1] if col in current_prices.columns else None
        )
        days_held = (
            pd.Timestamp.today().date() - pd.Timestamp(pos["giris_tarihi"]).date()
        ).days
        pl_pct = (current_price / pos["giris_fiyati"] - 1) * 100 if current_price else None
        rows.append({
            "Hisse": symbol,
            "Giriş Tarihi": pos["giris_tarihi"],
            "Giriş Fiyatı": pos["giris_fiyati"],
            "Güncel Fiyat": current_price,
            "Kaç Gündür": days_held,
            "%Kâr/Zarar": pl_pct,
            "Hedef Satış": pos["hedef_satis_fiyati"],
            "Tahmini Vade": pos["tahmini_vade"],
            "Sermaye Payı (%)": pos["sermaye_payi_pct"],
            "Gerekçe": pos["gerekce"],
        })
    st.dataframe(pd.DataFrame(rows))
else:
    st.info("Şu an aktif pozisyon yok — hedef fiyatına ulaşan hisse bekleniyor.")

watchlist = ai_state.get("watchlist", {})
if watchlist:
    with st.expander(f"İzleme Listesi ({len(watchlist)}) — hedef fiyatına henüz ulaşmadı"):
        watch_rows = [
            {
                "Hisse": symbol,
                "İzlemeye Alınma": w["eklenme_tarihi"],
                "Hedef Alım Fiyatı": w["hedef_alim_fiyati"],
                "Hedef Satış Fiyatı": w["hedef_satis_fiyati"],
                "Toplam Puan": w["toplam_puan"],
                "Tahmini Vade": w["tahmini_vade"],
            }
            for symbol, w in watchlist.items()
        ]
        st.dataframe(
            pd.DataFrame(watch_rows).sort_values("Toplam Puan", ascending=False).reset_index(drop=True)
        )

if ai_state["closed"]:
    closed_df = pd.DataFrame(ai_state["closed"])
    st.subheader(f"Kapanan İşlemler — Performans ({len(closed_df)} işlem)")

    win_rate = (closed_df["getiri_pct"] > 0).mean() * 100
    avg_return = closed_df["getiri_pct"].mean()
    with_benchmark = closed_df["bist100_getiri_pct"].notna()
    avg_excess = (
        (closed_df.loc[with_benchmark, "getiri_pct"] - closed_df.loc[with_benchmark, "bist100_getiri_pct"]).mean()
        if with_benchmark.any()
        else None
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Kazanma Oranı", f"%{win_rate:.0f}")
    col2.metric("Ortalama Getiri", f"%{avg_return:.1f}")
    col3.metric(
        "BIST100'e Göre Fark",
        f"%{avg_excess:.1f}" if avg_excess is not None else "—",
    )
    st.caption(
        "Az sayıda işlemle bu rakamlar henüz bir şey kanıtlamaz — zamanla işlem "
        "sayısı arttıkça anlamlı hale gelir."
    )

    with st.expander("Tüm kapanan işlemler"):
        st.dataframe(closed_df)

import altair as alt
import pandas as pd
import streamlit as st

from analyzer.backtest import run_momentum_backtest
from analyzer.basket import compute_momentum_table
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

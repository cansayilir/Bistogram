import streamlit as st

from analyzer.basket import compute_momentum_table
from analyzer.universe import BIST_UNIVERSE

st.set_page_config(page_title="Bistogram", page_icon="📊")

st.title("Bistogram")
st.caption("BIST için sıfırdan, kendi yöntemlerimizle geliştirilen analiz sistemi")

st.header("Sepet Motoru — Momentum Sıralaması")
st.write(
    "Aşağıdaki tablo, BIST hisselerini son 1 yıllık performansına göre sıralıyor "
    "(en son 1 ay hariç tutuluyor — kısa vadeli gürültüyü azaltmak için). "
    "En üstteki hisseler bu ölçüye göre son dönemde en güçlü performans gösterenler."
)
st.warning(
    "Bu ilk sürüm sadece anlık bir sıralama gösteriyor — bu kod tabanında henüz "
    "geçmişe dönük olarak ayrıca doğrulanmadı. Bir alım-satım önerisi değil, "
    "sepet motorunun ilk adımı."
)


@st.cache_data(ttl=6 * 60 * 60, show_spinner="BIST verileri çekiliyor...")
def get_momentum_table():
    return compute_momentum_table(BIST_UNIVERSE)


momentum_table = get_momentum_table()

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

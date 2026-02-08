import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="Steam Analytics",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================
# STYLE
# =====================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Public Sans', sans-serif;
    color: #EAEAEA;
}
.stApp { background-color: #0E1117; }
h1, h2, h3 { color: #FFFFFF; }

[data-testid="stSidebar"] {
    background-color: #1A1D24;
}

.kpi-box {
    background-color: #1E222A;
    padding: 20px;
    border-radius: 8px;
    border-top: 4px solid #00D9FF;
}
.kpi-title {
    font-size: 12px;
    color: #9CA3AF;
    font-weight: 700;
}
.kpi-value {
    font-size: 24px;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# LOAD DATA
# =====================================================
@st.cache_data
def load_data():
    harga = pd.read_csv("data_output/harga_popularitas.csv", on_bad_lines="skip")
    genre = pd.read_csv("data_output/game_kontroversi.csv", on_bad_lines="skip")[["appid", "genre"]]
    genre.rename(columns={"genre": "genres"}, inplace=True)

    df = harga.merge(genre, on="appid", how="left")

    df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0)
    df["positive_ratings"] = pd.to_numeric(df["positive_ratings"], errors="coerce").fillna(0)
    df["negative_ratings"] = pd.to_numeric(df["negative_ratings"], errors="coerce").fillna(0)
    df["total_ratings"] = df["positive_ratings"] + df["negative_ratings"]

    df["owners_numeric"] = df["total_ratings"] * 10

    df["negative_ratio"] = np.where(
        df["total_ratings"] > 0,
        df["negative_ratings"] / df["total_ratings"] * 100,
        0
    )

    df["positive_ratio"] = np.where(
        df["total_ratings"] > 0,
        df["positive_ratings"] / df["total_ratings"] * 100,
        0
    )

    try:
        steam = pd.read_csv("steam.csv")[["appid", "release_date"]]
        steam["release_date"] = pd.to_datetime(steam["release_date"], errors="coerce")
        steam["release_year"] = steam["release_date"].dt.year
        df = df.merge(steam[["appid", "release_year"]], on="appid", how="left")
    except:
        df["release_year"] = 2020

    df["game_type"] = df["price"].apply(lambda x: "Free" if x == 0 else "Paid")
    df["primary_genre"] = df["genres"].str.split(";").str[0].fillna("Unknown")

    return df

df = load_data()

# =====================================================
# FILTER FUNCTION
# =====================================================
def apply_filters(
    df,
    year_range=None,
    genres=None,
    game_type=None,
    min_ratings=None,
    price_range=None
):
    temp = df.copy()

    if year_range:
        temp = temp[
            (temp.release_year >= year_range[0]) &
            (temp.release_year <= year_range[1])
        ]

    if genres and "All" not in genres:
        temp = temp[temp.primary_genre.isin(genres)]

    if game_type and game_type != "All":
        temp = temp[temp.game_type == game_type]

    if min_ratings:
        temp = temp[temp.total_ratings >= min_ratings]

    if price_range:
        temp = temp[
            (temp.price >= price_range[0]) &
            (temp.price <= price_range[1])
        ]

    return temp

# =====================================================
# SIDEBAR
# =====================================================
st.sidebar.title("STEAM ANALYTICS")
page = st.sidebar.radio(
    "Navigasi",
    ["Dashboard", "Game Kontroversial", "Harga vs Popularitas", "Popularitas by Tahun Rilis"]
)

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Total Game:** {len(df):,}")
st.sidebar.markdown(
    f"**Periode Data:** {int(df.release_year.min())} – {int(df.release_year.max())}"
)
st.sidebar.markdown("**Sumber Data:** Hadoop MapReduce")

# =====================================================
# DASHBOARD
# =====================================================
if page == "Dashboard":
    st.title("Dashboard Ekosistem Steam")

    st.markdown("""
    Dashboard ini menyajikan gambaran umum ekosistem Steam berdasarkan data hasil pemrosesan Big Data.
    Analisis difokuskan pada skala pasar, struktur model bisnis, serta distribusi genre untuk memahami
    tingkat kompetisi dalam industri game PC.
    """)

    st.markdown("### Filter Data")
    c1, c2, c3 = st.columns(3)

    with c1:
        year_filter = st.slider(
            "Tahun Rilis",
            int(df.release_year.min()),
            int(df.release_year.max()),
            (2015, int(df.release_year.max()))
        )

    with c2:
        genre_filter = st.multiselect(
            "Genre",
            options=["All"] + sorted(df.primary_genre.unique()),
            default=["All"]
        )

    with c3:
        type_filter = st.selectbox(
            "Tipe Game",
            ["All", "Free", "Paid"]
        )
        
    fdf = apply_filters(
        df,
        year_range=year_filter,
        genres=genre_filter,
        game_type=type_filter
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="kpi-box">
            <div class="kpi-title">TOTAL GAME</div>
            <div class="kpi-value">{len(fdf):,}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        avg_price = fdf[fdf.price > 0]["price"].mean()
        st.markdown(f"""
        <div class="kpi-box">
            <div class="kpi-title">HARGA RATA-RATA</div>
            <div class="kpi-value">${avg_price:.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        owners = fdf.owners_numeric.sum() / 1e6
        st.markdown(f"""
        <div class="kpi-box">
            <div class="kpi-title">ESTIMASI PEMILIK</div>
            <div class="kpi-value">{owners:.0f}M</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Free vs Paid
    st.subheader("Distribusi Model Bisnis Game")
    st.markdown("""
    Data menunjukkan perbandingan antara game gratis dan game berbayar yang tersedia di Steam.
    Distribusi ini memberikan gambaran mengenai pendekatan monetisasi yang paling umum digunakan
    oleh developer dalam merilis game mereka.
    """)

    type_dist = fdf.game_type.value_counts().reset_index()
    type_dist.columns = ["Tipe", "Jumlah"]
    
    # Warna: Hijau untuk Free (gratis = positif), Biru untuk Paid (berbayar = netral)
    colors = {'Free': '#10B981', 'Paid': '#3B82F6'}
    fig = px.pie(type_dist, values="Jumlah", names="Tipe", hole=0.4,
                 color="Tipe", color_discrete_map=colors)
    fig.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Insight Analisis"):
        st.markdown("""
        Distribusi model bisnis menunjukkan bahwa game berbayar masih mendominasi jumlah judul
        yang tersedia di Steam. Meskipun game gratis jumlahnya lebih sedikit, model ini sering
        digunakan untuk menjangkau pemain dalam jumlah besar melalui pendekatan tanpa biaya awal.
        Secara keseluruhan, data ini mengindikasikan bahwa pembayaran di awal masih menjadi
        strategi utama developer dalam mendistribusikan game PC.
        
        - Model gratis bersifat selektif dan tidak digunakan oleh sebagian besar game
        - Model berbayar masih dianggap stabil dan berkelanjutan
        """)

    st.markdown("---")


    # Genre
    st.subheader("Distribusi Genre Game")
    st.markdown("""
    Visualisasi ini memperlihatkan genre dengan jumlah game terbanyak di Steam.
    Perbedaan jumlah game antar genre mencerminkan tingkat popularitas dan kepadatan pasar
    pada masing-masing genre.
    """)

    genre = fdf.primary_genre.value_counts().head(10).reset_index()
    genre.columns = ["Genre", "Jumlah"]
    
    # Gradient biru untuk menunjukkan tingkat popularitas
    fig = px.bar(genre, x="Jumlah", y="Genre", orientation="h",
                 color="Jumlah", color_continuous_scale="Blues")
    fig.update_layout(coloraxis_showscale=False)
    fig.update_traces(hovertemplate='<b>%{y}</b><br>Jumlah Game: %{x}<extra></extra>')
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Insight Analisis"):
        st.markdown("""
        Perbedaan jumlah game antar genre menunjukkan tingkat kepadatan pasar yang tidak merata.
        Beberapa genre memiliki jumlah game yang sangat tinggi, yang menandakan persaingan
        yang ketat dan pasar yang sudah matang. Sebaliknya, genre dengan jumlah game lebih sedikit
        berpotensi menawarkan ruang bagi pengembangan game niche dengan kompetisi yang lebih rendah.
        
        - Genre padat menuntut diferensiasi yang lebih kuat
        - Genre kecil berpotensi menjadi peluang strategis
        """)


# =====================================================
# GAME KONTROVERSIAL
# =====================================================
elif page == "Game Kontroversial":
    st.title("Analisis Game Kontroversial")

    st.markdown("""
    Halaman ini berfokus pada game dengan tingkat ulasan negatif yang tinggi.
    Analisis dilakukan untuk mengidentifikasi risiko kualitas dan potensi ketidakpuasan
    pengguna dalam skala besar.
    """)

    # Filter
    st.markdown("### Filter Analisis")
    c1, c2, c3 = st.columns(3)

    with c1:
        min_rating = st.number_input("Minimal Total Ulasan", 50, 1000, 100, 50)

    with c2:
        genre_filter = st.multiselect(
            "Genre",
            ["All"] + sorted(df.primary_genre.unique()),
            default=["All"]
        )

    with c3:
        year_filter = st.slider(
            "Tahun Rilis",
            int(df.release_year.min()),
            int(df.release_year.max()),
            (2010, int(df.release_year.max()))
        )

    # Apply filters
    fdf = apply_filters(
        df,
        year_range=year_filter,
        genres=genre_filter,
        min_ratings=min_rating
    )

    top = fdf.nlargest(15, "negative_ratio")

    st.subheader("Game dengan Rasio Ulasan Negatif Tertinggi")
    st.markdown("""
    Daftar game berikut menunjukkan proporsi ulasan negatif tertinggi dibandingkan total ulasan.
    Rasio ini digunakan sebagai indikator tingkat kontroversi suatu game.
    """)

    fig = go.Figure()
    # Hijau untuk rating positif, Merah untuk rating negatif
    fig.add_bar(y=top.name, x=top.positive_ratings, orientation="h", 
               name="Positif", marker_color='#10B981')
    fig.add_bar(y=top.name, x=top.negative_ratings, orientation="h", 
               name="Negatif", marker_color='#EF4444')
    fig.update_layout(barmode="stack", 
                     xaxis_title="Jumlah Ulasan",
                     yaxis_title="Game",
                     legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Insight Analisis"):
        st.markdown("""
        Dominasi ulasan negatif pada game-game tertentu menunjukkan adanya masalah kualitas
        yang dirasakan oleh banyak pemain. Rasio negatif yang tinggi, terutama pada game dengan
        jumlah ulasan besar, mengindikasikan bahwa permasalahan tersebut bersifat sistemik,
        bukan sekadar preferensi individu. Kondisi ini dapat berdampak pada reputasi developer
        serta kepercayaan pengguna terhadap produk game tersebut.
        
        - Rasio negatif tinggi mencerminkan risiko kualitas
        - Dampaknya lebih signifikan pada game dengan basis pemain besar
        """)

    st.markdown("---")


    st.subheader("Popularitas dan Tingkat Kontroversi")
    st.markdown("""
    Hubungan antara jumlah ulasan dan rasio ulasan negatif memberikan gambaran
    apakah kontroversi bersifat terbatas atau berdampak luas.
    """)

    fig = px.scatter(
        top,
        x="total_ratings",
        y="negative_ratio",
        size="total_ratings",
        color="negative_ratio",
        # Red scale: semakin tinggi rasio negatif, semakin merah
        color_continuous_scale="Reds",
        labels={
            "total_ratings": "Total Ulasan",
            "negative_ratio": "Rasio Negatif (%)"
        }
    )
    fig.update_traces(hovertemplate='<b>%{customdata}</b><br>' +
                     'Total Ulasan: %{x}<br>' +
                     'Rasio Negatif: %{y:.1f}%<extra></extra>',
                     customdata=top.name)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Insight Analisis"):
        st.markdown("""
        Hubungan antara jumlah ulasan dan rasio negatif menunjukkan bahwa tidak semua
        kontroversi memiliki dampak yang sama. Game dengan popularitas tinggi dan rasio negatif
        besar menandakan ketidakpuasan yang meluas, sementara game dengan popularitas rendah
        cenderung memiliki dampak terbatas. Analisis ini membantu membedakan antara masalah
        berskala besar dan isu minor.
        
        - Kontroversi pada game populer memiliki dampak lebih luas
        - Game kecil cenderung memiliki risiko terbatas
        """)


# =====================================================
# HARGA VS POPULARITAS
# =====================================================
elif page == "Harga vs Popularitas":
    st.title("Analisis Harga dan Popularitas Game")

    st.markdown("""
    Analisis ini mengkaji hubungan antara harga game dan jumlah pemain yang dimiliki.
    Tujuannya adalah untuk memahami apakah harga berpengaruh langsung terhadap popularitas.
    """)

    # Filter
    st.markdown("### Filter Harga & Kualitas")
    c1, c2, c3 = st.columns(3)

    with c1:
        price_filter = st.slider(
            "Rentang Harga (USD)",
            0.0,
            float(df.price.max()),
            (0.0, 30.0)
        )

    with c2:
        min_rating = st.number_input("Minimal Total Ulasan", 50, 1000, 100, 50)

    with c3:
        genre_filter = st.multiselect(
            "Genre",
            ["All"] + sorted(df.primary_genre.unique()),
            default=["All"]
        )

    # Apply filters
    fdf = apply_filters(
        df,
        price_range=price_filter,
        min_ratings=min_rating,
        genres=genre_filter
    )

    paid = fdf[fdf.price > 0]
    sample = paid.sample(min(500, len(paid)))

    st.subheader("Hubungan Harga dan Jumlah Pemilik")
    st.markdown("""
    Perbandingan harga dan estimasi jumlah pemilik menunjukkan variasi tingkat adopsi
    pada setiap rentang harga game.
    """)

    fig = px.scatter(
        sample,
        x="price",
        y="owners_numeric",
        size="total_ratings",
        color="positive_ratio",
        log_y=True,
        # Green scale: semakin tinggi rasio positif, semakin hijau
        color_continuous_scale="Greens",
        labels={
            "price": "Harga (USD)",
            "owners_numeric": "Estimasi Pemilik",
            "positive_ratio": "Rasio Positif (%)"
        }
    )
    fig.update_traces(hovertemplate='<b>%{customdata}</b><br>' +
                     'Harga: $%{x}<br>' +
                     'Estimasi Pemilik: %{y:,.0f}<br>' +
                     'Rasio Positif: %{color:.1f}%<extra></extra>',
                     customdata=sample.name)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Insight Analisis"):
        st.markdown("""
        Hubungan antara harga dan jumlah pemilik menunjukkan bahwa harga bukan satu-satunya
        faktor penentu popularitas game. Beberapa game berharga tinggi tetap mampu menarik
        banyak pemain, terutama ketika didukung oleh kualitas dan reputasi yang baik.
        Hal ini menunjukkan bahwa pemain bersedia membayar lebih untuk pengalaman yang
        dianggap bernilai.
        
        - Kualitas berperan penting dalam keberhasilan game premium
        - Harga murah tidak selalu menjamin popularitas tinggi
        """)

    st.markdown("---")


    st.subheader("Performa Berdasarkan Rentang Harga")
    st.markdown("""
    Segmentasi harga digunakan untuk melihat perbedaan rata-rata jumlah pemilik
    pada setiap kategori harga.
    """)

    def price_category(p):
        if p == 0: return "Free"
        if p < 5: return "Budget"
        if p < 15: return "Mid"
        if p < 30: return "Premium"
        return "AAA"

    fdf["price_category"] = fdf.price.apply(price_category)
    grp = fdf.groupby("price_category").owners_numeric.mean().reset_index()
    
    # Warna berbeda untuk setiap kategori harga
    category_colors = {
        'Free': '#10B981',    # Hijau untuk gratis
        'Budget': '#3B82F6',  # Biru untuk budget
        'Mid': '#6366F1',     # Indigo untuk mid
        'Premium': '#8B5CF6', # Purple untuk premium
        'AAA': '#EC4899'      # Pink untuk AAA
    }
    
    fig = px.bar(grp, x="price_category", y="owners_numeric",
                color="price_category", color_discrete_map=category_colors,
                labels={
                    "price_category": "Kategori Harga",
                    "owners_numeric": "Rata-rata Estimasi Pemilik"
                })
    fig.update_layout(showlegend=False)
    fig.update_traces(hovertemplate='<b>%{x}</b><br>Rata-rata Pemilik: %{y:,.0f}<extra></extra>')
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Insight Analisis"):
        st.markdown("""
        Hubungan antara harga dan jumlah pemilik menunjukkan bahwa harga bukan satu-satunya
        faktor penentu popularitas game. Beberapa game berharga tinggi tetap mampu menarik
        banyak pemain, terutama ketika didukung oleh kualitas dan reputasi yang baik.
        Hal ini menunjukkan bahwa pemain bersedia membayar lebih untuk pengalaman yang
        dianggap bernilai.
        
        - Kualitas berperan penting dalam keberhasilan game premium
        - Harga murah tidak selalu menjamin popularitas tinggi
        """)


# =====================================================
# TEMPORAL ANALYSIS
# =====================================================
else:
    st.title("Popularitas Game Berdasarkan Tahun Rilis")

    st.markdown("""
    Analisis temporal digunakan untuk melihat perkembangan industri game PC dari waktu ke waktu.
    Fokus analisis meliputi jumlah rilis dan perubahan kualitas game berdasarkan ulasan pemain.
    """)

    # Filter
    st.markdown("### Filter Temporal")
    c1, c2 = st.columns(2)

    with c1:
        year_filter = st.slider(
            "Rentang Tahun",
            int(df.release_year.min()),
            int(df.release_year.max()),
            (2005, int(df.release_year.max()))
        )

    with c2:
        type_filter = st.selectbox(
            "Tipe Game",
            ["All", "Free", "Paid"]
        )

    # Apply filters
    fdf = apply_filters(
        df,
        year_range=year_filter,
        game_type=type_filter
    )

    yearly = fdf.groupby("release_year").agg(
        games=("appid", "count"),
        owners=("owners_numeric", "sum"),
        pos=("positive_ratings", "sum"),
        neg=("negative_ratings", "sum")
    ).reset_index()

    yearly["positive_ratio"] = yearly.pos / (yearly.pos + yearly.neg) * 100

    st.subheader("Jumlah Game Dirilis per Tahun")
    st.markdown("""
    Perubahan jumlah rilis per tahun mencerminkan dinamika pertumbuhan dan tingkat kejenuhan pasar.
    Peningkatan rilis dapat meningkatkan kompetisi antar game.
    """)

    fig = px.area(yearly, x="release_year", y="games",
                 color_discrete_sequence=['#00D9FF'],  # Brand color
                 labels={
                     "release_year": "Tahun Rilis",
                     "games": "Jumlah Game"
                 })
    fig.update_traces(hovertemplate='<b>%{x}</b><br>Jumlah Game: %{y}<extra></extra>')
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Insight Analisis"):
        st.markdown("""
        Segmentasi harga menunjukkan perbedaan performa yang cukup jelas antar kategori.
        Segmen harga menengah cenderung memiliki keseimbangan terbaik antara jumlah pemain
        dan kualitas game. Sementara itu, game dengan harga sangat tinggi membutuhkan
        kualitas yang sebanding agar tetap diminati oleh pemain.
        
        - Harga menengah cenderung paling stabil
        - Harga tinggi menuntut kualitas yang konsisten
        """)

    st.markdown("---")


    st.subheader("Tren Kualitas Game dari Waktu ke Waktu")
    st.markdown("""
    Rasio ulasan positif digunakan sebagai indikator kualitas game pada setiap tahun rilis.
    Perubahan nilai ini menunjukkan stabilitas atau penurunan kualitas industri.
    """)

    fig = px.line(yearly, x="release_year", y="positive_ratio",
                 color_discrete_sequence=['#10B981'],  # Hijau untuk kualitas positif
                 labels={
                     "release_year": "Tahun Rilis",
                     "positive_ratio": "Rasio Ulasan Positif (%)"
                 })
    fig.update_traces(line=dict(width=3),
                     hovertemplate='<b>%{x}</b><br>Rasio Positif: %{y:.1f}%<extra></extra>')
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Insight Analisis"):
        st.markdown("""
        Tren rilis game per tahun menunjukkan peningkatan signifikan setelah tahun 2015.
        Kondisi ini mencerminkan rendahnya hambatan masuk industri game PC serta meningkatnya
        jumlah developer. Akibatnya, tingkat kompetisi semakin tinggi dan pasar menjadi lebih padat.
        
        - Peningkatan rilis berpotensi menyebabkan oversupply
        - Game baru semakin sulit mendapatkan perhatian
        """)


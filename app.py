
import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Dashboard Detail Tiket", layout="wide")

# ==================================
# 🔄 Refresh data manual
# ==================================
if st.button("🔄 Refresh Data dari Google Sheet"):
    st.cache_data.clear()
    st.success("✅ Data berhasil di-refresh. Silakan tekan Ctrl+R untuk memuat ulang.")

# ==================================
# 📥 Load data
# ==================================
@st.cache_data
def load_data():
    url = "https://docs.google.com/spreadsheets/d/1gzds45lEjsxycC1h_Wji6Cvq-TamQsx-J5rjXaT1rS0/gviz/tq?tqx=out:csv&gid=2000809130"
    df = pd.read_csv(url)
    df["Created Date"] = pd.to_datetime(df["Created Date"], errors='coerce', dayfirst=True)
    df["Finish Date"] = pd.to_datetime(df["Finish Date"], errors='coerce', dayfirst=True)
    return df

df = load_data()

# ==================================
# 🎛️ Sidebar filters
# ==================================
with st.sidebar:
    st.header("🔍 Filter")

    service_options = ["All"] + sorted(df["Services"].dropna().unique().tolist())
    service_filter = st.selectbox("📄 Pilih Services", options=service_options)

    # Mode filter
    filter_type = st.radio("🎯 Mode Filter Tanggal", ["Per Hari", "Per Bulan"], horizontal=True)

    if filter_type == "Per Hari":
        min_date = df["Created Date"].min().date()
        max_date = df["Created Date"].max().date()
        date_range = st.date_input(
            "📅 Pilih Rentang Tanggal",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
    else:  # Per Bulan
        tahun_opsi = sorted(df["Created Date"].dt.year.unique())
        selected_year = st.selectbox("📅 Pilih Tahun", options=tahun_opsi)

        bulan_opsi = {
            1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
            7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"
        }

        bulan_di_data = df[df["Created Date"].dt.year == selected_year]["Created Date"].dt.month.unique()
        bulan_tersedia = [b for b in bulan_opsi if b in bulan_di_data]

        selected_month = st.selectbox("📅 Pilih Bulan", options=bulan_tersedia, format_func=lambda x: bulan_opsi[x])

# ==================================
# 📊 Filter data
# ==================================
if filter_type == "Per Hari":
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date = pd.to_datetime(date_range[0])
        end_date = pd.to_datetime(date_range[1]) + pd.Timedelta(days=1)
    else:
        st.warning("⚠️ Silakan pilih rentang tanggal yang lengkap (mulai dan akhir).")
        st.stop()
else:
    start_date = pd.to_datetime(f"{selected_year}-{selected_month:02d}-01")
    end_date = start_date + pd.DateOffset(months=1)

filtered_df = df[(df["Created Date"] >= start_date) & (df["Created Date"] < end_date)]

if service_filter != "All":
    filtered_df = filtered_df[filtered_df["Services"] == service_filter]

# ==================================
# 🧾 Tampilan Ringkasan & Analisis
# ==================================
st.title("📊 Dashboard Detail Tiket")

if service_filter == "All":
    st.subheader("📈 Ringkasan Total Tiket per Kategori")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Issue", len(filtered_df[filtered_df["Services"] == "Issue"]))
    col2.metric("Total Request", len(filtered_df[filtered_df["Services"] == "Request"]))
    col3.metric("Total Question", len(filtered_df[filtered_df["Services"] == "Question"]))
    col4.metric("Total Task", len(filtered_df[filtered_df["Services"] == "Task"]))

    st.markdown("---")
    st.subheader("📌 Top 5 Tags untuk Setiap Jenis Services")

    kategori_list = ["Issue", "Request", "Question", "Task"]
    cols = st.columns(4)

    for i, kategori in enumerate(kategori_list):
        with cols[i % 4]:
            st.write("")
            st.markdown(f"**🔸 Top 5 Tags untuk {kategori}:**")
            sub_df = filtered_df[filtered_df["Services"] == kategori]
            if "Tags" in sub_df.columns and not sub_df.empty:
                top_tags = sub_df["Tags"].value_counts().head(5)
                for idx, (tag, count) in enumerate(top_tags.items(), 1):
                    st.write(f"{idx}. {tag} ({count} tiket)")
            else:
                st.info(f"Tidak ada data untuk kategori {kategori}")

    st.markdown("---")
    st.subheader("📌 Top 5 Company berdasarkan Services")
    service_list = ['Issue', 'Request', 'Question', 'Task']
    cols = st.columns(2)

    for i, service in enumerate(service_list):
        with cols[i % 2]:
            st.write("")
            st.markdown(f"**🏢 Top 5 Company berdasarkan {service}:**")
            df_service = filtered_df[filtered_df["Services"] == service]
            top_companies = df_service["Company"].value_counts().head(5)
            for i, (company, count) in enumerate(top_companies.items(), 1):
                st.markdown(f"{i}. {company} ({count} tiket)")

else:
    # Tampilan khusus jika service_filter dipilih, misalnya hanya "Issue"
    st.subheader(f"📌 Daftar Semua Tags untuk Service: {service_filter}")
    st.markdown(f"**Total Tiket untuk Service `{service_filter}`:** {len(filtered_df)} tiket")
    tag_limit_option = st.selectbox(
    "Tampilkan jumlah tag:",
    options=["All Tags", "Top 5", "Top 10", "Top 20"])

    tag_counts = filtered_df["Tags"].value_counts()
    if "Tags" in filtered_df.columns and filtered_df["Tags"].notna().sum() > 0:
        tag_counts = filtered_df["Tags"].value_counts()
        if not tag_counts.empty:
            cols = st.columns(4)
            if tag_limit_option == "Top 5":
                tag_items = list(tag_counts.items())[:5]
            elif tag_limit_option == "Top 10":
                tag_items = list(tag_counts.items())[:10]
            elif tag_limit_option == "Top 20":
                tag_items = list(tag_counts.items())[:20]
            else:  # All Tags
                tag_items = list(tag_counts.items())

            for i, (tag, count) in enumerate(tag_items):
                with cols[i % 4]:
                    st.write(f"{i+1}. {tag} ({count} tiket)")
        else:
            st.info(f"Tidak ada data Tags yang valid untuk service **{service_filter}**.")
    else:
        st.info(f"Tidak ditemukan kolom Tags atau seluruh nilainya kosong untuk service **{service_filter}**.")

    st.markdown("---")
    st.subheader(f"🧾 Tabel Detail Tiket untuk Service: {service_filter}")
    st.dataframe(filtered_df.sort_values(by="Tags", ascending=True))

# ==================================
# 📊 Tampilan Grafik Interaktif (khusus Services = All)
# ==================================
if service_filter == "All":
    st.markdown("---")
    st.subheader("📈 Grafik Analisis Berdasarkan Pilihan")

    tab_grafik = st.tabs(["📊 Grafik Berdasarkan Tags", "🏢 Grafik Berdasarkan Company"])

    with tab_grafik[0]:
        all_tags = filtered_df["Tags"].dropna().unique().tolist()

        # Simpan pilihan sebelumnya di session state
        if "selected_tag" not in st.session_state:
            st.session_state.selected_tag = all_tags[0] if all_tags else None

        if st.session_state.selected_tag not in all_tags:
            st.session_state.selected_tag = all_tags[0] if all_tags else None

        selected_tag = st.selectbox(
            "Pilih Tag...",
            options=all_tags,
            index=all_tags.index(st.session_state.selected_tag) if st.session_state.selected_tag in all_tags else 0,
            key="selected_tag")

        df_tag = filtered_df[filtered_df["Tags"] == selected_tag].copy()
        df_tag["Tanggal"] = df_tag["Created Date"].dt.date
        tag_summary = df_tag.groupby("Tanggal").size().reset_index(name="Jumlah Tiket")

        if tag_summary.empty:
            st.info("Tidak ada data untuk tag ini pada periode yang dipilih.")
        else:
            chart = alt.Chart(tag_summary).mark_line(point=True).encode(
                x='Tanggal:T',
                y='Jumlah Tiket:Q'
            ) + alt.Chart(tag_summary).mark_text(
                align='center',
                baseline='bottom',
                dy=-5  # geser ke atas
            ).encode(
                x='Tanggal:T',
                y='Jumlah Tiket:Q',
                text='Jumlah Tiket:Q'
            )

            st.altair_chart(chart, use_container_width=True)

    with tab_grafik[1]:
        all_companies = filtered_df["Company"].dropna().unique().tolist()

        # Simpan state pilihan sebelumnya
        if "selected_company" not in st.session_state:
            st.session_state.selected_company = all_companies[0] if all_companies else None

        # Hanya ubah jika tidak ada di daftar
        if st.session_state.selected_company not in all_companies:
            st.session_state.selected_company = all_companies[0] if all_companies else None

        selected_company = st.selectbox(
            "Pilih Company...",
            options=all_companies,
            index=all_companies.index(st.session_state.selected_company) if st.session_state.selected_company in all_companies else 0,
            key="selected_company")

        df_comp = filtered_df[filtered_df["Company"] == selected_company].copy()
        df_comp["Tanggal"] = df_comp["Created Date"].dt.date
        comp_summary = df_comp.groupby("Tanggal").size().reset_index(name="Jumlah Tiket")

        if comp_summary.empty:
            st.info("Tidak ada data untuk company ini pada periode yang dipilih.")
        else:
            chart = alt.Chart(comp_summary).mark_line(point=True).encode(
                x='Tanggal:T',
                y='Jumlah Tiket:Q'
            ) + alt.Chart(comp_summary).mark_text(
                align='center',
                baseline='bottom',
                dy=-5  # geser ke atas
            ).encode(
                x='Tanggal:T',
                y='Jumlah Tiket:Q',
                text='Jumlah Tiket:Q'
            )

            st.altair_chart(chart, use_container_width=True)

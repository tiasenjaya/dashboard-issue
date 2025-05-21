
import streamlit as st
import pandas as pd

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
    url = "https://docs.google.com/spreadsheets/d/1gzds45lEjsxycC1h_Wji6Cvq-TamQsx-J5rjXaT1rS0/gviz/tq?tqx=out:csv&gid=501506018"
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
    service_filter = st.selectbox("Pilih Services", options=service_options)

    min_date = df["Created Date"].min().date()
    max_date = df["Created Date"].max().date()

    date_range = st.date_input(
        "📅 Pilih Rentang Tanggal",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

# ==================================
# 📊 Filter data
# ==================================
start_date = pd.to_datetime(date_range[0])
end_date = pd.to_datetime(date_range[1]) + pd.Timedelta(days=1)

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
            
            df_service = df[df["Services"] == service]
            top_companies = df_service["Company"].value_counts().head(5)

            for i, (company, count) in enumerate(top_companies.items(), 1):
                st.markdown(f"{i}. {company} ({count} tiket)")
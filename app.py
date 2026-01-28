import streamlit as st
import pandas as pd
import altair as alt
import datetime
import math
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

st.set_page_config(page_title="Dashboard Detail Tiket", layout="wide")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

def _get_sheet_title_by_gid(service, spreadsheet_id: str, sheet_gid: int) -> str:
    meta = service.spreadsheets().get(
        spreadsheetId=spreadsheet_id,
        fields="sheets(properties(sheetId,title))",
    ).execute()

    for s in meta.get("sheets", []):
        props = s.get("properties", {})
        if int(props.get("sheetId", -1)) == int(sheet_gid):
            return props.get("title")

    raise ValueError(f"GID sheet {sheet_gid} tidak ditemukan di spreadsheet {spreadsheet_id}")

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
    # ambil dari Streamlit Secrets
    spreadsheet_id = st.secrets["SPREADSHEET_ID"]
    sheet_gid = int(st.secrets["SHEET_GID"])

    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES,
    )
    service = build("sheets", "v4", credentials=creds, cache_discovery=False)

    sheet_title = _get_sheet_title_by_gid(service, spreadsheet_id, sheet_gid)

    values = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=sheet_title)
        .execute()
        .get("values", [])
    )

    if not values:
        return pd.DataFrame()

    header = [h.strip() for h in values[0]]
    rows = values[1:]

    # rapihin panjang kolom biar konsisten
    max_len = len(header)
    fixed_rows = []
    for r in rows:
        r = r[:max_len] + [""] * max(0, max_len - len(r))
        fixed_rows.append(r)

    df = pd.DataFrame(fixed_rows, columns=header)

    # buang baris kosong (Sheets API sering ngasih empty string)
    df = df.replace({"": None}).dropna(how="all")

    # parse tanggal kalau kolomnya ada
    if "Created Date" in df.columns:
        df["Created Date"] = pd.to_datetime(df["Created Date"], errors="coerce", dayfirst=True)
    if "Finish Date" in df.columns:
        df["Finish Date"] = pd.to_datetime(df["Finish Date"], errors="coerce", dayfirst=True)

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
    filter_type = st.radio("🎯 Mode Filter Tanggal", ["Per Hari", "Per Bulan", "Per Tahun"], horizontal=True)

    if filter_type == "Per Hari":
        min_date = df["Created Date"].min().date()
        max_date = df["Created Date"].max().date()
        # Ambil tahun dan bulan pertama dari data
        first_date = df["Created Date"].min().date()
        default_start = datetime.date(first_date.year, first_date.month, 1)

        # Hanya set default 1 hari saja
        date_range = st.date_input(
            "📅 Pilih Rentang Tanggal",
            value=(default_start, default_start),
            min_value=min_date,
            max_value=max_date
        )

    elif filter_type == "Per Bulan":
        tahun_opsi = sorted(df["Created Date"].dt.year.unique())
        selected_year = st.selectbox("📅 Pilih Tahun", options=tahun_opsi)

        bulan_opsi = {
            1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
            7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"
        }

        bulan_di_data = df[df["Created Date"].dt.year == selected_year]["Created Date"].dt.month.unique()
        bulan_tersedia = [b for b in bulan_opsi if b in bulan_di_data]

        selected_month = st.selectbox("📅 Pilih Bulan", options=bulan_tersedia, format_func=lambda x: bulan_opsi[x])
        start_date = pd.to_datetime(f"{selected_year}-{selected_month:02d}-01")
        end_date = pd.to_datetime(f"{selected_year}-{selected_month:02d}-01") + pd.offsets.MonthEnd(1)
        end_date += pd.Timedelta(days=1)

    elif filter_type == "Per Tahun":
        tahun_opsi = sorted(df["Created Date"].dt.year.unique())
        selected_year = st.selectbox("📅 Pilih Tahun", options=tahun_opsi)

        bulan_opsi = {
            1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
            7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"
        }

        bulan_di_data = df[df["Created Date"].dt.year == selected_year]["Created Date"].dt.month.unique()
        bulan_tersedia = [b for b in bulan_opsi if b in bulan_di_data]

        selected_months = st.multiselect("📅 Pilih Bulan", options=bulan_tersedia,
                                default=bulan_tersedia, format_func=lambda x: bulan_opsi[x])
        if selected_months:
            start_month = min(selected_months)
            end_month = max(selected_months)
            start_date = pd.to_datetime(f"{selected_year}-{start_month:02d}-01")
            end_date = pd.to_datetime(f"{selected_year}-{end_month:02d}-01") + pd.offsets.MonthEnd(1)
            end_date += pd.Timedelta(days=1)
        else:
            st.warning("⚠️ Silakan pilih minimal satu bulan.")
            st.stop()

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

elif filter_type == "Per Bulan":
    start_date = pd.to_datetime(f"{selected_year}-{selected_month:02d}-01")
    end_date = pd.to_datetime(f"{selected_year}-{selected_month:02d}-01") + pd.offsets.MonthEnd(1)
    end_date += pd.Timedelta(days=1)

elif filter_type == "Per Tahun":
    if selected_months:
        start_month = min(selected_months)
        end_month = max(selected_months)
        start_date = pd.to_datetime(f"{selected_year}-{start_month:02d}-01")
        end_date = pd.to_datetime(f"{selected_year}-{end_month:02d}-01") + pd.offsets.MonthEnd(1)
        end_date += pd.Timedelta(days=1)
    else:
        st.warning("⚠️ Pilih minimal satu bulan untuk mode Per Tahun.")
        st.stop()

# ==================================
# 🧾 Tampilan Ringkasan & Analisis
# ==================================
st.title("📊 Dashboard Detail Tiket")
filtered_df = df[(df["Created Date"] >= start_date) & (df["Created Date"] < end_date)]

if service_filter != "All":
    filtered_df = filtered_df[filtered_df["Services"] == service_filter]


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
            
            if not df_service.empty and "Company" in df_service.columns:
                top_companies = df_service["Company"].value_counts().head(5)
                if not top_companies.empty:
                    for i, (company, count) in enumerate(top_companies.items(), 1):
                        st.markdown(f"{i}. {company} ({count} tiket)")
                else:
                    st.info(f"❌ Tidak ada data data Company {service}")
            else:
                st.info(f"❌ Tidak ada data data Company {service}")

else:
    # Tampilan khusus jika service_filter dipilih, misalnya hanya "Issue"
    st.subheader(f"📌 Daftar Semua Tags untuk Service: {service_filter}")
    st.markdown(f"**Total Tiket untuk Service `{service_filter}`:** {len(filtered_df)} tiket")
    # Pilihan Mode Analisis
    mode_filter = st.radio("Mode Tampilan:", ["📊 Semua Company", "🏢 Spesifik Company"], horizontal=True)

    # Jika pilih company spesifik, tampilkan pilihan company
    if mode_filter == "🏢 Spesifik Company":
        company_list = (
            filtered_df["Company"]
            .dropna()
            .value_counts()
            .sort_values(ascending=False)
            .index.tolist()
        )
          
        if "selected_specific_company" not in st.session_state:
            st.session_state.selected_specific_company = company_list[0] if company_list else None

        if st.session_state.selected_specific_company not in company_list:
            st.session_state.selected_specific_company = company_list[0] if company_list else None

        selected_company = st.selectbox(
            "Pilih Company:",
            options=company_list,
            index=company_list.index(st.session_state.selected_specific_company) if st.session_state.selected_specific_company in company_list else 0,
            key="selected_specific_company"
        )
        tag_data = filtered_df[filtered_df["Company"] == selected_company]
        # Simpan state agar grafik dan tabel ikut menyesuaikan
        filtered_df = filtered_df[filtered_df["Company"] == selected_company]

    else:
        tag_data = filtered_df.copy()

    tag_limit_option = st.selectbox(
    "Tampilkan jumlah tag:",
    options=["All Tags", "Top 5", "Top 10", "Top 20"])

    if "Tags" in filtered_df.columns and filtered_df["Tags"].notna().sum() > 0:
        tag_counts = tag_data["Tags"].value_counts()
        if not tag_counts.empty:
            cols = st.columns(4)
            if tag_limit_option == "Top 5":
                tag_items = list(tag_counts.items())[:5]
            elif tag_limit_option == "Top 10":
                tag_items = list(tag_counts.items())[:10]
            elif tag_limit_option == "Top 20":
                tag_items = list(tag_counts.items())[:20]
            else:
                tag_items = list(tag_counts.items())

            st.session_state.current_tag_items = tag_items

            # Tampilkan tag_items
            n_cols = 4
            cols = st.columns(n_cols)
            n_items = len(tag_items)
            n_rows = math.ceil(n_items / n_cols)

            for row_idx in range(n_rows):
                for col_idx in range(n_cols):
                    idx = row_idx + col_idx * n_rows
                    if idx < n_items:
                        tag, count = tag_items[idx]
                        with cols[col_idx]:
                            st.write(f"{idx + 1}. {tag} ({count} tiket)")
        else:
            st.session_state.current_tag_items = []
            st.info(f"Tidak ada data Tags yang valid untuk service **{service_filter}**.")
    else:
        st.session_state.current_tag_items = []
        st.info(f"Tidak ditemukan kolom Tags atau seluruh nilainya kosong untuk service **{service_filter}**.")

st.markdown("---")
if service_filter !="All":
    st.subheader(f"🧾 Tabel Detail Tiket untuk Service: {service_filter}")
    st.markdown("### 🎯 Filter Detail Berdasarkan Tags & Company")

    filter_mode = st.selectbox(
        "Pilih jenis filter detail:",
        ["Tampilkan Semua", "Filter berdasarkan Tag", "Filter berdasarkan Company", "Filter berdasarkan Keduanya"])

    detail_df = filtered_df.copy()

    if filter_mode == "Filter berdasarkan Tag":
        tag_items_from_session = st.session_state.get("current_tag_items", [])

        # Ambil hanya nama tag dari hasil top N
        available_tags = [tag for tag, _ in tag_items_from_session]

        # Jika list kosong, fallback ke semua tags agar tidak error
        if not available_tags:
            available_tags = (
                filtered_df["Tags"]
                .dropna()
                .value_counts()
                .sort_values(ascending=False)
                .index.tolist()
            )

        selected_tag = st.selectbox("Pilih Tag:", options=available_tags)
        detail_df = detail_df[detail_df["Tags"] == selected_tag]

    elif filter_mode == "Filter berdasarkan Company":
        available_companies = (
            filtered_df["Company"]
            .dropna()
            .value_counts()
            .sort_values(ascending=False)
            .index.tolist()
        )

        selected_company = st.selectbox("Pilih Company:", options=available_companies)
        detail_df = detail_df[detail_df["Company"] == selected_company]

    elif filter_mode == "Filter berdasarkan Keduanya":
        available_tags = (
            filtered_df["Tags"]
            .dropna()
            .value_counts()
            .sort_values(ascending=False)
            .index.tolist()
        )

        available_companies = (
            filtered_df["Company"]
            .dropna()
            .value_counts()
            .sort_values(ascending=False)
            .index.tolist()
        )

        selected_tag = st.selectbox("Pilih Tag:", options=available_tags)
        selected_company = st.selectbox("Pilih Company:", options=available_companies)

        detail_df = detail_df[
            (detail_df["Tags"] == selected_tag) &
            (detail_df["Company"] == selected_company)]

    if detail_df.empty:
        st.info(f"Tidak ada data detail tiket untuk service **{service_filter}** pada periode yang dipilih.")
    else:
        st.dataframe(detail_df.sort_values(by="Tags", ascending=True))

# ===============================
# 📈 Tampilan Grafik Interaktif (untuk semua pilihan Services)
# ===============================
st.markdown("---")
st.subheader("📈 Grafik Analisis Berdasarkan Pilihan")

tab_grafik = st.tabs(["📊 Grafik Berdasarkan Tags", "🏢 Grafik Berdasarkan Company"])

# Gunakan grafik_df sebagai basis, copy dari filtered_df
grafik_df = filtered_df.copy()

with tab_grafik[0]:
    all_tags = (
    grafik_df["Tags"]
    .dropna()
    .value_counts()
    .sort_values(ascending=False)
    .index.tolist()
    )


    if "selected_tag" not in st.session_state:
        st.session_state.selected_tag = all_tags[0] if all_tags else None

    if st.session_state.selected_tag not in all_tags:
        st.session_state.selected_tag = all_tags[0] if all_tags else None

    selected_tag = st.selectbox(
        "Pilih Tag...",
        options=all_tags,
        index=all_tags.index(st.session_state.selected_tag) if st.session_state.selected_tag in all_tags else 0,
        key="selected_tag"
    )

    bulan_opsi = {
        1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
        7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"
    }

    bulan_order = list(bulan_opsi.values())

    df_tag = grafik_df[grafik_df["Tags"] == selected_tag].copy()

    if filter_type == "Per Hari":
        df_tag["Tanggal"] = df_tag["Created Date"]
        x_type = "temporal"
        x_sort = None
    elif filter_type == "Per Bulan":
        df_tag["Tanggal"] = df_tag["Created Date"].dt.day
        x_type = "ordinal"
        x_sort = None
    else:  # Per Tahun
        df_tag["Tanggal"] = df_tag["Created Date"].dt.month
        df_tag["Tanggal"] = df_tag["Tanggal"].map(lambda x: bulan_opsi.get(x, str(x)))
        x_type = "nominal"
        x_sort = bulan_order

    tag_summary = df_tag.groupby("Tanggal").size().reset_index(name="Jumlah Tiket")

    if tag_summary.empty:
        st.info("Tidak ada data untuk tag ini pada periode yang dipilih.")
    else:
        chart = alt.Chart(tag_summary).mark_line(point=True).encode(
            x=alt.X("Tanggal", type=x_type, sort=x_sort),
            y=alt.Y("Jumlah Tiket:Q", scale=alt.Scale(domainMin=tag_summary["Jumlah Tiket"].min() * 0.9))
        ) + alt.Chart(tag_summary).mark_text(
            align="center",
            baseline="bottom",
            dy=-5
        ).encode(
            x=alt.X("Tanggal", type=x_type, sort=x_sort),
            y="Jumlah Tiket:Q",
            text="Jumlah Tiket:Q"
        )
        st.altair_chart(chart, use_container_width=True)

all_companies = (
    grafik_df["Company"]
    .dropna()
    .value_counts()
    .sort_values(ascending=False)
    .index.tolist()
)

if "selected_company" not in st.session_state:
    st.session_state.selected_company = all_companies[0] if all_companies else None

if st.session_state.selected_company not in all_companies:
    st.session_state.selected_company = all_companies[0] if all_companies else None

with tab_grafik[1]:
    all_companies = (
    grafik_df["Company"]
    .dropna()
    .value_counts()
    .sort_values(ascending=False)
    .index.tolist()
)

    if "selected_company" not in st.session_state:
        st.session_state.selected_company = all_companies[0] if all_companies else None

    if st.session_state.selected_company not in all_companies:
        st.session_state.selected_company = all_companies[0] if all_companies else None

    selected_company = st.selectbox(
        "Pilih Company:",
        options=all_companies,
        index=all_companies.index(st.session_state.selected_company) if st.session_state.selected_company in all_companies else 0,
        key="selected_company"
    )

    bulan_opsi = {
        1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
        7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"
    }

    bulan_order = list(bulan_opsi.values())

    df_company = grafik_df[grafik_df["Company"] == selected_company].copy()

    if filter_type == "Per Hari":
        df_company["Tanggal"] = df_company["Created Date"]
        x_type = "temporal"
        x_sort = None
    elif filter_type == "Per Bulan":
        df_company["Tanggal"] = df_company["Created Date"].dt.day
        x_type = "ordinal"
        x_sort = None
    else:  # Per Tahun
        df_company["Tanggal"] = df_company["Created Date"].dt.month
        df_company["Tanggal"] = df_company["Tanggal"].map(lambda x: bulan_opsi.get(x, str(x)))
        x_type = "nominal"
        x_sort = bulan_order

    company_summary = df_company.groupby("Tanggal").size().reset_index(name="Jumlah Tiket")

    if company_summary.empty:
        st.info("Tidak ada data untuk company ini pada periode yang dipilih.")
    else:
        chart = alt.Chart(company_summary).mark_line(point=True).encode(
            x=alt.X("Tanggal", type=x_type, sort=x_sort),
            y=alt.Y("Jumlah Tiket:Q", scale=alt.Scale(domainMin=company_summary["Jumlah Tiket"].min() * 0.9))
        ) + alt.Chart(company_summary).mark_text(
            align="center",
            baseline="bottom",
            dy=-5
        ).encode(
            x=alt.X("Tanggal", type=x_type, sort=x_sort),
            y="Jumlah Tiket:Q",
            text="Jumlah Tiket:Q"
        )
        st.altair_chart(chart, use_container_width=True)

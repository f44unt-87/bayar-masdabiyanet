import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_searchbox import st_searchbox

# Setup Halaman
st.set_page_config(page_title="BAYAR-MASDABIYANET", layout="centered")
st.title("💰 MASDABIYANET")

# Koneksi Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Fungsi Pencarian Nama untuk Searchbox
def search_customer(search_term: str):
    if not search_term:
        return []
    try:
        # Membaca data nama dari Sheets (Cache 5 menit)
        df_names = conn.read(ttl="5m")
        all_names = df_names['Nama'].dropna().unique().tolist()
        matches = [name for name in all_names if search_term.lower() in name.lower()]
        return matches
    except:
        return []

# --- 1. INPUT NAMA ---
nama_pilihan = st_searchbox(
    search_customer,
    label="NAMA PELANGGAN",
    placeholder="Ketik nama (contoh: joko)...",
    key="customer_search",
    edit_after_submit=True, 
)

if not nama_pilihan:
    nama = st.session_state.get("customer_search", {}).get("search", "")
else:
    nama = nama_pilihan

# --- 2. FORM DATA PEMBAYARAN ---
with st.form("form_bayar"):
    tgl = st.date_input("TANGGAL BAYAR")
    tagihan = st.selectbox("TAGIHAN", [150000, 200000, 250000, 300000])
    submit = st.form_submit_button("SIMPAN")

# Proses Simpan Data
if submit:
    if not nama or nama.strip() == "":
        st.error("Silakan isi nama pelanggan terlebih dahulu!")
    else:
        df = conn.read(ttl="0")
        df = df.astype(object)
        
        tgl_str = tgl.strftime("%d/%m/%Y")
        bulan = tgl.strftime("%b").lower()
        
        mapping = {'may': 'mei', 'aug': 'agu', 'oct': 'okt', 'dec': 'des'}
        if bulan in mapping: bulan = mapping[bulan]
        
        if nama in df['Nama'].values:
            idx = df.index[df['Nama'] == nama][0]
            df.at[idx, 'Tanggal Bayar'] = tgl_str
            df.at[idx, 'Tagihan'] = tagihan
            df.at[idx, bulan] = tgl_str
            st.success(f"Data {nama} diperbarui!")
        else:
            new_row = {"Nama": nama, "Tanggal Bayar": tgl_str, "Tagihan": tagihan, bulan: tgl_str}
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            st.success(f"Pelanggan {nama} baru ditambahkan!")
        
        conn.update(data=df)

# --- 3. TAMPILAN DATA KESELURUHAN ---
st.markdown("---") # Garis pembatas
if st.button("📊 TAMPILKAN DATA PELANGGAN"):
    try:
        # Mengambil data terbaru tanpa cache
        df_view = conn.read(ttl="0")
        
        if not df_view.empty:
            st.subheader("Data Keseluruhan Pelanggan")
            # Menampilkan tabel yang bisa di-scroll dan difilter
            st.dataframe(df_view, use_container_width=True)
            
            # Opsional: Ringkasan singkat
            st.info(f"Total Pelanggan Terdaftar: {len(df_view)} orang")
        else:
            st.warning("Database masih kosong.")
    except Exception as e:
        st.error(f"Gagal mengambil data: {e}")

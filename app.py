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

# Fungsi Pencarian Nama (Tetap sama)
def search_customer(search_term: str):
    if not search_term: return []
    try:
        df_names = conn.read(ttl="5m")
        all_names = df_names['Nama'].dropna().unique().tolist()
        return [name for name in all_names if search_term.lower() in name.lower()]
    except: return []

# --- 1. INPUT NAMA ---
nama_pilihan = st_searchbox(
    search_customer,
    label="NAMA PELANGGAN",
    placeholder="Ketik nama...",
    key="customer_search",
)
nama = nama_pilihan if nama_pilihan else st.session_state.get("customer_search", {}).get("search", "")

# --- 2. FORM DATA PEMBAYARAN ---
with st.form("form_bayar"):
    tgl = st.date_input("TANGGAL BAYAR")
    tagihan = st.selectbox("TAGIHAN", [150000, 200000, 250000, 300000])
    submit = st.form_submit_button("SIMPAN & BUAT NOTA")

# Proses Simpan Data
if submit:
    if not nama or nama.strip() == "":
        st.error("Silakan isi nama pelanggan terlebih dahulu!")
    else:
        df = conn.read(ttl="0")
        df = df.astype(object)
        
        tgl_str = tgl.strftime("%d/%m/%Y")
        bulan_key = tgl.strftime("%b").lower()
        mapping = {'may': 'mei', 'aug': 'agu', 'oct': 'okt', 'dec': 'des'}
        bulan_indo = mapping.get(bulan_key, bulan_key)
        
        # Update/Insert Data
        if nama in df['Nama'].values:
            idx = df.index[df['Nama'] == nama][0]
            df.at[idx, 'Tanggal Bayar'] = tgl_str
            df.at[idx, 'Tagihan'] = tagihan
            df.at[idx, bulan_indo] = tgl_str
            pesan = f"Data {nama} diperbarui!"
        else:
            new_row = {"Nama": nama, "Tanggal Bayar": tgl_str, "Tagihan": tagihan, bulan_indo: tgl_str}
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            pesan = f"Pelanggan {nama} baru ditambahkan!"
        
        conn.update(data=df)
        st.success(pesan)

        # --- FITUR CETAK NOTA ---
        st.markdown("---")
        st.subheader("🧾 Nota Pembayaran")
        
        # Menyusun format nota (Plain Text)
        nota_teks = f"""
================================
       MASDABIYANET
================================
Tanggal  : {tgl_str}
Nama     : {nama.upper()}
Layanan  : Internet Bulanan
Total    : Rp {tagihan:,}
Status   : LUNAS
================================
   Terima Kasih Atas
     Pembayaran Anda
================================
        """
        
        # Menampilkan pratinjau nota di kotak kode
        st.code(nota_teks)
        
        # Tombol Download Nota sebagai File .txt
        st.download_button(
            label="💾 Download Nota (.txt)",
            data=nota_teks,
            file_name=f"Nota_{nama}_{tgl_str}.txt",
            mime="text/plain"
        )

# --- 3. TAMPILAN DATA KESELURUHAN ---
st.markdown("---")
if st.button("📊 TAMPILKAN DATA PELANGGAN"):
    try:
        df_view = conn.read(ttl="0")
        if not df_view.empty:
            st.subheader("Data Keseluruhan Pelanggan")
            st.dataframe(df_view, use_container_width=True)
            st.info(f"Total Pelanggan Terdaftar: {len(df_view)} orang")
        else:
            st.warning("Database masih kosong.")
    except Exception as e:
        st.error(f"Gagal mengambil data: {e}")

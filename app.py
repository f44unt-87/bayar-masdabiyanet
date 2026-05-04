import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_searchbox import st_searchbox

# --- 1. SETUP HALAMAN ---
st.set_page_config(page_title="BAYAR-MASDABIYANET", layout="centered", page_icon="💰")

# Custom CSS untuk mempercantik tampilan dan tombol
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .stDownloadButton>button { width: 100%; background-color: #2e7d32; color: white; }
    code { color: #1e1e1e; }
    </style>
    """, unsafe_allow_html=True)

st.title("💰 MASDABIYANET")
st.subheader("Sistem Manajemen Pembayaran")

# --- 2. KONEKSI GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def search_customer(search_term: str):
    """Fungsi untuk mencari nama pelanggan di database"""
    if not search_term:
        return []
    try:
        # Membaca data dengan cache singkat (1 menit) agar sinkronisasi cepat
        df_names = conn.read(ttl="1m")
        all_names = df_names['Nama'].dropna().unique().tolist()
        return [name for name in all_names if search_term.lower() in name.lower()]
    except:
        return []

# --- 3. INPUT NAMA PELANGGAN ---
st.markdown("### 👤 Data Pelanggan")
nama_pilihan = st_searchbox(
    search_customer,
    label="Cari Nama atau Ketik Nama Baru",
    placeholder="Ketik nama pelanggan...",
    key="customer_search",
)

# Menentukan Nama Final (Pilihan dari list ATAU ketikan baru)
# Menggunakan session_state agar input manual tidak hilang saat klik tombol
if nama_pilihan:
    nama_final = nama_pilihan
else:
    nama_final = st.session_state.get("customer_search", {}).get("search", "")

if nama_final:
    st.info(f"Target Transaksi: **{nama_final.upper()}**")

# --- 4. FORM TRANSAKSI ---
with st.form("form_pembayaran", clear_on_submit=False):
    st.markdown("### 📑 Detail Pembayaran")
    
    col1, col2 = st.columns(2)
    with col1:
        tgl = st.date_input("TANGGAL BAYAR", datetime.now())
    with col2:
        tagihan = st.selectbox("NOMINAL TAGIHAN", [150000, 200000, 250000, 300000])
    
    submitted = st.form_submit_button("SIMPAN DATA & BUAT NOTA")

# --- 5. LOGIKA PROSES & CETAK ---
if submitted:
    if not nama_final or nama_final.strip() == "":
        st.error("⚠️ Nama pelanggan tidak boleh kosong!")
    else:
        with st.spinner("Menyambungkan ke database..."):
            try:
                # 1. Ambil data terbaru (ttl=0 untuk data paling fresh)
                df = conn.read(ttl="0")
                df = df.astype(object)
                
                # 2. Format Waktu & Bulan Indonesia
                tgl_str = tgl.strftime("%d/%m/%Y")
                bulan_key = tgl.strftime("%b").lower()
                mapping_bulan = {
                    'jan': 'jan', 'feb': 'feb', 'mar': 'mar', 'apr': 'apr',
                    'may': 'mei', 'jun': 'jun', 'jul': 'jul', 'aug': 'agu',
                    'sep': 'sep', 'oct': 'okt', 'nov': 'nov', 'dec': 'des'
                }
                bulan_indo = mapping_bulan.get(bulan_key, bulan_key)
                
                # 3. Update Baris jika ada, atau Tambah jika tidak ada
                if nama_final in df['Nama'].values:
                    idx = df.index[df['Nama'] == nama_final][0]
                    df.at[idx, 'Tanggal Bayar'] = tgl_str
                    df.at[idx, 'Tagihan'] = tagihan
                    if bulan_indo in df.columns:
                        df.at[idx, bulan_indo] = tgl_str
                    msg = f"✅ Data {nama_final} diperbarui!"
                else:
                    new_data = {"Nama": nama_final, "Tanggal Bayar": tgl_str, "Tagihan": tagihan, bulan_indo: tgl_str}
                    df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
                    msg = f"🎊 Pelanggan baru {nama_final} ditambahkan!"
                
                # 4. Kirim kembali ke Google Sheets
                conn.update(data=df)
                st.success(msg)

                # --- 6. GENERATE NOTA ---
                st.markdown("---")
                st.subheader("🧾 NOTA TRANSAKSI")
                
                nota_layout = f"""================================
       MASDABIYANET
================================
TANGGAL  : {tgl_str}
NAMA     : {nama_final.upper()}
LAYANAN  : Internet Bulanan
NOMINAL  : Rp {tagihan:,}
STATUS   : LUNAS / PAID
================================
  Simpan nota ini sebagai 
    bukti bayar yang sah.
================================
Cetak: {datetime.now().strftime('%H:%M:%S')}
"""
                # Tampilkan nota di layar
                st.code(nota_layout)
                
                # Tombol Download Nota
                st.download_button(
                    label="💾 DOWNLOAD NOTA (.TXT)",
                    data=nota_layout,
                    file_name=f"Nota_{nama_final}_{tgl_str.replace('/','-')}.txt",
                    mime="text/plain"
                )

            except Exception as e:
                st.error(f"Gagal memproses data: {e}")

# --- 7. DATABASE VIEW ---
st.markdown("<br><br>", unsafe_allow_html=True)
with st.expander("📊 LIHAT SEMUA DATA PELANGGAN"):
    if st.button("🔄 Segarkan Database"):
        st.cache_data.clear()
        st.rerun()
        
    try:
        df_full = conn.read(ttl="0")
        st.dataframe(df_full, use_container_width=True)
        st.caption(f"Total data tersimpan: {len(df_full)} baris")
    except:
        st.warning("Database belum tersedia.")

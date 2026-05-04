import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_searchbox import st_searchbox

# --- SETUP HALAMAN ---
st.set_page_config(page_title="BAYAR-MASDABIYANET", layout="centered", page_icon="💰")

# Custom CSS untuk tampilan lebih rapi
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 5px; }
    .nota-box { background-color: #f0f2f6; padding: 20px; border-radius: 10px; border: 1px dashed #333; }
    </style>
    """, unsafe_allow_key_html=True)

st.title("💰 MASDABIYANET")
st.subheader("Sistem Pembayaran Internet")

# --- KONEKSI GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Fungsi Pencarian Pelanggan
def search_customer(search_term: str):
    if not search_term:
        return []
    try:
        # Cache 1 menit saja agar data baru cepat muncul
        df_names = conn.read(ttl="1m")
        all_names = df_names['Nama'].dropna().unique().tolist()
        matches = [name for name in all_names if search_term.lower() in name.lower()]
        return matches
    except:
        return []

# --- 1. INPUT NAMA (DENGAN FIX AGAR TIDAK HILANG) ---
st.markdown("### 1. Cari atau Input Nama")
nama_pilihan = st_searchbox(
    search_customer,
    label="Pilih Nama dari Database atau Ketik Nama Baru",
    placeholder="Contoh: Joko...",
    key="customer_search",
)

# Ambil nama dari searchbox atau dari session state internal searchbox
if nama_pilihan:
    nama_final = nama_pilihan
else:
    # Ini menangkap teks yang baru diketik (untuk client baru)
    nama_final = st.session_state.get("customer_search", {}).get("search", "")

# Menampilkan indikator nama yang dipilih
if nama_final:
    st.info(f"📍 Pelanggan: **{nama_final.upper()}**")

# --- 2. FORM DATA PEMBAYARAN ---
with st.form("form_bayar", clear_on_submit=False):
    st.markdown("### 2. Detail Transaksi")
    col1, col2 = st.columns(2)
    with col1:
        tgl = st.date_input("TANGGAL BAYAR", datetime.now())
    with col2:
        tagihan = st.selectbox("JUMLAH TAGIHAN", [150000, 200000, 250000, 300000])
    
    submit = st.form_submit_button("💾 SIMPAN & CETAK NOTA")

# --- PROSES SIMPAN & NOTA ---
if submit:
    if not nama_final or nama_final.strip() == "":
        st.error("❌ Nama tidak boleh kosong! Silakan ketik nama terlebih dahulu.")
    else:
        with st.spinner("Sedang menyimpan data..."):
            try:
                # Baca data terbaru
                df = conn.read(ttl="0")
                df = df.astype(object)
                
                tgl_str = tgl.strftime("%d/%m/%Y")
                bulan_key = tgl.strftime("%b").lower()
                
                # Mapping Bulan Indonesia
                mapping = {'may': 'mei', 'aug': 'agu', 'oct': 'okt', 'dec': 'des'}
                bulan_indo = mapping.get(bulan_key, bulan_key)
                
                # Update atau Insert
                if nama_final in df['Nama'].values:
                    idx = df.index[df['Nama'] == nama_final][0]
                    df.at[idx, 'Tanggal Bayar'] = tgl_str
                    df.at[idx, 'Tagihan'] = tagihan
                    if bulan_indo in df.columns:
                        df.at[idx, bulan_indo] = tgl_str
                    st.success(f"✅ Data {nama_final} berhasil diperbarui!")
                else:
                    new_row = {"Nama": nama_final, "Tanggal Bayar": tgl_str, "Tagihan": tagihan, bulan_indo: tgl_str}
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    st.success(f"🎊 Pelanggan baru '{nama_final}' berhasil ditambahkan!")
                
                # Push ke Google Sheets
                conn.update(data=df)

                # --- BAGIAN NOTA ---
                st.markdown("---")
                st.subheader("🧾 NOTA PEMBAYARAN")
                
                nota_teks = f"""================================
       MASDABIYANET
================================
TANGGAL  : {tgl_str}
NAMA     : {nama_final.upper()}
LAYANAN  : Internet Bulanan
TOTAL    : Rp {tagihan:,}
STATUS   : LUNAS
================================
   Terima Kasih Atas
     Pembayaran Anda
================================
Waktu Cetak: {datetime.now().strftime('%H:%M:%S')}
"""
                # Tampilan Visual Nota
                st.code(nota_teks)
                
                # Tombol Download
                st.download_button(
                    label="📥 Download Nota (TXT)",
                    data=nota_teks,
                    file_name=f"Nota_{nama_final}_{tgl_str.replace('/','-')}.txt",
                    mime="text/plain"
                )
                
            except Exception as e:
                st.error(f"Terjadi kesalahan: {e}")

# --- 3. TAMPILAN DATA KESELURUHAN ---
st.markdown("<br><br>", unsafe_allow_key_html=True)
with st.expander("📊 TAMPILKAN DATABASE PELANGGAN"):
    if st.button("🔄 REFRESH DATA"):
        st.cache_data.clear()
    
    try:
        df_view = conn.read(ttl="0")
        if not df_view.empty:
            st.dataframe(df_view, use_container_width=True)
            st.caption(f"Total Pelanggan: {len(df_view)}")
        else:
            st.info("Database masih kosong.")
    except Exception as e:
        st.error(f"Gagal mengambil data: {e}")

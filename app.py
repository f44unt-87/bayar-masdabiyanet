import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_searchbox import st_searchbox
import urllib.parse

# --- 1. SETUP HALAMAN ---
st.set_page_config(page_title="BAYAR-MASDABIYANET", layout="centered", page_icon="💰")

# Style CSS agar tampilan profesional
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; background-color: #007bff; color: white; }
    .stDownloadButton>button { width: 100%; background-color: #6c757d; color: white; }
    .wa-button { 
        display: inline-block; width: 100%; background-color: #25D366; color: white; 
        text-align: center; padding: 12px; border-radius: 8px; font-weight: bold; 
        text-decoration: none; margin-top: 10px; border: none;
    }
    .wa-button:hover { background-color: #128C7E; color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("💰 MASDABIYANET")

# --- 2. KONEKSI & FUNGSI ---
conn = st.connection("gsheets", type=GSheetsConnection)

def search_customer(search_term: str):
    """Fungsi pencarian nama di database."""
    if not search_term: return []
    try:
        df_names = conn.read(ttl="1m")
        all_names = df_names['Nama'].dropna().unique().tolist()
        return [name for name in all_names if search_term.lower() in name.lower()]
    except: return []

def buat_link_wa(nama, tagihan, tgl, no_hp):
    """Membuat link API WhatsApp."""
    if not no_hp or pd.isna(no_hp): return None
    num = str(no_hp).strip().replace(" ", "").replace("-", "").replace("+", "")
    if num.startswith('0'): num = '62' + num[1:]
    
    pesan = (f"Halo Kak *{nama.upper()}*,\n\n"
             f"Terima kasih, pembayaran internet *MASDABIYANET* telah kami terima.\n"
             f"Total: *Rp {tagihan:,}*\n"
             f"Tanggal: *{tgl}*\n\n"
             f"Status: *LUNAS* ✅\n"
             f"Selamat berinternet kembali!")
    return f"https://wa.me/{num}?text={urllib.parse.quote(pesan)}"

# --- 3. LOGIKA HANDLING NAMA & AUTO-FILL ---
# Inisialisasi session state agar input tidak hilang
if "nama_disimpan" not in st.session_state:
    st.session_state.nama_disimpan = ""

# Searchbox untuk cari nama
nama_pilihan = st_searchbox(
    search_customer, 
    label="Cari Pelanggan (Ketik nama baru jika tidak ada)", 
    key="customer_search"
)

# Ambil teks yang sedang diketik meskipun tidak dipilih dari list (Anti-Hilang)
teks_sedang_diketik = st.session_state.get("customer_search", {}).get("search", "")

# Tentukan nama final: Prioritas hasil klik, jika tidak ada pakai hasil ketikan
if nama_pilihan:
    st.session_state.nama_disimpan = nama_pilihan
elif teks_sedang_diketik:
    st.session_state.nama_disimpan = teks_sedang_diketik

# Tampilkan Nama yang akan diproses
nama_aktif = st.session_state.nama_disimpan
if nama_aktif:
    st.info(f"📍 Memproses untuk: **{nama_aktif.upper()}**")

# Lookup No HP jika nama_aktif ada di database
no_hp_terdeteksi = ""
if nama_aktif:
    try:
        df_lookup = conn.read(ttl="1m")
        match = df_lookup[df_lookup['Nama'].str.lower() == nama_aktif.lower()]
        if not match.empty:
            no_hp_terdeteksi = str(match['No HP'].values[0])
    except:
        pass

# --- 4. FORM TRANSAKSI ---
with st.form("form_utama", clear_on_submit=False):
    col1, col2 = st.columns(2)
    with col1:
        tgl = st.date_input("TANGGAL BAYAR", datetime.now())
        tagihan = st.selectbox("TAGIHAN", [150000, 200000, 250000, 300000])
    with col2:
        # Field No HP akan terisi otomatis jika ditemukan
        no_hp_input = st.text_input("NO WHATSAPP", value=no_hp_terdeteksi, placeholder="0812...")
    
    submit_button = st.form_submit_button("💾 SIMPAN & BUAT NOTA")

# --- 5. PROSES SIMPAN ---
if submit_button:
    if not nama_aktif:
        st.error("⚠️ Silakan isi nama pelanggan!")
    elif not no_hp_input:
        st.error("⚠️ Silakan isi nomor HP!")
    else:
        with st.spinner("Menyimpan ke Google Sheets..."):
            try:
                # Ambil data paling fresh
                df = conn.read(ttl="0").astype(object)
                tgl_str = tgl.strftime("%d/%m/%Y")
                
                # Mapping Bulan Indonesia
                bulan_key = tgl.strftime("%b").lower()
                mapping = {'may': 'mei', 'aug': 'agu', 'oct': 'okt', 'dec': 'des'}
                bulan_indo = mapping.get(bulan_key, bulan_key)

                # Update atau Tambah Data Baru
                mask = df['Nama'].str.lower() == nama_aktif.lower()
                if mask.any():
                    idx = df.index[mask][0]
                    df.at[idx, 'No HP'] = no_hp_input
                    df.at[idx, 'Tanggal Bayar'] = tgl_str
                    df.at[idx, 'Tagihan'] = tagihan
                    if bulan_indo in df.columns:
                        df.at[idx, bulan_indo] = tgl_str
                else:
                    new_row = {
                        "Nama": nama_aktif, 
                        "No HP": no_hp_input, 
                        "Tanggal Bayar": tgl_str, 
                        "Tagihan": tagihan, 
                        bulan_indo: tgl_str
                    }
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

                # Kirim ke Sheets
                conn.update(data=df)
                st.success(f"✅ Transaksi {nama_aktif} berhasil dicatat!")

                # Tampilkan Nota
                nota = f"================================\n       MASDABIYANET\n================================\nTANGGAL  : {tgl_str}\nNAMA     : {nama_aktif.upper()}\nTAGIHAN  : Rp {tagihan:,}\nSTATUS   : LUNAS\n================================"
                st.code(nota)
                
                # Link WhatsApp
                link_wa = buat_link_wa(nama_aktif, tagihan, tgl_str, no_hp_input)
                if link_wa:
                    st.markdown(f'<a href="{link_wa}" target="_blank" class="wa-button">📲 KIRIM NOTA VIA WHATSAPP</a>', unsafe_allow_html=True)
                
                # Reset nama setelah berhasil agar form bersih untuk input selanjutnya
                st.session_state.nama_disimpan = ""

            except Exception as e:
                st.error(f"Terjadi kesalahan teknis: {e}")

# --- 6. DATABASE VIEW ---
st.markdown("---")
with st.expander("📊 LIHAT SEMUA DATA PELANGGAN"):
    if st.button("🔄 REFRESH DATA"):
        st.cache_data.clear()
        st.rerun()
    st.dataframe(conn.read(ttl="0"), use_container_width=True)

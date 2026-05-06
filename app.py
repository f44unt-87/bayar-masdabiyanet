import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_searchbox import st_searchbox
import urllib.parse

# --- 1. SETUP HALAMAN ---
st.set_page_config(page_title="BAYAR-MASDABIYANET", layout="centered", page_icon="💰")

# Style CSS untuk tombol agar ramah pengguna HP
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; background-color: #007bff; color: white; }
    .wa-button { 
        display: inline-block; width: 100%; background-color: #25D366; color: white; 
        text-align: center; padding: 12px; border-radius: 8px; font-weight: bold; 
        text-decoration: none; margin-top: 10px; border: none;
    }
    .wa-button:hover { background-color: #128C7E; color: white; cursor: pointer; }
    </style>
    """, unsafe_allow_html=True)

st.title("💰 MASDABIYANET")

# --- 2. KONEKSI & FUNGSI PEMBERSIH DATA ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_cleaned_data(ttl_time="1m"):
    """Membaca data dan membersihkan format No HP secara paksa agar tidak jadi float/desimal."""
    try:
        # Baca data asli
        df = conn.read(ttl=ttl_time)
        # Paksa seluruh kolom menjadi string/object untuk menghindari error float64
        df_clean = df.astype(str)
        
        if 'No HP' in df_clean.columns:
            # Bersihkan teks 'nan', hapus desimal '.0', dan hapus spasi
            df_clean['No HP'] = df_clean['No HP'].replace('nan', '')
            df_clean['No HP'] = df_clean['No HP'].str.split('.').str[0]
            df_clean['No HP'] = df_clean['No HP'].str.strip()
            
        return df_clean
    except:
        return pd.DataFrame()

def search_customer(search_term: str):
    """Fungsi pencarian nama pelanggan."""
    if not search_term: return []
    df = get_cleaned_data()
    if df.empty: return []
    all_names = df['Nama'].dropna().unique().tolist()
    return [name for name in all_names if search_term.lower() in name.lower()]

def buat_link_wa(nama, tagihan, tgl, no_hp):
    """Membuat link WhatsApp dengan proteksi error format angka."""
    if not no_hp or str(no_hp).lower() == 'nan' or no_hp == "":
        return None
    
    # Ambil angka saja (menghilangkan karakter non-digit)
    num = "".join(filter(str.isdigit, str(no_hp).split('.')[0]))
    
    if not num: return None
    
    # Konversi awalan 0 ke 62 (Indonesia)
    if num.startswith('0'):
        num = '62' + num[1:]
    elif not num.startswith('62'):
        num = '62' + num
        
    pesan = (f"Halo Kak *{nama.upper()}*,\n\n"
             f"Terima kasih, pembayaran internet *MASDABIYANET* telah kami terima.\n"
             f"Total: *Rp {int(tagihan):,}*\n"
             f"Tanggal: *{tgl}*\n\n"
             f"Status: *LUNAS* ✅\n"
             f"Selamat berinternet kembali!")
    return f"https://wa.me/{num}?text={urllib.parse.quote(pesan)}"

# --- 3. LOGIKA HANDLING NAMA ---
if "nama_disimpan" not in st.session_state:
    st.session_state.nama_disimpan = ""

nama_pilihan = st_searchbox(
    search_customer, 
    label="Cari Pelanggan (Ketik nama baru jika tidak ada)", 
    key="customer_search"
)

teks_sedang_diketik = st.session_state.get("customer_search", {}).get("search", "")

if nama_pilihan:
    st.session_state.nama_disimpan = nama_pilihan
elif teks_sedang_diketik:
    st.session_state.nama_disimpan = teks_sedang_diketik

nama_aktif = st.session_state.nama_disimpan

# Lookup No HP Otomatis berdasarkan nama yang dipilih
no_hp_terdeteksi = ""
if nama_aktif:
    df_lookup = get_cleaned_data()
    if not df_lookup.empty:
        match = df_lookup[df_lookup['Nama'].str.lower() == nama_aktif.lower()]
        if not match.empty:
            no_hp_terdeteksi = match['No HP'].values[0]

if nama_aktif:
    st.info(f"📍 Memproses untuk: **{nama_aktif.upper()}**")

# --- 4. FORM TRANSAKSI ---
with st.form("form_utama", clear_on_submit=False):
    col1, col2 = st.columns(2)
    with col1:
        tgl = st.date_input("TANGGAL BAYAR", datetime.now())
        tagihan = st.selectbox("TAGIHAN", [150000, 200000, 250000, 300000])
    with col2:
        no_hp_input = st.text_input("NO WHATSAPP", value=no_hp_terdeteksi, placeholder="0812...")
    
    submit_button = st.form_submit_button("💾 SIMPAN & BUAT NOTA")

# --- 5. PROSES SIMPAN (FORCE STRING MODE) ---
if submit_button:
    if not nama_aktif:
        st.error("⚠️ Silakan isi nama pelanggan!")
    elif not no_hp_input:
        st.error("⚠️ Silakan isi nomor HP!")
    else:
        with st.spinner("Menyimpan ke Google Sheets..."):
            try:
                # 1. Baca data fresh dan paksa semua jadi string
                df = conn.read(ttl="0").astype(str)
                df = df.replace('nan', '')
                
                tgl_str = tgl.strftime("%d/%m/%Y")
                
                # 2. Mapping Nama Bulan ke Bahasa Indonesia
                bulan_key = tgl.strftime("%b").lower()
                mapping = {'may': 'mei', 'aug': 'agu', 'oct': 'okt', 'dec': 'des'}
                bulan_indo = mapping.get(bulan_key, bulan_key)

                # 3. Update atau Tambah Data
                mask = df['Nama'].str.lower() == nama_aktif.lower()
                
                if mask.any():
                    idx = df.index[mask][0]
                    df.at[idx, 'No HP'] = str(no_hp_input)
                    df.at[idx, 'Tanggal Bayar'] = tgl_str
                    df.at[idx, 'Tagihan'] = str(tagihan)
                    if bulan_indo in df.columns:
                        df.at[idx, bulan_indo] = tgl_str
                else:
                    new_row = {
                        "Nama": str(nama_aktif), 
                        "No HP": str(no_hp_input), 
                        "Tanggal Bayar": tgl_str, 
                        "Tagihan": str(tagihan), 
                        bulan_indo: tgl_str
                    }
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

                # 4. Kirim Update ke Sheets dengan memaksa tipe string lagi
                conn.update(data=df.astype(str))
                st.success(f"✅ Transaksi {nama_aktif} berhasil dicatat!")

                # --- Tampilkan Nota & Tombol WhatsApp ---
                nota = f"================================\n       MASDABIYANET\n================================\nTANGGAL  : {tgl_str}\nNAMA     : {nama_aktif.upper()}\nTAGIHAN  : Rp {int(tagihan):,}\nSTATUS   : LUNAS\n================================"
                st.code(nota)
                
                link_wa = buat_link_wa(nama_aktif, tagihan, tgl_str, no_hp_input)
                if link_wa:
                    st.markdown(f'<a href="{link_wa}" target="_blank" class="wa-button">📲 KIRIM NOTA VIA WHATSAPP</a>', unsafe_allow_html=True)
                
                # Reset nama agar form bersih
                st.session_state.nama_disimpan = ""

            except Exception as e:
                st.error(f"Terjadi kesalahan teknis: {e}")

# --- 6. DATABASE VIEW ---
st.markdown("---")
with st.expander("📊 LIHAT SEMUA DATA PELANGGAN"):
    if st.button("🔄 REFRESH DATA"):
        st.cache_data.clear()
        st.rerun()
    st.dataframe(get_cleaned_data(ttl_time="0"), use_container_width=True)

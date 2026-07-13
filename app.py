import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import urllib.parse
from streamlit_searchbox import st_searchbox

# --- SETUP HALAMAN ---
st.set_page_config(page_title="BAYAR-MASDABIYANET", layout="wide", page_icon="💰")

# Inisialisasi Koneksi Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
LIST_BULAN = ['jan', 'feb', 'mar', 'apr', 'mei', 'jun', 'jul', 'agu', 'sep', 'okt', 'nov', 'des']

@st.cache_resource(ttl=600)
def load_data():
    try:
        # Membaca data mentah dari Google Sheets
        df = conn.read()
        if df is not None and not df.empty:
            # Mengisi sel kosong (NaN) dengan string kosong secara aman sebelum konversi tipe data
            return df.fillna('').astype(str)
        # Jika sheet kosong, buat DataFrame dasar agar aplikasi tidak crash
        return pd.DataFrame(columns=['Nama', 'No HP', 'Tagihan'] + LIST_BULAN)
    except Exception as e:
        st.error(f"Gagal mengambil data dari Google Sheets. Pastikan Secrets sudah terpasang. Detail: {e}")
        return pd.DataFrame(columns=['Nama', 'No HP', 'Tagihan'] + LIST_BULAN)

# Memastikan data termuat di session state
if 'df_data' not in st.session_state:
    st.session_state.df_data = load_data()

# --- FUNGSI WA ---
def buat_link_wa(nama, tagihan, tgl_input, no_hp):
    num = "".join(filter(str.isdigit, str(no_hp)))
    if not num: return None
    if num.startswith('0'): num = '62' + num[1:]
    elif not num.startswith('62'): num = '62' + num
    
    pesan = (f"Halo Kak *{nama.upper()}*,\n\n"
             f"Terima kasih, pembayaran internet *MASDABIYANET* telah kami terima.\n"
             f"Total: *Rp {int(tagihan):,}*\n"
             f"Tanggal: *{tgl_input}*\n\n"
             f"Status: *LUNAS* ✅\n"
             f"Selamat berinternet kembali!\n\n"
             f"💚Untuk Pelanggan Setia\n"
             f"\"Terima kasih atas pembayaran Anda! Kami senang dapat melayani kebutuhan internet Anda. "
             f"Semoga layanan kami membawa kemudahan dan kenyamanan dalam aktivitas Anda.\n"
             f"Dan semoga REZEKI Anda dilancarkan oleh Allah. Amiin 🤲\n\n"
             f"Ttd\nMASDABIYANET")
    return f"https://wa.me/{num}?text={urllib.parse.quote(pesan)}"

# --- UI UTAMA ---
st.title("💰 MASDABIYANET")
tab1, tab2 = st.tabs(["➕ INPUT TRANSAKSI BARU", "📋 KELOLA DATA PELANGGAN"])

with tab1:
    def search_pelanggan(search_term):
        df = st.session_state.df_data
        if 'Nama' in df.columns:
            return [nama for nama in df['Nama'].unique() if search_term.lower() in str(nama).lower()]
        return []

    nama_pilihan = st_searchbox(search_pelanggan, label="Nama Pelanggan", key="nama_search")
    
    no_hp_default = ""
    if nama_pilihan and 'Nama' in st.session_state.df_data.columns:
        match = st.session_state.df_data[st.session_state.df_data['Nama'].str.lower() == nama_pilihan.lower()]
        if not match.empty:
            no_hp_default = match['No HP'].values[0]

    with st.form("form_baru", clear_on_submit=True):
        nama = st.text_input("Nama Pelanggan", value=nama_pilihan if nama_pilihan else "")
        no_hp = st.text_input("No HP", value=no_hp_default)
        tgl_transaksi = st.date_input("Pilih Tanggal Pembayaran", datetime.now())
        tagihan = st.selectbox("Tagihan", [150000, 200000, 250000, 300000])
        submit = st.form_submit_button("SIMPAN TRANSAKSI")
        
        if submit:
            tgl_str = tgl_transaksi.strftime("%d/%m/%Y")
            bulan_key = LIST_BULAN[tgl_transaksi.month - 1]
            
            if 'Nama' in st.session_state.df_data['Nama'].values:
                idx = st.session_state.df_data.index[st.session_state.df_data['Nama'] == nama][0]
                st.session_state.df_data.at[idx, bulan_key] = tgl_str
                st.session_state.df_data.at[idx, 'No HP'] = no_hp
            else:
                new_row = {"Nama": nama, "No HP": no_hp, "Tagihan": str(tagihan), bulan_key: tgl_str}
                st.session_state.df_data = pd.concat([st.session_state.df_data, pd.DataFrame([new_row])], ignore_index=True)
            
            try:
                conn.update(data=st.session_state.df_data)
                st.success(f"Data {nama} berhasil disimpan untuk tanggal {tgl_str}!")
                
                link_wa = buat_link_wa(nama, tagihan, tgl_str, no_hp)
                if link_wa:
                    st.markdown(f'<a href="{link_wa}" target="_blank" style="padding:15px; background-color:#25D366; color:white; border-radius:8px; text-align:center; display:block; font-weight:bold; text-decoration:none;">📲 KIRIM NOTA VIA WHATSAPP</a>', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Gagal memperbarui Google Sheets: {e}")

with tab2:
    col1, col2 = st.columns(2)
    s_nama = col1.text_input("🔍 Cari Nama", key="search_nama_tab2")
    s_bulan = col2.selectbox("📅 Filter Bulan", ["Semua"] + LIST_BULAN)
    
    df_temp = st.session_state.df_data.copy()
    if s_nama and 'Nama' in df_temp.columns:
        df_temp = df_temp[df_temp['Nama'].str.contains(s_nama, case=False, na=False)]
    if s_bulan != "Semua" and s_bulan in df_temp.columns:
        df_temp = df_temp[df_temp[s_bulan] != ""]
        
    # Memperbaiki use_container_width menjadi width="stretch" sesuai standar Streamlit terbaru
    edited = st.data_editor(df_temp, num_rows="dynamic", width="stretch")
    
    if st.button("💾 SIMPAN SEMUA PERUBAHAN KE SHEETS"):
        try:
            st.session_state.df_data.update(edited)
            conn.update(data=st.session_state.df_data)
            st.success("Perubahan tersimpan!")
            st.rerun()
        except Exception as e:
            st.error(f"Gagal menyimpan perubahan: {e}")

    if st.button("🔄 Refresh Data"):
        st.cache_resource.clear()
        st.session_state.df_data = load_data()
        st.rerun()

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_searchbox import st_searchbox
import urllib.parse

st.set_page_config(page_title="BAYAR-MASDABIYANET", layout="centered", page_icon="💰")

# --- 1. INISIALISASI ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Gunakan session_state agar data hanya dibaca 1x per sesi
if 'df_data' not in st.session_state:
    st.session_state.df_data = conn.read().astype(str).replace('nan', '')

# --- 2. FUNGSI UTAMA ---
def get_names(search_term):
    df = st.session_state.df_data
    all_names = df['Nama'].unique().tolist()
    return [name for name in all_names if search_term.lower() in name.lower()]

def buat_link_wa(nama, tagihan, tgl, no_hp):
    num = "".join(filter(str.isdigit, str(no_hp)))
    if not num: return None
    if num.startswith('0'): num = '62' + num[1:]
    elif not num.startswith('62'): num = '62' + num
    pesan = f"Halo *{nama.upper()}*, pembayaran *MASDABIYANET* Rp{int(tagihan):,} tgl {tgl} telah diterima. Status: *LUNAS* ✅"
    return f"https://wa.me/{num}?text={urllib.parse.quote(pesan)}"

# --- 3. UI SEARCH ---
nama_pilihan = st_searchbox(get_names, label="Cari Pelanggan", key="searchbox")

# Ambil No HP dari state tanpa query API
no_hp_val = ""
if nama_pilihan:
    row = st.session_state.df_data[st.session_state.df_data['Nama'].str.lower() == nama_pilihan.lower()]
    if not row.empty:
        no_hp_val = row['No HP'].values[0]

# --- 4. FORM ---
with st.form("form_transaksi"):
    tgl = st.date_input("TANGGAL", datetime.now())
    tagihan = st.selectbox("TAGIHAN", [150000, 200000, 250000, 300000])
    no_hp = st.text_input("NO WA", value=no_hp_val)
    submit = st.form_submit_button("SIMPAN & KIRIM")

if submit:
    if not nama_pilihan:
        st.error("Pilih pelanggan terlebih dahulu!")
    else:
        with st.spinner("Memproses..."):
            # Update data lokal
            tgl_str = tgl.strftime("%d/%m/%Y")
            bulan_key = tgl.strftime("%b").lower()
            
            # Update DataFrame
            idx = st.session_state.df_data.index[st.session_state.df_data['Nama'].str.lower() == nama_pilihan.lower()]
            if not idx.empty:
                st.session_state.df_data.loc[idx[0], ['No HP', 'Tanggal Bayar', 'Tagihan', bulan_key]] = [no_hp, tgl_str, str(tagihan), tgl_str]
            else:
                new_row = {"Nama": nama_pilihan, "No HP": no_hp, "Tanggal Bayar": tgl_str, "Tagihan": str(tagihan), bulan_key: tgl_str}
                st.session_state.df_data = pd.concat([st.session_state.df_data, pd.DataFrame([new_row])], ignore_index=True)
            
            # Push ke Google Sheets sekali saja
            conn.update(data=st.session_state.df_data)
            st.success("Data tersimpan!")
            
            link = buat_link_wa(nama_pilihan, tagihan, tgl_str, no_hp)
            st.markdown(f'<a href="{link}" target="_blank" style="padding:10px; background:#25D366; color:white; border-radius:5px; text-decoration:none;">📲 Kirim WA</a>', unsafe_allow_html=True)

# Tombol Refresh untuk sinkronisasi manual
if st.button("🔄 Refresh Data dari Google Sheets"):
    st.session_state.df_data = conn.read().astype(str).replace('nan', '')
    st.rerun()

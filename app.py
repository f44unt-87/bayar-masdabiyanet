import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="BAYAR-MASDABIYANET", layout="wide", page_icon="💰")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 1. INISIALISASI DATA ---
if 'df_data' not in st.session_state:
    st.session_state.df_data = conn.read().astype(str).replace('nan', '')

# Daftar bulan sesuai dengan header Google Sheets Anda
LIST_BULAN = ['jan', 'feb', 'mar', 'apr', 'mei', 'jun', 'jul', 'agu', 'sep', 'okt', 'nov', 'des']

st.title("💰 MASDABIYANET")

tab1, tab2 = st.tabs(["➕ INPUT TRANSAKSI BARU", "📋 KELOLA DATA PELANGGAN"])

with tab1:
    with st.form("form_baru", clear_on_submit=True):
        nama = st.text_input("Nama Pelanggan")
        no_hp = st.text_input("No HP")
        tagihan = st.selectbox("Tagihan", [150000, 200000, 250000, 300000])
        submit = st.form_submit_button("SIMPAN")
        
        if submit:
            tgl_hari_ini = datetime.now()
            tgl_str = tgl_hari_ini.strftime("%d/%m/%Y")
            # Mengambil index bulan untuk mencocokkan dengan list (jan=0, feb=1, dst)
            bulan_key = LIST_BULAN[tgl_hari_ini.month - 1]
            
            # Update atau Tambah Data
            if nama in st.session_state.df_data['Nama'].values:
                idx = st.session_state.df_data.index[st.session_state.df_data['Nama'] == nama][0]
                st.session_state.df_data.at[idx, bulan_key] = tgl_str
            else:
                new_row = {"Nama": nama, "No HP": no_hp, "Tagihan": str(tagihan), bulan_key: tgl_str}
                st.session_state.df_data = pd.concat([st.session_state.df_data, pd.DataFrame([new_row])], ignore_index=True)
            
            conn.update(data=st.session_state.df_data)
            st.success(f"Data {nama} berhasil disimpan untuk bulan {bulan_key.upper()}!")

with tab2:
    # --- PENCARIAN & FILTER ---
    col1, col2 = st.columns(2)
    s_nama = col1.text_input("🔍 Cari Nama")
    s_bulan = col2.selectbox("📅 Filter Berdasarkan Bulan", ["Semua"] + LIST_BULAN)
    
    df_temp = st.session_state.df_data.copy()
    
    if s_nama:
        df_temp = df_temp[df_temp['Nama'].str.contains(s_nama, case=False, na=False)]
    if s_bulan != "Semua":
        # Hanya tampilkan baris yang ada isi tanggalnya di bulan tersebut
        df_temp = df_temp[df_temp[s_bulan] != ""]
        
    # --- EDIT & HAPUS ---
    st.info("💡 Edit langsung di tabel. Klik tombol di bawah untuk menyimpan perubahan.")
    edited = st.data_editor(df_temp, num_rows="dynamic", use_container_width=True)
    
    if st.button("💾 SIMPAN SEMUA PERUBAHAN KE SHEETS"):
        # Update session state dengan data hasil edit
        st.session_state.df_data.update(edited)
        conn.update(data=st.session_state.df_data)
        st.success("Perubahan berhasil tersimpan ke Google Sheets!")

    if st.button("🔄 Refresh Data"):
        st.session_state.df_data = conn.read().astype(str).replace('nan', '')
        st.rerun()

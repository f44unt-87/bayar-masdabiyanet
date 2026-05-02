import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_searchbox import st_searchbox

# Setup Halaman Mobile
st.set_page_config(page_title="BAYAR-MASDABIYANET", layout="centered")
st.title("💰 MASDABIYANET")

# Koneksi Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Fungsi untuk mengambil daftar nama dari Google Sheets (untuk fitur pencarian)
def search_customer(search_term: str):
    try:
        # Membaca data terbaru untuk mendapatkan daftar nama
        df_names = conn.read(ttl="10m") # Cache 10 menit agar tidak terlalu berat
        all_names = df_names['Nama'].dropna().unique().tolist()
        
        # Jika kotak pencarian kosong, tampilkan semua nama
        if not search_term:
            return all_names
        
        # Filter nama yang mengandung kata yang diketik
        return [name for name in all_names if search_term.lower() in name.lower()]
    except:
        return []

# Form Input
with st.form("form_bayar"):
    # Menggunakan Searchbox untuk fitur pencarian otomatis
    # User bisa memilih dari daftar atau mengetik nama baru
    nama = st_searchbox(
        search_customer,
        label="NAMA PELANGGAN",
        placeholder="Ketik nama pelanggan...",
        key="customer_search",
    )
    
    tgl = st.date_input("TANGGAL BAYAR")
    tagihan = st.selectbox("TAGIHAN", [150000, 200000, 250000, 300000])
    submit = st.form_submit_button("SIMPAN")

if submit:
    if not nama:
        st.error("Silakan masukkan atau pilih nama pelanggan!")
    else:
        # Baca data lengkap untuk proses update
        df = conn.read(ttl="0") 
        df = df.astype(object)
        
        tgl_str = tgl.strftime("%d/%m/%Y")
        bulan = tgl.strftime("%b").lower()
        
        # Mapping nama bulan Indo
        mapping = {'may': 'mei', 'aug': 'agu', 'oct': 'okt', 'dec': 'des'}
        if bulan in mapping: 
            bulan = mapping[bulan]
            
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
            
        # Update ke Google Sheets
        conn.update(data=df)

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
# Setup Halaman Mobile
st.set_page_config(page_title="BAYAR-MASDABIYANET", layout="centered")
st.title("💰 MASDABIYANET")
# Koneksi Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
with st.form("form_bayar"):
    nama = st.text_input("NAMA PELANGGAN")
    tgl = st.date_input("TANGGAL BAYAR")
    tagihan = st.selectbox("TAGIHAN", [150000, 200000, 250000, 300000])
    submit = st.form_submit_button("SIMPAN")
if submit:
    df = conn.read()
    tgl_str = tgl.strftime("%d/%m/%Y")
    bulan = tgl.strftime("%b").lower()
    # Mapping nama bulan Indo
    mapping = {'may': 'mei', 'aug': 'agu', 'oct': 'okt', 'dec': 'des'}
    if bulan in mapping: bulan = mapping[bulan]
    if nama in df['Nama'].values:
        idx = df.index[df['Nama'] == nama][0]
        df.at[idx, 'Tanggal Bayar'] = tgl_str
        df.at[idx, 'Tagihan'] = tagihan
        df.at[idx, bulan] = tgl_str
        st.success(f"Data {nama} diperbarui!")
    else:
        new_row = {"Nama": nama, "Tanggal Bayar": tgl_str, "Tagihan": tagihan, 
bulan: tgl_str}
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        st.success(f"Pelanggan {nama} baru ditambahkan!")
    conn.update(data=df)
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_searchbox import st_searchbox
import urllib.parse

# --- 1. SETUP HALAMAN ---
st.set_page_config(page_title="BAYAR-MASDABIYANET", layout="centered", page_icon="💰")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .stDownloadButton>button { width: 100%; background-color: #2e7d32; color: white; }
    .wa-button { 
        display: inline-block; width: 100%; background-color: #25D366; color: white; 
        text-align: center; padding: 10px; border-radius: 8px; font-weight: bold; 
        text-decoration: none; margin-top: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("💰 MASDABIYANET")

# --- 2. KONEKSI & FUNGSI ---
conn = st.connection("gsheets", type=GSheetsConnection)

def search_customer(search_term: str):
    if not search_term: return []
    try:
        df_names = conn.read(ttl="1m")
        all_names = df_names['Nama'].dropna().unique().tolist()
        return [name for name in all_names if search_term.lower() in name.lower()]
    except: return []

def buat_link_wa(nama, tagihan, tgl, no_hp):
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

# --- 3. INPUT NAMA ---
nama_pilihan = st_searchbox(search_customer, label="Cari/Ketik Nama Pelanggan", key="customer_search")
nama_final = nama_pilihan if nama_pilihan else st.session_state.get("customer_search", {}).get("search", "")

# --- 4. FORM TRANSAKSI ---
with st.form("form_pembayaran"):
    col1, col2 = st.columns(2)
    with col1:
        tgl = st.date_input("TANGGAL BAYAR", datetime.now())
        tagihan = st.selectbox("TAGIHAN", [150000, 200000, 250000, 300000])
    with col2:
        # Input No HP hanya perlu diisi jika pelanggan baru
        no_hp_baru = st.text_input("NO HP (Isi jika pelanggan baru)", placeholder="0812...")
    
    submitted = st.form_submit_button("SIMPAN & BUAT NOTA")

if submitted:
    if not nama_final:
        st.error("⚠️ Nama harus diisi!")
    else:
        try:
            df = conn.read(ttl="0").astype(object)
            tgl_str = tgl.strftime("%d/%m/%Y")
            bulan = tgl.strftime("%b").lower()
            mapping = {'may': 'mei', 'aug': 'agu', 'oct': 'okt', 'dec': 'des'}
            bulan_indo = mapping.get(bulan, bulan)

            # Logika Update/Insert
            if nama_final in df['Nama'].values:
                idx = df.index[df['Nama'] == nama_final][0]
                df.at[idx, 'Tanggal Bayar'] = tgl_str
                df.at[idx, 'Tagihan'] = tagihan
                if bulan_indo in df.columns: df.at[idx, bulan_indo] = tgl_str
                # Update No HP jika di form diisi
                if no_hp_baru: df.at[idx, 'No HP'] = no_hp_baru
                current_no_hp = df.at[idx, 'No HP']
            else:
                new_row = {"Nama": nama_final, "No HP": no_hp_baru, "Tanggal Bayar": tgl_str, "Tagihan": tagihan, bulan_indo: tgl_str}
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                current_no_hp = no_hp_baru

            conn.update(data=df)
            st.success(f"✅ Data {nama_final} Berhasil Disimpan!")

            # --- NOTA & WHATSAPP ---
            nota = f"""================================
       MASDABIYANET
================================
TANGGAL  : {tgl_str}
NAMA     : {nama_final.upper()}
TOTAL    : Rp {tagihan:,}
STATUS   : LUNAS
================================
"""
            st.code(nota)
            
            # Tombol WhatsApp
            link_wa = buat_link_wa(nama_final, tagihan, tgl_str, current_no_hp)
            if link_wa:
                st.markdown(f'<a href="{link_wa}" target="_blank" class="wa-button">📲 KIRIM NOTA KE WHATSAPP</a>', unsafe_allow_html=True)
            else:
                st.warning("⚠️ No HP tidak ditemukan. Masukkan nomor HP untuk kirim WA.")

        except Exception as e:
            st.error(f"Error: {e}")

# --- 5. DATABASE ---
with st.expander("📊 LIHAT DATA PELANGGAN"):
    if st.button("🔄 REFRESH"): st.rerun()
    st.dataframe(conn.read(ttl="0"), use_container_width=True)

import streamlit as st
import pandas as pd
import sqlite3
import yfinance as yf
from datetime import datetime
import plotly.express as px

# Sayfa Ayarları
st.set_page_config(page_title="Portföy Yöneticisi", page_icon="📈", layout="wide")

# --- 1. VERİTABANI ALTYAPISI ---
def veritabani_olustur():
    conn = sqlite3.connect('portfoy.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS yatirimlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            varlik_kodu TEXT,
            alis_fiyati REAL,
            adet REAL,
            alis_tarihi TEXT
        )
    ''')
    conn.commit()
    conn.close()

veritabani_olustur()

# --- 2. GERÇEK ENFLASYON MOTORU ---
aylik_enflasyon_oranlari = {
    "2023-01": 6.65, "2023-02": 3.15, "2023-03": 2.29, "2023-04": 2.39, "2023-05": 0.04, "2023-06": 3.92,
    "2023-07": 9.49, "2023-08": 9.09, "2023-09": 4.75, "2023-10": 3.43, "2023-11": 3.28, "2023-12": 2.93,
    "2024-01": 6.70, "2024-02": 4.53, "2024-03": 3.16, "2024-04": 3.18, "2024-05": 3.37, "2024-06": 1.64,
    "2024-07": 3.23, "2024-08": 2.47, "2024-09": 2.97, "2024-10": 2.88, "2024-11": 2.24, "2024-12": 1.90,
    "2025-01": 2.50, "2025-02": 2.10, "2025-03": 2.00, "2025-04": 2.00, "2025-05": 1.80, "2025-06": 1.50,
    "2025-07": 1.50, "2025-08": 1.50, "2025-09": 1.50, "2025-10": 1.50, "2025-11": 1.50, "2025-12": 1.50,
    "2026-01": 1.50, "2026-02": 1.50, "2026-03": 1.50
}

def gercek_enflasyon_hesapla(alis_tarihi):
    bugun = datetime.today().date()
    toplam_carpan = 1.0
    current_date = alis_tarihi.replace(day=1)
    end_date = bugun.replace(day=1)
    
    while current_date <= end_date:
        key = current_date.strftime("%Y-%m")
        oran = aylik_enflasyon_oranlari.get(key, 2.0)
        toplam_carpan *= (1 + (oran / 100))
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)
    return toplam_carpan - 1.0

# --- 3. KULLANICI ARAYÜZÜ (EKLEME VE SİLME FORMLARI) ---
st.title("📊 Profesyonel Portföy ve Enflasyon Takip Sistemi")
st.markdown("---")

menu_col1, menu_col2 = st.columns(2)

# EKLEME MENÜSÜ
with menu_col1:
    with st.expander("➕ Yeni Yatırım Ekle", expanded=False):
        with st.form("ekleme_formu", clear_on_submit=True):
            varlik_kodu = st.text_input("Varlık Kodu (Örn: THYAO.IS, BTC-USD)")
            alis_fiyati = st.number_input("Birim Alış Fiyatı", min_value=0.0, format="%.4f")
            adet = st.number_input("Adet", min_value=0.0, format="%.4f")
            alis_tarihi = st.date_input("Alış Tarihi")
                
            ekle_butonu = st.form_submit_button("💾 Kaydet")

            if ekle_butonu:
                if varlik_kodu and alis_fiyati > 0 and adet > 0:
                    conn = sqlite3.connect('portfoy.db')
                    c = conn.cursor()
                    c.execute("INSERT INTO yatirimlar (varlik_kodu, alis_fiyati, adet, alis_tarihi) VALUES (?, ?, ?, ?)", 
                              (varlik_kodu.upper(), alis_fiyati, adet, str(alis_tarihi)))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ {varlik_kodu.upper()} eklendi!")
                    st.rerun() # Sayfayı otomatik yenile
                else:
                    st.error("⚠️ Eksik bilgi girdiniz.")

# SİLME MENÜSÜ
with menu_col2:
    with st.expander("🗑️ Portföyden Varlık Sil (Satış)", expanded=False):
        conn = sqlite3.connect('portfoy.db')
        df_sil = pd.read_sql_query("SELECT id, varlik_kodu, adet, alis_tarihi FROM yatirimlar", conn)
        
        if not df_sil.empty:
            # Kullanıcıya göstermek için şık bir liste hazırlıyoruz
            silme_secenekleri = {f"{row['varlik_kodu']} - {row['adet']} Adet (Alış: {row['alis_tarihi']})": row['id'] for index, row in df_sil.iterrows()}
            secilen_silinecek = st.selectbox("Silmek/Satmak İstediğiniz Varlığı Seçin:", list(silme_secenekleri.keys()))
            
            if st.button("🗑️ Seçili Varlığı Sil"):
                silinecek_id = silme_secenekleri[secilen_silinecek]
                c = conn.cursor()
                c.execute("DELETE FROM yatirimlar WHERE id=?", (silinecek_id,))
                conn.commit()
                conn.close()
                st.success("✅ Varlık başarıyla silindi!")
                st.rerun() # Sayfayı anında güncelle
        else:
            st.info("Portföyünüzde silinecek varlık bulunmuyor.")
            conn.close()

st.markdown("---")

# --- 4. CANLI PİYASA MOTORU VE REEL KÂR HESABI ---
conn = sqlite3.connect('portfoy.db')
df = pd.read_sql_query("SELECT id, varlik_kodu as 'Varlık Kodu', alis_fiyati as 'Alış Fiyatı', adet as 'Adet', alis_tarihi as 'Alış Tarihi' FROM yatirimlar", conn)
conn.close()

if not df.empty:
    
    guncel_fiyatlar = []
    
    for kod in df['Varlık Kodu']:
        try:
            ticker = yf.Ticker(kod)
            data = ticker.history(period="1d")
            if not data.empty:
                fiyat = data['Close'].iloc[-1]
                guncel_fiyatlar.append(float(fiyat))
            else:
                guncel_fiyatlar.append(0.0)
        except:
            guncel_fiyatlar.append(0.0)

    # Matematiksel Hesaplamalar
    df['Güncel Fiyat'] = guncel_fiyatlar
    df['Toplam Maliyet'] = df['Alış Fiyatı'] * df['Adet']
    df['Güncel Değer'] = df['Güncel Fiyat'] * df['Adet']
    df['Nominal Kâr'] = df['Güncel Değer'] - df['Toplam Maliyet']
    
    df['Alış Tarihi'] = pd.to_datetime(df['Alış Tarihi']).dt.date
    df['Dönemsel Gerçek Enflasyon Oranı (%)'] = df['Alış Tarihi'].apply(gercek_enflasyon_hesapla)
    
    df['Enflasyonlu (Reel) Maliyet'] = df['Toplam Maliyet'] * (1 + df['Dönemsel Gerçek Enflasyon Oranı (%)'])
    df['Net REEL Kâr'] = df['Güncel Değer'] - df['Enflasyonlu (Reel) Maliyet']
    
    # --- ÖZET KARTLARI ---
    toplam_maliyet = df['Toplam Maliyet'].sum()
    toplam_deger = df['Güncel Değer'].sum()
    toplam_nominal_kar = df['Nominal Kâr'].sum()
    toplam_reel_kar = df['Net REEL Kâr'].sum()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Toplam Dökülen Nakit", f"{toplam_maliyet:,.2f} ₺")
    col2.metric("📈 Güncel Değer", f"{toplam_deger:,.2f} ₺", f"Düz Kâr: {toplam_nominal_kar:,.2f} ₺")
    col3.metric("🛡️ Toplam REEL Kâr (Net Alım Gücü)", f"{toplam_reel_kar:,.2f} ₺", 
                f"Gerçek Kazanç", delta_color="normal" if toplam_reel_kar > 0 else "inverse")
    
    st.markdown("---")
    
    # --- GRAFİKLER VE GÖRSELLEŞTİRME ---
    gorsel_col1, gorsel_col2 = st.columns(2)
    
    with gorsel_col1:
        fig_pasta = px.pie(df, values='Güncel Değer', names='Varlık Kodu', 
                           title='Portföy Dağılımı (Güncel Değere Göre)', hole=0.4,
                           color_discrete_sequence=px.colors.sequential.RdBu)
        fig_pasta.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pasta, use_container_width=True)
        
    with gorsel_col2:
        fig_cubuk = px.bar(df, x='Varlık Kodu', y='Net REEL Kâr', 
                           title='Varlık Bazında Reel Kâr/Zarar Durumu',
                           color='Net REEL Kâr', color_continuous_scale=px.colors.diverging.RdYlGn)
        st.plotly_chart(fig_cubuk, use_container_width=True)

    # --- TABLO ---
    df['Dönemsel Gerçek Enflasyon Oranı (%)'] = df['Dönemsel Gerçek Enflasyon Oranı (%)'] * 100
    gosterim_df = df[['Varlık Kodu', 'Alış Tarihi', 'Dönemsel Gerçek Enflasyon Oranı (%)', 'Toplam Maliyet', 'Güncel Değer', 'Nominal Kâr', 'Net REEL Kâr']]
    
    st.dataframe(gosterim_df.style.format({
        'Dönemsel Gerçek Enflasyon Oranı (%)': '%{:.2f}',
        'Toplam Maliyet': '{:,.2f} ₺',
        'Güncel Değer': '{:,.2f} ₺',
        'Nominal Kâr': '{:,.2f} ₺',
        'Net REEL Kâr': '{:,.2f} ₺'
    }), use_container_width=True)

else:
    st.info("📌 Portföyünüz boş. Yukarıdan veri ekleyerek canlı sistemi başlatın.")
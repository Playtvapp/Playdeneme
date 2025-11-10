import os
import requests
import re
import xml.etree.ElementTree as ET

# EPG dosyasının URL'si
EPG_URL = "https://raw.githubusercontent.com/braveheart1983/tvg-macther/main/tr-epg.xml"

# Domain aralığı (25–99)
active_domain = None
for i in range(25, 100):
    url = f"https://birazcikspor{i}.xyz/"
    try:
        r = requests.head(url, timeout=5)
        if r.status_code == 200:
            active_domain = url
            print(f"Aktif domain bulundu: {active_domain}")
            break
    except:
        continue

if not active_domain:
    raise SystemExit("Aktif domain bulunamadı.")

# İlk kanal ID'si al
html = requests.get(active_domain, timeout=10).text
m = re.search(r'<iframe[^>]+id="matchPlayer"[^>]+src="event\.html\?id=([^"]+)"', html)
if not m:
    raise SystemExit("Kanal ID bulunamadı.")
first_id = m.group(1)
print(f"İlk Kanal ID: {first_id}")

# Base URL çek
event_source_url = active_domain + "event.html?id=" + first_id
event_source = requests.get(event_source_url, timeout=10).text
b = re.search(r'var\s+baseurls\s*=\s*\[\s*"([^"]+)"', event_source)
if not b:
    raise SystemExit("Base URL bulunamadı.")
base_url = b.group(1)
print(f"Base URL: {base_url}")

# --- EPG Verilerini İndir ve İşle ---
print(f"EPG verileri şuradan indiriliyor: {EPG_URL}")
# 1. Otomatik Eşleştirme Haritası (XML'deki display-name'e göre)
epg_map_auto = {} 
try:
    epg_response = requests.get(EPG_URL, timeout=10)
    epg_response.raise_for_status() 
    
    root = ET.fromstring(epg_response.content)
    
    for channel in root.findall('channel'):
        channel_id = channel.get('id') 
        display_name_element = channel.find('display-name')
        
        if channel_id and display_name_element is not None:
            display_name = display_name_element.text
            if display_name not in epg_map_auto:
                epg_map_auto[display_name] = channel_id
                
    print(f"✅ {len(epg_map_auto)} adet EPG kanalı otomatik eşleştirme için yüklendi.")

except Exception as e:
    print(f"⚠️ EPG verisi işlenirken hata oluştu: {e}")
# --- EPG BÖLÜMÜ SONU ---


# Kanal listesi
channels = [
    ("beIN Sport 1 HD","androstreamlivebs1","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("beIN Sport 2 HD","androstreamlivebs2","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("beIN Sport 3 HD","androstreamlivebs3","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("beIN Sport 4 HD","androstreamlivebs4","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("beIN Sport 5 HD","androstreamlivebs5","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("beIN Sport Max 1 HD","androstreamlivebsm1","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("beIN Sport Max 2 HD","androstreamlivebsm2","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("S Sport 1 HD","androstreamlivess1","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("S Sport 2 HD","androstreamlivess2","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("Tivibu Sport HD","androstreamlivets","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("Tivibu Sport 1 HD","androstreamlivets1","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("Tivibu Sport 2 HD","androstreamlivets2","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("Tivibu Sport 3 HD","androstreamlivets3","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("Tivibu Sport 4 HD","androstreamlivets4","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("Smart Sport 1 HD","androstreamlivesm1","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("Smart Sport 2 HD","androstreamlivesm2","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("Euro Sport 1 HD","androstreamlivees1","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("Euro Sport 2 HD","androstreamlivees2","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    # Exxen ve Tabii kanalları EPG dosyasında bulunmuyor.
    # Onlar için tvg-id, kanalın kendi adı olarak atanacak.
    ("Tabii HD","androstreamlivetb","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("Tabii 1 HD","androstreamlivetb1","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("Tabii 2 HD","androstreamlivetb2","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("Tabii 3 HD","androstreamlivetb3","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("Tabii 4 HD","androstreamlivetb4","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("Tabii 5 HD","androstreamlivetb5","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("Tabii 6 HD","androstreamlivetb6","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("Tabii 7 HD","androstreamlivetb7","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("Tabii 8 HD","androstreamlivetb8","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("Exxen HD","androstreamliveexn","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("Exxen 1 HD","androstreamliveexn1","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("Exxen 2 HD","androstreamliveexn2","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("Exxen 3 HD","androstreamliveexn3","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("Exxen 4 HD","androstreamliveexn4","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("Exxen 5 HD","androstreamliveexn5","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("Exxen 6 HD","androstreamliveexn6","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("Exxen 7 HD","androstreamliveexn7","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
    ("Exxen 8 HD","androstreamliveexn8","https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"),
]

# --- YENİ BÖLÜM: Manuel EPG Eşleştirme Haritası ---
# Script'teki 'name' ile EPG'deki 'id' arasında manuel eşleştirme.
# Otomatik eşleştirme (epg_map_auto) "beIN Sport 1 HD" gibi birebir aynı olanları yakalar.
# Bu manuel harita, "S Sport 1 HD" (script) -> "S Sport.tr" (EPG) gibi farklı olanları düzeltir.
MANUAL_EPG_MAP = {
    # Script Adı : EPG ID
    "S Sport 1 HD"      : "S Sport.tr",
    "S Sport 2 HD"      : "S Sport 2.tr",
    "Tivibu Sport HD"   : "T.Sport.tr",
    # Tivibu 1-4, EPG dosyasında bulunmuyor.
    "Smart Sport 1 HD"  : "Smart Spor.tr",
    "Smart Sport 2 HD"  : "Smart Spor 2.tr",
    "Euro Sport 1 HD"   : "Eurosport 1.tr",
    "Euro Sport 2 HD"   : "Eurosport 2.tr",
    # beIN kanalları otomatik haritadan (epg_map_auto) doğru eşleşecektir.
    # Exxen ve Tabii kanalları EPG'de bulunmadığı için varsayılan (isim) ID'sini alacaktır.
}


# Proxy URL
proxy_prefix = "https://api.codetabs.com/v1/proxy/?quest="

# ✅ Toplu M3U faylı (androiptv.m3u8)
lines = [f'#EXTM3U x-tvg-url="{EPG_URL}"']
eşleşen_sayisi = 0
eşleşmeyen_sayisi = 0

for name, cid, logo in channels:
    
    # --- GÜNCELLENMİŞ EŞLEŞTİRME MANTIĞI ---
    tvg_id = None
    
    # 1. Önce Manuel Haritayı (MANUAL_EPG_MAP) kontrol et
    if name in MANUAL_EPG_MAP:
        tvg_id = MANUAL_EPG_MAP[name]
        eşleşen_sayisi += 1
    
    # 2. Manuel haritada yoksa, Otomatik Haritayı (epg_map_auto) kontrol et
    elif name in epg_map_auto:
        tvg_id = epg_map_auto[name]
        eşleşen_sayisi += 1
        
    # 3. Hiçbir haritada (ne manuel ne otomatik) yoksa, varsayılan olarak kanal adını kullan
    else:
        tvg_id = name # Örn: "Exxen 1 HD"
        eşleşmeyen_sayisi += 1
    # --- EŞLEŞTİRME MANTIĞI SONU ---
    
    lines.append(f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{name}" tvg-logo="{logo}" group-title="PLAY SPOR | Telegram @playtvmedya",{name}')
    
    full_url = f"{proxy_prefix}{base_url}{cid}.m3u8"
    lines.append(full_url)

with open("androiptv.m3u8", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"✅ androiptv.m3u8 dosyası doğru EPG ID'leri ile oluşturuldu.")
print(f"   EPG Eşleşen Kanal: {eşleşen_sayisi}")
print(f"   EPG Eşleşmeyen (Varsayılan): {eşleşmeyen_sayisi}")


# ✅ Ayrı-ayrı .m3u8 faylları (Bu kısım değişmedi)
out_dir = "channels"
os.makedirs(out_dir, exist_ok=True)

for name, cid, logo in channels:
    file_name = name.replace(" ", "_").replace("/", "_") + ".m3u8"
    full_url = f"{proxy_prefix}{base_url}{cid}.m3u8"

    content = [
        "#EXTM3U",
        "#EXT-X-VERSION:3",
        '#EXT-X-STREAM-INF:BANDWIDTH=5500000,AVERAGE-BANDWIDTH=8976000,RESOLUTION=1920x1080,CODECS="avc1.640028,mp4a.40.2",FRAME-RATE=25',
        full_url
    ]

    with open(os.path.join(out_dir, file_name), "w", encoding="utf-8") as f:
        f.write("\n".join(content))

print(f"✅ {len(channels)} kanal ayrıca '{out_dir}' qovluğuna .m3u8 faylı olaraq yazıldı.")
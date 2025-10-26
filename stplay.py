import requests
import zstd  # Hata toleranslı decompress için gerekli
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import datetime

# --- Hata toleranslı decompress fonksiyonu ---
def decompress_content(response):
    """Gelen yanıtı zstd formatında ise açar, değilse olduğu gibi döndürür."""
    try:
        if response.headers.get("content-encoding") == "zstd":
            dctx = zstd.ZstdDecompressor()
            return dctx.decompress(response.content)
        else:
            return response.content
    except zstd.ZstdError:
        # Zstd hatası durumunda orijinal içeriği döndür
        print("⚠️ Zstd decompress hatası, orijinal içerik deneniyor.")
        return response.content
    except Exception as e:
        print(f"⚠️ Decompress sırasında bilinmeyen hata: {e}")
        return response.content

# --- 1. Stream listesi al ---

    url_list = "url_list = "https://api.istplay.xyz/stream-list-v2/?tv=tv""
headers = {
    "Accept": "application/json, text/plain, */*",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/141.0.0.0 Safari/537.36",
}

print("📢 Yayın listesi alınıyor...")
response = requests.get(url_list, headers=headers, timeout=15)
data = decompress_content(response)
parsed = json.loads(data)
print("✅ Yayın listesi başarıyla alındı.")

# --- 4. m3u8 linkini alma fonksiyonu ---
def get_m3u8(stream_id):
    """Verilen stream_id için m3u8 linkini çeker."""
    try:
        url = f"https://istplay.xyz/tv/?stream_id={stream_id}"
        response = requests.get(url, headers=headers, timeout=10)
        
        # BeautifulSoup kullanarak script etiketini bul
        soup = BeautifulSoup(response.text, 'html.parser')
        source = soup.find("source", {"type": "application/vnd.apple.mpegurl"})
        
        if source and source.get("src"):
            return stream_id, source["src"]
    except Exception as e:
        print(f"⚠️ Hata (stream_id={stream_id}): {e}")
    return stream_id, None

# --- 5. Tüm stream_id’leri topla ---
all_events = []
if "sports" in parsed and isinstance(parsed["sports"], dict):
    for sport_name, sport_category in parsed["sports"].items():
        if not isinstance(sport_category, dict):
            continue
        
        events = sport_category.get("events", {})
        # API bazen dict, bazen list dönebiliyor, ikisini de ele al
        iterable = events.items() if isinstance(events, dict) else [(str(i), e) for i, e in enumerate(events)]

        for event_id, event_data in iterable:
            if event_data.get("stream_id"):
                all_events.append((sport_name, event_id, event_data))

# --- 6. ThreadPool ile eş zamanlı m3u8 çek ---
print(f"🔗 {len(all_events)} adet yayın linki çekiliyor (Bu işlem biraz sürebilir)...")
with ThreadPoolExecutor(max_workers=20) as executor:
    future_to_event = {executor.submit(get_m3u8, ev[2]['stream_id']): ev for ev in all_events}
    for future in as_completed(future_to_event):
        sport_name, event_id, event_data = future_to_event[future]
        try:
            sid, m3u8_url = future.result()
            event_data["m3u8_url"] = m3u8_url
        except Exception as e:
            print(f"⚠️ Future hatası: {e}")
print("✅ Tüm linkler çekildi.")

# --- 7. Spor isimleri ve logolar ---
sport_translation = {
    "FOOTBALL"    : {"name": "FUTBOL", "logo": "https://i.imgur.com/YMWsPUP.png"},
    "BASKETBALL"  : {"name": "BASKETBOL", "logo": "https://i.imgur.com/TUhbEbl.png"},
    "TENNIS"      : {"name": "TENİS", "logo": "https://i.imgur.com/S3Hj6yZ.png"},
    "VOLLEYBALL"  : {"name": "VOLEYBOL", "logo": "https://i.imgur.com/qLROp0s.png"},
    "ICE_HOCKEY"  : {"name": "BUZ HOKEYİ", "logo": "https://i.imgur.com/gQvgyw0.png"},
    "CRICKET"     : {"name": "KRİKET", "logo": "https://i.imgur.com/eB30c3P.png"},
    "HANDBALL"    : {"name": "HENTBOL", "logo": "https://i.imgur.com/uGfdeP2.png"},
    "HORSE_RACING": {"name": "AT YARIŞI", "logo": "https://i.imgur.com/mU4tW6A.png"},
    "SNOOKER"     : {"name": "İNGİLTERE BİLARDOSU", "logo": "https://cdn.shopify.com/s/files/1/0644/5685/1685/files/pool-table-graphic-1.jpg"},
    "BILLIARDS"   : {"name": "BİLARDO", "logo": "https://www.bilardo.org.tr/image/be2a4809f1c796e4453b45ccf0d9740c.jpg"},
    "BICYCLE"     : {"name": "BİSİKLET YARIŞI", "logo": "https://www.gazetekadikoy.com.tr/Uploads/gazetekadikoy.com.tr/202204281854011-img.jpg"},
    "BOXING"      : {"name": "BOKS", "logo": "https://www.sportsmith.co/wp-content/uploads/2023/04/Thumbnail-scaled.jpg"},
}

# --- 8. M3U formatlı çıktı üret (KATEGORİZE EDİLMİŞ VE SAATLİ) ---
print("📝 M3U dosyası oluşturuluyor...")
output_lines = ['#EXTM3U', '']

# all_events listesini (artık m3u8_url'leri içeriyor) döngüye al
for sport_name, event_id, event_data in all_events:
    
    m3u8_url = event_data.get("m3u8_url")
    # Eğer m3u8 linki alınamadıysa bu yayını atla
    if not m3u8_url:
        continue

    league = event_data.get("league", "Bilinmiyor")
    # API'de yazım hatası var gibi ('competitiors'), ona göre alıyoruz
    competitors = event_data.get("competitiors", {}) 
    home = competitors.get("home", "").strip()
    away = competitors.get("away", "").strip()

    # YENİ: Başlangıç saatini al ve formatla
    start_timestamp = event_data.get("start_time")
    start_time_str = ""
    if start_timestamp:
        try:
            # Unix timestamp'i datetime objesine çevir
            dt_object = datetime.datetime.fromtimestamp(int(start_timestamp))
            # HH:MM formatına getir
            start_time_str = f"[{dt_object.strftime('%H:%M')}] "
        except (ValueError, TypeError):
            start_time_str = "" # Hatalı timestamp durumunda boş bırak

    # YENİ: Grup başlığını spor isminden al
    sport_info = sport_translation.get(sport_name.upper(), {"name": sport_name.upper(), "logo": ""})
    display_sport = sport_info["name"]
    logo_url = sport_info.get("logo", "")
    group_title = display_sport  # Grup başlığı artık dinamik

    # Başlığı saat bilgisiyle birleştir
    if sport_name.upper() == "HORSE_RACING":
        display_title = f"{start_time_str}{home.upper()} ({league.upper()})"
    else:
        display_title = f"{start_time_str}{home.upper()} vs {away.upper()} ({league.upper()})"

    line = f'#EXTINF:-1 tvg-name="{display_sport}" tvg-logo="{logo_url}" group-title="{group_title}",{display_title}\n{m3u8_url}'
    output_lines.append(line)

# --- 9. Dosyaya yaz ---
output_filename = "all_world_sports_categorized.m3u"
with open(output_filename, "w", encoding="utf-8") as f:
    f.write("\n".join(output_lines))

print(f"💾 M3U çıktısı '{output_filename}' dosyasına başarıyla kaydedildi.")
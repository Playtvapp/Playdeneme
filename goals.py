import requests
import re
import os
import shutil
import sys
import time
from urllib.parse import quote

def main():
    print("🚀 PyGoals V2 M3U8 Kanal İndirici Başlatılıyor...")
    print("⏰ Lütfen işlemin tamamlanmasını bekleyin...")

    # Trgoals domain kontrol
    base = "https://trgoals"
    domain = ""

    print("\n🔍 Domain aranıyor: trgoals.xyz → trgoals.xyz")
    for i in range(1393, 2101):
        test_domain = f"{base}{i}.xyz"
        try:
            # HEAD isteği daha hızlıdır
            response = requests.head(test_domain, timeout=3, headers={"User-Agent": "Mozilla/5.0"})
            if response.status_code == 200:
                domain = test_domain
                print(f"✅ Domain bulundu: {domain}")
                break
            else:
                print(f"⏳ Denenen domain: {test_domain} (Status: {response.status_code})")
        except Exception as e:
            print(f"⏳ Denenen domain: {test_domain} (Hata: {str(e)[:30]}...)")
            continue

    if not domain:
        print("❌ UYARI: Hiçbir domain çalışmıyor - boş klasör oluşturulacak")

    # Kanallar
    # Yapı güncellendi: Artık logo URL'sini de içeriyor
    # İkinci betikteki tüm logolar aynı olduğu için o URL'yi kullandım.
    LOGO_URL = "https://i.ibb.co/v61Yw2ds/v-QSm-JSfa-S2apqzv-Rwlp-X2-Q.webp"
    
    channel_ids = {
        "yayinzirve": {"name": "beIN Sports 1 ☪️", "logo": LOGO_URL},
        "yayininat": {"name": "beIN Sports 1 ⭐", "logo": LOGO_URL},
        "yayin1": {"name": "beIN Sports 1 ♾️", "logo": LOGO_URL},
        "yayinb2": {"name": "beIN Sports 2", "logo": LOGO_URL},
        "yayinb3": {"name": "beIN Sports 3", "logo": LOGO_URL},
        "yayinb4": {"name": "beIN Sports 4", "logo": LOGO_URL},
        "yayinb5": {"name": "beIN Sports 5", "logo": LOGO_URL},
        "yayinbm1": {"name": "beIN Sports 1 Max", "logo": LOGO_URL},
        "yayinbm2": {"name": "beIN Sports 2 Max", "logo": LOGO_URL},
        "yayinss": {"name": "Saran Sports 1", "logo": LOGO_URL},
        "yayinss2": {"name": "Saran Sports 2", "logo": LOGO_URL},
        "yayint1": {"name": "Tivibu Sports 1", "logo": LOGO_URL},
        "yayint2": {"name": "Tivibu Sports 2", "logo": LOGO_URL},
        "yayint3": {"name": "Tivibu Sports 3", "logo": LOGO_URL},
        "yayint4": {"name": "Tivibu Sports 4", "logo": LOGO_URL},
        "yayinsmarts": {"name": "Smart Sports", "logo": LOGO_URL},
        "yayinsms2": {"name": "Smart Sports 2", "logo": LOGO_URL},
        "yayintrtspor": {"name": "TRT Spor", "logo": LOGO_URL},
        "yayintrtspor2": {"name": "TRT Spor 2", "logo": LOGO_URL},
        "yayinas": {"name": "A Spor", "logo": LOGO_URL},
        "yayinatv": {"name": "ATV", "logo": LOGO_URL},
        "yayintv8": {"name": "TV8", "logo": LOGO_URL},
        "yayintv85": {"name": "TV8.5", "logo": LOGO_URL},
        "yayinnbatv": {"name": "NBA TV", "logo": LOGO_URL},
        "yayinex1": {"name": "Tâbii 1", "logo": LOGO_URL},
        "yayinex2": {"name": "Tâbii 2", "logo": LOGO_URL},
        "yayinex3": {"name": "Tâbii 3", "logo": LOGO_URL},
        "yayinex4": {"name": "Tâbii 4", "logo": LOGO_URL},
        "yayinex5": {"name": "Tâbii 5", "logo": LOGO_URL},
        "yayinex6": {"name": "Tâbii 6", "logo": LOGO_URL},
        "yayinex7": {"name": "Tâbii 7", "logo": LOGO_URL},
        "yayinex8": {"name": "Tâbii 8", "logo": LOGO_URL},
        "yayintrt1": {"name": "TRT1", "logo": LOGO_URL},
    }

    # Klasör işlemleri
    folder_name = "channels_files"
    print(f"\n📁 Klasör işlemleri: {folder_name}")

    if os.path.exists(folder_name):
        try:
            shutil.rmtree(folder_name)
            print(f"🗑️  Eski klasör silindi: {folder_name}")
        except Exception as e:
            print(f"⚠️  Klasör silinemedi: {e}")

    try:
        os.makedirs(folder_name, exist_ok=True)
        print(f"✅ Klasör oluşturuldu: {folder_name}")
    except Exception as e:
        print(f"❌ KRİTİK HATA: Klasör oluşturulamadı: {e}")
        sys.exit(1)

    if not domain:
        print("\nℹ️  Domain bulunamadığı için dosya oluşturulmayacak.")
        print("📂 Sadece boş klasör oluşturuldu.")
        return

    # Kanalları işleme
    print(f"\n📺 {len(channel_ids)} kanal işleniyor...")
    created = 0
    failed = 0
    
    # Toplu M3U listesi için
    combined_m3u_lines = ["#EXTM3U"]
    combined_file_path = os.path.join(folder_name, "pygoals_iptv_listesi.m3u8")

    for i, (channel_id, channel_data) in enumerate(channel_ids.items(), 1):
        
        channel_name = channel_data["name"]
        logo_url = channel_data["logo"]
        
        try:
            print(f"\n[{i}/{len(channel_ids)}] {channel_name} işleniyor...")

            url = f"{domain}/channel.html?id={channel_id}"
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)

            if response.status_code != 200:
                print(f"❌ HTTP Hatası: {response.status_code}")
                failed += 1
                continue

            match = re.search(r'const baseurl = "(.*?)"', response.text)
            if not match:
                print("❌ BaseURL bulunamadı")
                failed += 1
                continue

            baseurl = match.group(1)
            encoded_url = quote(f"{baseurl}{channel_id}.m3u8", safe='')
            full_url = f"http://proxylendim101010.mywire.org/proxy.php?url={encoded_url}"

            # İstenen format (logo ve grup başlığı ile)
            extinf_line = f'#EXTINF:-1 tvg-id="sport.tr" tvg-name="TR:{channel_name}" tvg-logo="{logo_url}" group-title="TRGOALS Telegram @playtvmedya",TR:{channel_name}'

            # 1. Ayrı M3U dosyası için içerik
            # Orijinal betikteki gibi stream info satırını da ekleyelim
            content_individual = f"""#EXTM3U
{extinf_line}
#EXT-X-VERSION:3
#EXT-X-STREAM-INF:BANDWIDTH=5500000,AVERAGE-BANDWIDTH=8976000,RESOLUTION=1920x1080,CODECS="avc1.640028,mp4a.40.2",FRAME-RATE=25
{full_url}
"""
            # Güvenli dosya adı oluşturma
            safe_name = re.sub(r'[^\w\s.-]', '_', channel_name)
            safe_name = safe_name.replace(' ', '_') + ".m3u8"
            path = os.path.join(folder_name, safe_name)

            # Dosyayı yazma
            with open(path, "w", encoding="utf-8") as f:
                f.write(content_individual)

            print(f"✅ {channel_name} → {safe_name}")
            created += 1
            
            # 2. Toplu M3U listesine ekle
            combined_m3u_lines.append(extinf_line)
            combined_m3u_lines.append(full_url)

            time.sleep(0.1)

        except requests.exceptions.Timeout:
            print("❌ İstek zaman aşımına uğradı")
            failed += 1
        except requests.exceptions.RequestException as e:
            print(f"❌ Ağ hatası: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ Beklenmeyen hata: {e}")
            failed += 1

    # Toplu M3U dosyasını yaz
    if created > 0:
        try:
            with open(combined_file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(combined_m3u_lines))
            print(f"\n✅ Toplu M3U dosyası oluşturuldu: {os.path.basename(combined_file_path)}")
        except Exception as e:
            print(f"\n❌ Toplu M3U dosyası yazılırken hata oluştu: {e}")

    # Sonuç raporu
    print("\n" + "="*50)
    print("📊 İŞLEM SONUÇLARI")
    print("="*50)
    print(f"✅ Başarılı (Ayrı Dosyalar): {created}")
    print(f"❌ Başarısız: {failed}")
    print(f"📂 Çıktı Klasörü: {os.path.abspath(folder_name)}")
    if created > 0:
        print(f"📂 Toplu M3U: {os.path.abspath(combined_file_path)}")
        print("\n🎉 İşlem başarıyla tamamlandı!")
    else:
        print("\nℹ️  Hiç dosya oluşturulamadı, lütfen internet bağlantınızı kontrol edin.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ ANA KRİTİK HATA: {e}")
        sys.exit(1)
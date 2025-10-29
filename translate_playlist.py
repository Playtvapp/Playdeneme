import requests
import re
import sys

# İşlenecek M3U playlist'in URL'si
SOURCE_URL = "https://play-x.ru/playlist.php?token=cBzBp"

# Bulunacak orijinal grup adı
TARGET_GROUP_ORIGINAL = "ТУРЦИЯ(231)"
# Gruba verilecek yeni ad
TARGET_GROUP_NEW = "TÜRKİYE"

# Çıktı dosyasının adı
OUTPUT_FILE = "turkey_first_playlist.m3u"

def fetch_playlist(url):
    """Verilen URL'den playlist içeriğini indirir."""
    print(f"Playlist indiriliyor: {url}")
    
    # --- YENİ EKLENEN KISIM ---
    # Sunucunun bizi engellememesi için tarayıcı gibi davranıyoruz (User-Agent)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    # --- YENİ EKLENEN KISIM SONU ---

    try:
        # 10 saniye zaman aşımı ve YENİ headers ile GET isteği
        response = requests.get(url, timeout=10, headers=headers) # 'headers=headers' eklendi
        
        # Hata durumunda (4xx veya 5xx) exception fırlat
        response.raise_for_status()

        # İçeriğin metin olup olmadığını kontrol et
        if 'text' not in response.headers.get('Content-Type', ''):
            print(f"Hata: URL bir metin dosyası döndürmedi. Content-Type: {response.headers.get('Content-Type')}", file=sys.stderr)
            return None

        content = response.text

        # İçeriğin geçerli bir M3U olup olmadığını kontrol et
        if not content.strip().startswith("#EXTM3U"):
            print("Hata: İndirilen içerik geçerli bir M3U dosyası değil (Başlıkta #EXTM3U yok).", file=sys.stderr)
            return None

        print("Playlist başarıyla indirildi.")
        return content

    except requests.exceptions.RequestException as e:
        print(f"Hata: Playlist indirilemedi. {e}", file=sys.stderr)
        return None

def process_playlist(content):
    """
    M3U içeriğini işleyerek belirtilen grubu yeniden adlandırır ve başa taşır.
    """
    print(f"'{TARGET_GROUP_ORIGINAL}' grubu işleniyor...")

    lines = content.splitlines()

    if not lines:
        print("Hata: Playlist boş.", file=sys.stderr)
        return None

    # Başlık satırını ayır
    header_line = [lines[0]]
    # Hedef (Türkiye) ve diğer kanallar için ayrı listeler oluştur
    turkey_channels = []
    other_channels = []

    i = 1 # 0. satır başlık olduğu için 1'den başla
    while i < len(lines):
        line = lines[i].strip()

        # Kanal bilgi satırı mı diye kontrol et (#EXTINF)
        if line.startswith("#EXTINF:"):
            extinf_line = line

            # Grup başlığını bulmak için regex kullan
            group_match = re.search(r'group-title="([^"]+)"', extinf_line)
            current_group = group_match.group(1) if group_match else ""

            # Bir sonraki satırın URL olduğunu varsay
            url_line = ""
            if i + 1 < len(lines) and not lines[i+1].strip().startswith("#"):
                # URL satırı var
                url_line = lines[i+1].strip()
                lines_to_advance = 2 # 2 satır atla (EXTINF + URL)
            else:
                # Hatalı giriş (URL yok veya bir sonraki satır da # ile başlıyor)
                url_line = None
                lines_to_advance = 1 # Sadece 1 satır atla

            # Grubun hedef grup olup olmadığını kontrol et
            if current_group == TARGET_GROUP_ORIGINAL:
                # Evet, hedef grup.
                # Grup adını değiştir
                modified_extinf = extinf_line.replace(
                    f'group-title="{TARGET_GROUP_ORIGINAL}"', 
                    f'group-title="{TARGET_GROUP_NEW}"'
                )
                # Türkiye listesine ekle
                turkey_channels.append(modified_extinf)
                if url_line:
                    turkey_channels.append(url_line)
            else:
                # Hayır, başka bir grup.
                # Diğer kanallar listesine ekle
                other_channels.append(extinf_line)
                if url_line:
                    other_channels.append(url_line)

            i += lines_to_advance

        else:
            # #EXTINF ile başlamayan diğer satırlar (örn. #EXTGRP veya boş satırlar)
            if line: # Boş satırları atla
                other_channels.append(line)
            i += 1

    if not turkey_channels:
        print(f"Uyarı: '{TARGET_GROUP_ORIGINAL}' adında bir grup bulunamadı.")
    else:
        print(f"'{TARGET_GROUP_ORIGINAL}' grubu bulundu, '{TARGET_GROUP_NEW}' olarak yeniden adlandırıldı ve başa taşındı.")

    # Son listeyi birleştir: Başlık + Türkiye Kanalları + Diğer Kanallar
    final_lines = header_line + turkey_channels + other_channels

    # Satırları birleştirerek tek bir metin oluştur
    return "\n".join(final_lines)

def save_playlist(content, filename):
    """İşlenmiş içeriği bir dosyaya kaydeder."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Yeni playlist başarıyla '{filename}' dosyasına kaydedildi.")
    except IOError as e:
        print(f"Hata: Dosya kaydedilemedi. {e}", file=sys.stderr)

def main():
    """Ana fonksiyon"""
    content = fetch_playlist(SOURCE_URL)
    if content:
        processed_content = process_playlist(content)
        if processed_content:
            save_playlist(processed_content, OUTPUT_FILE)

if __name__ == "__main__":
    main()
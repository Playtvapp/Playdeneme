import json
import os
import subprocess # yt-dlp'yi çalıştırmak için eklendi
import sys

# Dosya adları
JSON_FILE = 'channels.json'
M3U_FILE = 'playlist.m3u'

def get_youtube_m3u8(video_url):
    """
    yt-dlp kullanarak bir YouTube URL'sinden .m3u8 linkini çeker.
    """
    print(f"  -> YouTube linki işleniyor: {video_url}")
    try:
        # yt-dlp'yi çağır:
        # -g: Sadece URL'yi al (video indirme)
        # -f "best[ext=m3u8]": En iyi M3U8 formatını seç
        # --no-playlist: Eğer bir oynatma listesi linki verilirse, sadece videoyu al
        process = subprocess.run(
            ['yt-dlp', '-g', '-f', 'best[ext=m3u8]', '--no-playlist', video_url],
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8'
        )
        
        # yt-dlp'nin çıktısı (stdout) bizim .m3u8 linkimizdir
        stream_url = process.stdout.strip()
        
        if not stream_url or not stream_url.startswith("https"):
            print(f"  -> Hata: Geçersiz m3u8 URL'si alındı: {stream_url}")
            return None
            
        print(f"  -> Başarılı: Taze .m3u8 linki bulundu.")
        return stream_url
        
    except subprocess.CalledProcessError as e:
        # Komut başarısız olursa (örn: video yok, yasaklı)
        print(f"  -> Hata: yt-dlp {video_url} için çalıştırılamadı. Hata: {e.stderr}")
        return None
    except Exception as e:
        print(f"  -> Beklenmedik Hata: {e}")
        return None

def build_m3u():
    print(f"{JSON_FILE} okunuyor...")
    
    try:
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            channels = json.load(f)
    except Exception as e:
        print(f"Hata: {JSON_FILE} dosyası okunamadı veya formatı bozuk. Hata: {e}")
        return

    print(f"{len(channels)} kanal bulundu. M3U oluşturuluyor...")

    # M3U içeriğini başlat
    m3u_content = "#EXTM3U\n"

    # Her kanal için M3U formatını oluştur
    for channel in channels:
        name = channel.get('name', 'Bilinmeyen Kanal')
        logo = channel.get('logo', '')
        category = channel.get('category', 'Genel')
        source_type = channel.get('source', 'direct') # Varsayılan 'direct'
        url = channel.get('url', '')

        if not url:
            print(f"Uyarı: '{name}' kanalı geçersiz URL nedeniyle atlandı.")
            continue
            
        final_stream_url = None
        
        # ------------------------------------
        # YENİ EKLENEN AKILLI SİSTEM
        # ------------------------------------
        if source_type == 'youtube':
            # Kaynak YouTube ise, taze linki çek
            final_stream_url = get_youtube_m3u8(url)
        else:
            # 'direct' veya tanımsız ise, linki olduğu gibi kullan
            final_stream_url = url
        # ------------------------------------

        if final_stream_url:
            # M3U formatı: #EXTINF:-1 tvg-logo="logo_url" group-title="kategori",Kanal Adı
            m3u_content += f'\n#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="{category}",{name}\n'
            m3u_content += f'{final_stream_url}\n'
        else:
            print(f"Uyarı: '{name}' kanalı (URL: {url}) için yayın linki alınamadı, listeye eklenmiyor.")

    # M3U dosyasını yaz
    try:
        with open(M3U_FILE, 'w', encoding='utf-8') as f:
            f.write(m3u_content)
        print(f"Başarılı! {M3U_FILE} dosyası oluşturuldu/güncellendi.")
    except Exception as e:
        print(f"Hata: {M3U_FILE} dosyası yazılamadı. Hata: {e}")

if __name__ == "__main__":
    build_m3u()
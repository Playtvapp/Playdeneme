import requests
import re
import time
from deep_translator import GoogleTranslator

# Çevrilecek M3U listesinin URL'si
M3U_URL = "https://play-x.ru/playlist.php?token=cBzBp"

# Çıktı dosyasının adı
OUTPUT_FILE = "playlist_tr.m3u"

# Çeviri için önbellek (API'ye aynı isteği tekrar tekrar atmamak için)
# Bu, "Новости" gibi bir kategoriyi 100 kere çevirmeye çalışmasını engeller.
translation_cache = {}

def translate_text(text):
    """
    Metni Rusça'dan Türkçe'ye çevirir ve önbelleğe alır.
    """
    if text in translation_cache:
        return translation_cache[text]
    
    # Metin boşsa veya sadece boşluk içeriyorsa çeviri yapma
    if not text or text.isspace():
        return text

    try:
        # API limitlerine takılmamak için her çeviri arasında kısa bir bekleme
        time.sleep(0.1) 
        
        translated = GoogleTranslator(source='ru', target='tr').translate(text)
        
        if translated:
            print(f"Çevrildi: '{text}' -> '{translated}'")
            translation_cache[text] = translated
            return translated
        else:
            # Çeviri başarısız olursa orijinal metni koru
            return text
            
    except Exception as e:
        print(f"Çeviri hatası: {e} - Orijinal metin kullanılıyor: {text}")
        return text

def process_m3u():
    """
    M3U listesini indirir, işler, çevirir ve yeni dosyayı kaydeder.
    """
    print(f"M3U listesi indiriliyor: {M3U_URL}")
    try:
        response = requests.get(M3U_URL, timeout=10)
        response.raise_for_status() # HTTP hatası varsa programı durdur
        lines = response.text.splitlines()
        print("Liste başarıyla indirildi.")
    except requests.RequestException as e:
        print(f"URL indirilemedi: {e}")
        return

    new_m3u_content = []
    
    # Gerekli Regex kalıpları
    group_title_re = re.compile(r'group-title="([^"]*)"')
    channel_name_re = re.compile(r',(.+)$') # Satırın sonundaki kanal adı (virgülden sonra)

    print("Liste işleniyor ve çevriliyor... (Bu işlem listenin uzunluğuna göre uzun sürebilir)")
    
    for line in lines:
        line = line.strip()
        
        if line.startswith("#EXTM3U"):
            new_m3u_content.append(line)
            continue
        
        if line.startswith("#EXTINF"):
            new_line = line
            
            # 1. Kategori Başlığını (group-title) bul ve çevir
            group_match = group_title_re.search(line)
            if group_match:
                original_group = group_match.group(1)
                translated_group = translate_text(original_group)
                # Orijinal başlığı yenisiyle değiştir
                new_line = new_line.replace(f'group-title="{original_group}"', f'group-title="{translated_group}"')
            
            # 2. Kanal Adını (virgülden sonraki kısım) bul ve çevir
            name_match = channel_name_re.search(line)
            if name_match:
                original_name = name_match.group(1)
                translated_name = translate_text(original_name)
                # Satırın sadece son kısmını (kanal adını) değiştir
                start_index = line.rfind(',') + 1
                new_line = new_line[:start_index] + translated_name
                
            new_m3u_content.append(new_line)
            
        elif line.startswith("http") or line.startswith("rtmp"):
            # Medya URL'si, olduğu gibi ekle
            new_m3u_content.append(line)
        else:
            # Diğer etiketleri (varsa) olduğu gibi ekle
            new_m3u_content.append(line)

    print(f"Çeviri tamamlandı. {OUTPUT_FILE} dosyası oluşturuluyor.")
    
    # Yeni M3U dosyasını UTF-8 formatında yaz
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            for item in new_m3u_content:
                f.write(f"{item}\n")
        print(f"İşlem başarıyla tamamlandı. Yeni liste '{OUTPUT_FILE}' olarak kaydedildi.")
    except IOError as e:
        print(f"Dosya yazılamadı: {e}")

if __name__ == "__main__":
    process_m3u()

import re
import sys
import time
from urllib.parse import urlparse, parse_qs, urljoin
from playwright.sync_api import sync_playwright, Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError

# --- HEDEF SİTE ---
# Bu betik, tvjustin.com ve onun dinamik "maç yayını" yapısını hedefler.
JUSTINTV_DOMAIN = "https://tvjustin.com/"

# --- PROXY AYARI ---
# İkinci betikten istenen proxy ayarı
# Bu proxy, M3U8 linklerinin başına eklenecek.
PROXY_PREFIX = "https://api.codetabs.com/v1/proxy/?quest="

# Kullanılacak User-Agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"

def scrape_default_channel_info(page):
    """
    Justin TV ana sayfasını ziyaret eder ve varsayılan iframe'den
    event URL'sini ve stream ID'sini alır. (Base URL'i bulmak için gereklidir)
    """
    print(f"\n📡 Varsayılan kanal bilgisi {JUSTINTV_DOMAIN} adresinden alınıyor...")
    try:
        page.goto(JUSTINTV_DOMAIN, timeout=25000, wait_until='domcontentloaded')

        iframe_selector = "iframe#customIframe"
        print(f"-> Varsayılan iframe ('{iframe_selector}') aranıyor...")
        page.wait_for_selector(iframe_selector, timeout=15000)
        iframe_element = page.query_selector(iframe_selector)

        if not iframe_element:
            print("❌ Ana sayfada 'iframe#customIframe' bulunamadı.")
            return None, None

        iframe_src = iframe_element.get_attribute('src')
        if not iframe_src:
            print("❌ Iframe 'src' özniteliği boş.")
            return None, None

        event_url = urljoin(JUSTINTV_DOMAIN, iframe_src)
        parsed_event_url = urlparse(event_url)
        query_params = parse_qs(parsed_event_url.query)
        stream_id = query_params.get('id', [None])[0]

        if not stream_id:
            print(f"❌ Event URL'sinde ({event_url}) 'id' parametresi bulunamadı.")
            return None, None

        print(f"✅ Varsayılan kanal bilgisi alındı: ID='{stream_id}', EventURL='{event_url}'")
        return event_url, stream_id

    except Exception as e:
        print(f"❌ Ana sayfaya ulaşılamadı veya iframe bilgisi alınamadı: {e.__class__.__name__} - {e}")
        return None, None

def extract_base_m3u8_url(page, event_url):
    """
    Verilen event URL'sine (event.html veya event3.html) gider ve
    JavaScript içeriğinden M3U8 Base URL'i (sunucu adresi) çıkarır.
    """
    try:
        print(f"\n-> M3U8 Base URL'i almak için Event sayfasına gidiliyor: {event_url}")
        page.goto(event_url, timeout=20000, wait_until="domcontentloaded")
        content = page.content()
        
        # '/checklist/' içeren sunucu adresini bulmak için Regex
        base_url_match = re.search(r"['\"](https?://[^'\"]+/checklist/)['\"]", content)
        if not base_url_match:
             base_url_match = re.search(r"streamUrl\s*=\s*['\"](https?://[^'\"]+/checklist/)['\"]", content)
        if not base_url_match:
            print(" -> ❌ Event sayfası kaynağında '/checklist/' ile biten base URL bulunamadı.")
            return None
        
        base_url = base_url_match.group(1)
        print(f"-> ✅ M3U8 Base URL bulundu: {base_url}")
        return base_url
    except Exception as e:
        print(f"-> ❌ Event sayfası işlenirken hata oluştu: {e}")
        return None

def scrape_all_channels(page):
    """
    Justin TV ana sayfasına gider, JS'in yüklenmesini bekler ve
    o an sitede listelenen TÜM kanalları (maçlar, ulusal kanallar vb.) kazır.
    Bu, ilk betiğin "Maç Yayınları" bulma mantığıdır.
    """
    print(f"\n📡 Tüm kanallar (maçlar dahil) {JUSTINTV_DOMAIN} adresinden çekiliyor...")
    channels = []
    try:
        print(f"-> Ana sayfaya gidiliyor ve ağ trafiğinin durması bekleniyor (Max 45sn)...")
        # 'networkidle' beklemesi, JS'in çalışıp kanal listesini yüklemesi için kritik öneme sahiptir.
        page.goto(JUSTINTV_DOMAIN, timeout=45000, wait_until='networkidle')
        print("-> Ağ trafiği durdu veya zaman aşımına yaklaşıldı.")

        print("-> DOM güncellemeleri için 5 saniye bekleniyor...")
        page.wait_for_timeout(5000)

        # Sitedeki her bir kanal/maç bu seçiciyle eşleşir
        mac_item_selector = ".mac[data-url]"
        print(f"-> Sayfa içinde '{mac_item_selector}' elementleri var mı kontrol ediliyor...")

        elements_exist = page.evaluate(f'''() => {{
            return document.querySelector('{mac_item_selector}') !== null;
        }}''')

        if not elements_exist:
            print(f"❌ Sayfa içinde '{mac_item_selector}' elemanları bulunamadı.")
            print("❌ Sitenin yapısı değişmiş veya kanallar yüklenememiş olabilir.")
            return []

        print("-> ✅ Kanallar sayfada mevcut. Bilgiler çıkarılıyor...")
        channel_elements = page.query_selector_all(mac_item_selector)
        print(f"-> {len(channel_elements)} adet potansiyel kanal elemanı bulundu.")

        for element in channel_elements:
            name_element = element.query_selector(".takimlar")
            channel_name = name_element.inner_text().strip() if name_element else "İsimsiz Kanal"
            channel_name_clean = channel_name.replace('CANLI', '').strip()

            data_url = element.get_attribute('data-url')
            stream_id = None
            if data_url:
                try:
                    # ID'yi data-url'den parse et (örn: event3.html?id=123)
                    parsed_data_url = urlparse(data_url)
                    query_params = parse_qs(parsed_data_url.query)
                    stream_id = query_params.get('id', [None])[0]
                except Exception:
                    pass

            if stream_id: # Sadece geçerli bir ID varsa listeye ekle
                time_element = element.query_selector(".saat")
                time_str = time_element.inner_text().strip() if time_element else None
                
                if time_str and time_str != "CANLI":
                     # Saati olanları (örn: 21:00) maç yayını olarak formatla
                     final_channel_name = f"{channel_name_clean} ({time_str})"
                else:
                     final_channel_name = channel_name_clean

                channels.append({
                    'name': final_channel_name,
                    'id': stream_id
                })

        # Kanalları isme göre sırala
        channels.sort(key=lambda x: x['name'])

        print(f"✅ {len(channels)} adet kanal bilgisi başarıyla çıkarıldı.")
        return channels

    except Exception as e:
        print(f"❌ Kanal listesi işlenirken hata oluştu: {e}")
        return []

def get_channel_group(channel_name):
    """
    Kanal isimlerine göre M3U8 listesinde gruplama yapar.
    """
    channel_name_lower = channel_name.lower()
    group_mappings = {
        'BeinSports': ['bein sports', 'beın sports', ' bs', ' bein '],
        'S Sports': ['s sport'],
        'Tivibu': ['tivibu spor', 'tivibu'],
        'Exxen': ['exxen'],
        'Ulusal Kanallar': ['a spor', 'trt spor', 'trt 1', 'tv8', 'atv', 'kanal d', 'show tv', 'star tv', 'trt yıldız', 'a2'],
        'Spor': ['smart spor', 'nba tv', 'eurosport', 'sport tv', 'premier sports', 'ht spor', 'sports tv', 'd smart', 'd-smart'],
        'Yarış': ['tjk tv'],
        'Belgesel': ['national geographic', 'nat geo', 'discovery', 'dmax', 'bbc earth', 'history'],
        'Film & Dizi': ['bein series', 'bein movies', 'movie smart', 'filmbox', 'sinema tv'],
        'Haber': ['haber', 'cnn', 'ntv'],
        'Diğer': ['gs tv', 'fb tv', 'cbc sport']
    }
    for group, keywords in group_mappings.items():
        for keyword in keywords:
            if keyword in channel_name_lower:
                return group
    # Saati olan (örn: 21:00) veya ' - ' içeren (örn: Takım A - Takım B)
    # yayınları "Maç Yayınları" grubuna ata
    if re.search(r'\d{2}:\d{2}', channel_name): return "Maç Yayınları"
    if ' - ' in channel_name: return "Maç Yayınları"
    
    return "Diğer Kanallar"

def main():
    with sync_playwright() as p:
        print("🚀 Playwright ile Justin TV Proxy'li M3U8 Kanal İndirici Başlatılıyor...")
        print(f"ℹ️  Hedef Site: {JUSTINTV_DOMAIN}")
        print(f"ℹ️  Proxy: {PROXY_PREFIX}")

        browser = p.chromium.launch(headless=True) # Arka planda çalışır
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()

        # 1. Adım: Varsayılan kanaldan event URL'sini al (Base URL için)
        default_event_url, _ = scrape_default_channel_info(page)
        if not default_event_url:
            print("❌ UYARI: Varsayılan kanal bilgisi alınamadı, M3U8 Base URL bulunamıyor. İşlem sonlandırılıyor.")
            browser.close()
            sys.exit(1)

        # 2. Adım: event URL'den M3U8 Base URL'ini çıkar
        base_m3u8_url = extract_base_m3u8_url(page, default_event_url)
        if not base_m3u8_url:
            print("❌ UYARI: M3U8 Base URL (sunucu adresi) alınamadı. İşlem sonlandırılıyor.")
            browser.close()
            sys.exit(1)

        # 3. Adım: Ana sayfadaki tüm dinamik kanalları (maçlar vb.) kazı
        channels = scrape_all_channels(page)
        if not channels:
            print("❌ UYARI: Hiçbir kanal bulunamadı, işlem sonlandırılıyor.")
            browser.close()
            sys.exit(1)

        m3u_content = []
        output_filename = "justintv_proxy_kanallar.m3u8"
        print(f"\n📺 {len(channels)} kanal için PROXY'li M3U8 linkleri oluşturuluyor...")
        created = 0

        # M3U8 dosyası için gerekli başlıklar
        player_origin_host = JUSTINTV_DOMAIN.rstrip('/')
        player_referer = JUSTINTV_DOMAIN
        m3u_header_lines = [
            "#EXTM3U",
            f"#EXT-X-USER-AGENT:{USER_AGENT}",
            f"#EXT-X-REFERER:{player_referer}",
            f"#EXT-X-ORIGIN:{player_origin_host}"
        ]

        for i, channel_info in enumerate(channels, 1):
            channel_name = channel_info['name']
            stream_id = channel_info['id']
            group_name = get_channel_group(channel_name)

            # Orijinal M3U8 linkini oluştur (Base URL + Stream ID)
            original_m3u8_link = f"{base_m3u8_url}{stream_id}.m3u8"
            
            # --- YENİ: Proxy Entegrasyonu ---
            # Linkin başına istenen proxy'yi ekle
            proxied_m3u8_link = f"{PROXY_PREFIX}{original_m3u8_link}"
            # --- Bitti ---

            m3u_content.append(f'#EXTINF:-1 tvg-name="{channel_name}" group-title="{group_name}",{channel_name}')
            m3u_content.append(proxied_m3u8_link) # Dosyaya proxy'li linki ekle
            created += 1

        browser.close()

        if created > 0:
            with open(output_filename, "w", encoding="utf-8") as f:
                f.write("\n".join(m3u_header_lines))
                f.write("\n")
                f.write("\n".join(m3u_content))
            print(f"\n\n📂 {created} kanal başarıyla '{output_filename}' dosyasına kaydedildi.")
            print(f"ℹ️  Tüm linkler {PROXY_PREFIX} ile proxy'lenmiştir.")
        else:
            print("\n\nℹ️  Geçerli hiçbir M3U8 linki oluşturulamadığı için dosya oluşturulmadı.")

        print("\n🎉 İşlem tamamlandı!")

if __name__ == "__main__":
    main()
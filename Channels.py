import requests
from cloudscraper import CloudScraper

class RecTVUrlFetcher:
    def __init__(self):
        self.session = CloudScraper()

    def get_rectv_domain(self):
        try:
            response = self.session.post(
                url="https://firebaseremoteconfig.googleapis.com/v1/projects/791583031279/namespaces/firebase:fetch",
                headers={
                    "X-Goog-Api-Key": "AIzaSyBbhpzG8Ecohu9yArfCO5tF13BQLhjLahc",
                    "X-Android-Package": "com.rectv.shot",
                    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 12)",
                },
                json={
                    "appBuild": "81",
                    "appInstanceId": "evON8ZdeSr-0wUYxf0qs68",
                    "appId": "1:791583031279:android:1",
                }
            )
            main_url = response.json().get("entries", {}).get("api_url", "")
            base_domain = main_url.replace("/api/", "")
            print(f"🟢 Güncel RecTV domain alındı: {base_domain}")
            return base_domain
        except Exception as e:
            print("🔴 RecTV domain alınamadı!")
            print(f"Hata: {type(e).__name__} - {e}")
            return None

def get_all_channels(base_domain):
    all_channels = []
    page = 0

    while True:
        url = f"{base_domain}/api/channel/by/filtres/0/0/{page}/4F5A9C3D9A86FA54EACEDDD635185/c3c5bd17-e37b-4b94-a944-8a3688a30452"
        print(f"🔍 İstek atılıyor: {url}")
        response = requests.get(url)

        if response.status_code != 200:
            print(f"❌ HTTP {response.status_code}")
            break

        data = response.json()
        if not data:
            print(f"✅ Veri bitti, {page} sayfa tarandı.")
            break

        all_channels.extend(data)
        page += 1

    return all_channels

def extract_m3u8_links(channels):
    playlist_lines = ['#EXTM3U']


    priority_order = ["Spor", "Haber", "Ulusal", "Sinema","Belgesel","Diğer", "Müzik"]

    grouped_channels = {}

    for channel in channels:
        title = channel.get("title", "Bilinmeyen")
        logo = channel.get("image", "")
        channel_id = str(channel.get("id", ""))
        categories = channel.get("categories", [])
        group_title = categories[0]["title"] if categories else "Diğer"

        sources = channel.get("sources", [])
        for source in sources:
            url = source.get("url")
            if url and url.endswith(".m3u8"):
                quality = source.get("quality")
                quality_str = f" [{quality}]" if quality and quality.lower() != "none" else ""
                entry = (
                    f'#EXTINF:-1 tvg-id="{channel_id}" tvg-logo="{logo}" tvg-name="{title}" group-title="{group_title}",{title}{quality_str}',
                    '#EXTVLCOPT:http-user-agent=okhttp/4.12.0',
                    '#EXTVLCOPT:http-referrer=https://twitter.com',
                    url
                )


                grouped_channels.setdefault(group_title, []).append(entry)


    for group in priority_order + sorted(set(grouped_channels.keys()) - set(priority_order)):
        entries = grouped_channels.get(group)
        if entries:

            sorted_entries = sorted(entries, key=lambda e: e[0].split(",")[-1].lower())
            for entry in sorted_entries:
                playlist_lines.extend(entry)

    return '\n'.join(playlist_lines)



def save_to_file(content, filename="rectv_kanallar.m3u"):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    print(f" M3U dosyası kaydedildi: {filename}")

if __name__ == "__main__":
    fetcher = RecTVUrlFetcher()
    domain = fetcher.get_rectv_domain()

    if domain:
        kanallar = get_all_channels(domain)
        print(f" Toplam {len(kanallar)} kanal bulundu.")
        m3u_content = extract_m3u8_links(kanallar)
        save_to_file(m3u_content)
    else:
        print("Geçerli domain alınamadı.")

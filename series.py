import requests
import time

SERIE_URL = "https://m.prectv49.sbs/api/serie/by/filtres/0/created/{page}/4F5A9C3D9A86FA54EACEDDD635185/c3c5bd17-e37b-4b94-a944-8a3688a30452/"
EPISODE_URL_TEMPLATE = "https://m.prectv49.sbs/api/season/by/serie/{id}/4F5A9C3D9A86FA54EACEDDD635185/c3c5bd17-e37b-4b94-a944-8a3688a30452/"

HEADERS = {
    "user-agent": "okhttp/4.12.0"
}


def get_all_series():
    all_series = []
    page = 0

    while True:
        url = SERIE_URL.format(page=page)
        print(f"🔍 Sayfa {page} çekiliyor: {url}")
        response = requests.get(url, headers=HEADERS)

        if response.status_code != 200:
            print(f"❌ HTTP {response.status_code}")
            break

        data = response.json()
        if not data:
            print(f"✅ Tüm diziler alındı. Toplam sayfa: {page}")
            break

        all_series.extend(data)
        page += 1

    return all_series


def get_episodes(serie_id):
    url = EPISODE_URL_TEMPLATE.format(id=serie_id)
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        return []

    try:
        return response.json()
    except Exception as e:
        print(f"⚠️ JSON parse hatası: {e}")
        return []


def extract_serie_links(series):
    playlist_lines = ['#EXTM3U']

    for serie in series:
        title = serie.get("title", "Bilinmeyen")
        logo = serie.get("image", "")
        serie_id = str(serie.get("id", ""))
        year = serie.get("year", "")
        group = title  # group-title'ı dizinin ismiyle doldurduk

        print(f"🎞️ Dizi: {title} ({serie_id})")

        # Eğer ana kaynak varsa (çok nadir)
        sources = serie.get("sources", [])
        for source in sources:
            url = source.get("url")
            if url:
                # URL'yi yeni formatta oluşturuyoruz
                url = f"https://1.nejyoner19.workers.dev/?url={url}"

                quality = source.get("quality", "")
                quality_str = f" [{quality}]" if quality else ""
                entry = (
                    f'#EXTINF:-1 tvg-id="{serie_id}" tvg-logo="{logo}" tvg-name="{title}" group-title="{group}",{title} ({year}){quality_str}',
                    '#EXTVLCOPT:http-user-agent=okhttp/4.12.0',
                    '#EXTVLCOPT:http-referrer=https://twitter.com',
                    url
                )
                playlist_lines.extend(entry)

        # Bölüm çekimi
        seasons = get_episodes(serie_id)
        for season in seasons:
            season_title = season.get("title", "Sezon")
            episodes = season.get("episodes", [])
            for ep in episodes:
                ep_title = ep.get("title", "Bölüm")
                for source in ep.get("sources", []):
                    url = source.get("url")
                    if url and url.endswith(".m3u8"):
                        # URL'yi yeni formatta oluşturuyoruz
                        url = f"https://1.nejyoner19.workers.dev/?url={url}"

                        quality = source.get("quality", "")
                        quality_str = f" [{quality}]" if quality else ""
                        entry = (
                            f'#EXTINF:-1 tvg-id="{serie_id}" tvg-logo="{logo}" tvg-name="{title}" group-title="{group}",{title} - {season_title} - {ep_title}{quality_str}',
                            '#EXTVLCOPT:http-user-agent=okhttp/4.12.0',
                            '#EXTVLCOPT:http-referrer=https://twitter.com',
                            url
                        )
                        playlist_lines.extend(entry)

        time.sleep(0.3)  # Aşırı istekten kaçınmak için kısa gecikme

    return '\n'.join(playlist_lines)


def save_to_file(content, filename="rectv_series.m3u"):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"📁 M3U dosyası kaydedildi: {filename}")


if __name__ == "__main__":
    series = get_all_series()
    print(f"\n📺 Toplam {len(series)} dizi bulundu.\n")

    m3u_content = extract_serie_links(series)
    save_to_file(m3u_content)

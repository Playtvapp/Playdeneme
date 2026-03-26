import requests
from bs4 import BeautifulSoup
import json
import os

BASE_URL = "https://tizam.video" # URL adresini kendi kaynağına göre güncelleyebilirsin
START_URL = f"{BASE_URL}/fil_my_dlya_vzroslyh/"

def get_video_details(detail_url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(detail_url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Başlığı çek
        title_tag = soup.find('h1')
        title = title_tag.text.strip() if title_tag else "İsimsiz İçerik"
        
        # Video oynatıcıyı bul
        video_tag = soup.find('video', class_='video-js')
        if not video_tag:
            return None
            
        # Görseli al (poster niteliğinden)
        image_url = video_tag.get('poster', '')
        if image_url and image_url.startswith('/'):
            image_url = BASE_URL + image_url
            
        # MP4 bağlantısını bul
        source_tags = video_tag.find_all('source', type='video/mp4')
        mp4_url = ""
        for source in source_tags:
            mp4_url = source.get('src', '')
            if mp4_url:
                # İstersen burada "data-res" değerine göre 720p veya 480p seçimi yapabilirsin
                break 
                
        if mp4_url:
            return {"title": title, "image": image_url, "url": mp4_url}
            
    except Exception as e:
        print(f"Hata oluştu ({detail_url}): {e}")
    return None

def main():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }
    response = requests.get(START_URL, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Ana sayfadaki içerik linklerini bul (html içindeki item__cover class'ına göre)
    items = soup.find_all('a', class_='item__cover')
    
    playlist_data = []
    
    # İşlemi hızlandırmak için örnek olarak ilk 20 içeriği alıyoruz.
    # Tümünü çekmek istersen [:20] kısmını kaldırabilirsin.
    for item in items[:20]:
        link = item.get('href')
        if link:
            detail_url = BASE_URL + link if link.startswith('/') else link
            print(f"İşleniyor: {detail_url}")
            
            details = get_video_details(detail_url)
            if details:
                playlist_data.append(details)
                
    # 1. JSON Formatında Kaydet
    with open('playlist.json', 'w', encoding='utf-8') as f:
        json.dump(playlist_data, f, ensure_ascii=False, indent=4)
        print("playlist.json başarıyla oluşturuldu.")
        
    # 2. M3U Formatında Kaydet
    with open('playlist.m3u', 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for item in playlist_data:
            f.write(f'#EXTINF:-1 tvg-logo="{item["image"]}",{item["title"]}\n')
            f.write(f'{item["url"]}\n')
        print("playlist.m3u başarıyla oluşturuldu.")

if __name__ == "__main__":
    main()

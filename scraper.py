import requests
from bs4 import BeautifulSoup
import json

BASE_URL = "https://tizam.video" # Sitenin güncel adresi
START_URL = f"{BASE_URL}/fil_my_dlya_vzroslyh/"

def get_video_details(detail_url):
    """Detay sayfasına giderek .mp4 uzantısını ve afişi çeker."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
        }
        response = requests.get(detail_url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        video_tag = soup.find('video', class_='video-js')
        if not video_tag:
            return None, None
            
        source_tags = video_tag.find_all('source', type='video/mp4')
        mp4_url = ""
        
        for source in source_tags:
            mp4_url = source.get('src', '')
            if source.get('data-res') == '720':
                break
        
        poster = video_tag.get('poster', '')
        if poster and poster.startswith('/'):
            poster = BASE_URL + poster
            
        return mp4_url, poster
    except Exception as e:
        print(f"Detay çekme hatası ({detail_url}): {e}")
        return None, None

def main():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }
    
    print("Ana sayfa taranıyor...")
    response = requests.get(START_URL, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    items = soup.find_all('div', class_='item')
    playlist_data = []
    valid_count = 0
    
    for item in items:
        # Şimdilik testi hızlı yapmak için ilk 10 "geçerli" filmi alıyoruz
        # Tüm siteyi çekmek istersen bu iki satırı (if valid_count... ve break) silebilirsin.
        if valid_count >= 10: 
            break
            
        a_tag = item.find('a', class_='item__cover')
        if not a_tag:
            continue
            
        link = a_tag.get('href', '')
        
        # KATEGORİ FİLTRESİ: Sadece .html ile biten asıl film sayfalarını kabul et
        if not link or ".html" not in link:
            continue
            
        detail_url = BASE_URL + link if link.startswith('/') else link
        
        title_tag = item.find('h3', class_='item__title')
        title = title_tag.text.strip() if title_tag else "İsimsiz Video"
        
        img_tag = a_tag.find('img', class_='item__img')
        thumb_url = img_tag.get('src', '') if img_tag else ""
        if thumb_url and thumb_url.startswith('/'):
            thumb_url = BASE_URL + thumb_url
            
        print(f"İşleniyor: {title}")
        
        mp4_url, poster_url = get_video_details(detail_url)
        
        if mp4_url:
            final_img = poster_url if poster_url else thumb_url
            playlist_data.append({
                "title": title,
                "image": final_img,
                "url": mp4_url
            })
            valid_count += 1
            
    with open('playlist.json', 'w', encoding='utf-8') as f:
        json.dump(playlist_data, f, ensure_ascii=False, indent=4)
        print("-> playlist.json başarıyla oluşturuldu!")
        
    with open('playlist.m3u', 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for data in playlist_data:
            f.write(f'#EXTINF:-1 tvg-logo="{data["image"]}",{data["title"]}\n')
            f.write(f'{data["url"]}\n')
        print("-> playlist.m3u başarıyla oluşturuldu!")

if __name__ == "__main__":
    main()

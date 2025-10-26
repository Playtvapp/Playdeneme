import streamlink
import sys
import os 
import json
import traceback # Hata ayıklama için eklendi

def info_to_text(stream_info, url):
    """M3U8 dosyası için #EXT-X-STREAM-INF satırını oluşturur."""
    text = '#EXT-X-STREAM-INF:'
    if stream_info.program_id:
        text = text + 'PROGRAM-ID=' + str(stream_info.program_id) + ','
    if stream_info.bandwidth:
        text = text + 'BANDWIDTH=' + str(stream_info.bandwidth) + ','
    if stream_info.codecs:
        text = text + 'CODECS="'
        codecs = stream_info.codecs
        for i in range(0, len(codecs)):
            text = text + codecs[i]
            if len(codecs) - 1 != i:
                text = text + ','
        text = text + '",'
    if stream_info.resolution and stream_info.resolution.width:
        text = text + 'RESOLUTION=' + str(stream_info.resolution.width) + 'x' + str(stream_info.resolution.height) 

    text = text + "\n" + url + "\n"
    return text

def create_simple_m3u8(stream_url):
    """
    Doğrudan stream URL'leri (YouTube gibi) için basit, tek girişli bir M3U8 metni oluşturur.
    """
    text = "#EXTM3U\n"
    text += "#EXT-X-VERSION:3\n"
    text += f"#EXT-X-STREAM-INF:BANDWIDTH=8000000,PROGRAM-ID=1\n"
    text += f"{stream_url}\n"
    return text

def main():
    print("=== Starting stream processing (v3 - Robust YouTube/Direct Stream Support) ===")

    # 1. Config Dosyasını Yükle
    config_file = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    print(f"Loading config from: {config_file}")

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ ERROR loading config file: {e}")
        sys.exit(1)

    # 2. Çıktı Klasörlerini Ayarla ve Oluştur
    folder_name = config["output"]["folder"]
    best_folder_name = config["output"].get("bestFolder", "best") 
    master_folder_name = config["output"].get("masterFolder", "master")
    
    current_dir = os.getcwd()
    root_folder = os.path.join(current_dir, folder_name)
    
    best_folder = root_folder
    if best_folder_name: 
        best_folder = os.path.join(root_folder, best_folder_name)

    master_folder = root_folder
    if master_folder_name: 
        master_folder = os.path.join(root_folder, master_folder_name)

    print(f"Creating folders:")
    print(f"  Root: {root_folder}")
    print(f"  Best Folder: {best_folder}")
    print(f"  Master Folder: {master_folder}")

    os.makedirs(best_folder, exist_ok=True)
    if master_folder_name: 
        os.makedirs(master_folder, exist_ok=True)


    channels = config["channels"]
    print(f"\n=== Processing {len(channels)} channels ===\n")

    success_count = 0
    fail_count = 0

    # 3. Kanalları Tek Tek İşle (Ana Döngü)
    for idx, channel in enumerate(channels, 1):
        slug = channel.get("slug", "unknown")
        url = channel.get("url", "")
        master_file_path = os.path.join(master_folder, slug + ".m3u8")
        best_file_path = os.path.join(best_folder, slug + ".m3u8")

        print(f"[{idx}/{len(channels)}] Processing: {slug} (URL: {url})")

        try:
            # 4. Streamlink ile Yayınları Çek
            streams = streamlink.streams(url)

            # Gelişmiş Loglama: Hangi yayınların bulunduğunu göster
            if streams:
                print(f"  ℹ️  Available streams: {list(streams.keys())}")
            else:
                print(f"  ⚠️  No streams found for {slug} at all.")
                fail_count += 1
                if os.path.isfile(master_file_path): os.remove(master_file_path)
                if os.path.isfile(best_file_path): os.remove(best_file_path)
                continue

            # 5. YENİ: Güçlü Stream Seçimi
            stream_obj = None
            if 'best' in streams:
                stream_obj = streams['best']
                print("  ℹ️  Using 'best' stream key.")
            else:
                # 'best' yoksa, 'audio' olmayan son stream'i (genelde en yüksek kalite) seç
                video_streams = [key for key in streams.keys() if 'audio' not in key]
                if video_streams:
                    fallback_key = video_streams[-1] # Listenin sonuncusunu al
                    stream_obj = streams[fallback_key]
                    print(f"  ℹ️  'best' key not found. Using fallback: '{fallback_key}'")
                else:
                    print(f"  ⚠️  No video streams found (only audio?). Skipping.")
                    fail_count += 1
                    continue
            
            # --- Buradan sonrası 'stream_obj' kullanarak devam eder ---

            master_text = ''
            best_text = ''

            # 6. YAYIN TİPİNİ KONTROL ET
            
            # SENARYO 1: Yayın, HLS Master Playlist içeriyor (Twitch gibi)
            if hasattr(stream_obj, 'multivariant') and stream_obj.multivariant:
                print(f"  ℹ️  HLS Multivariant stream found (e.g., Twitch). Processing all resolutions.")
                playlists = stream_obj.multivariant.playlists
                previous_res_height = 0

                http_flag = False
                if url.startswith("http://"):
                    plugin_name, plugin_type, given_url = streamlink.session.Streamlink().resolve_url(url)
                    http_flag = True

                for playlist in playlists:
                    uri = playlist.uri
                    info = playlist.stream_info
                    if info.video != "audio_only": 
                        sub_text = info_to_text(info, uri)
                        if info.resolution.height > previous_res_height:
                            master_text = sub_text + master_text
                            best_text = sub_text
                        else:
                            master_text = master_text + sub_text
                        previous_res_height = info.resolution.height
                
                if master_text:
                    if stream_obj.multivariant.version:
                        master_text = '#EXT-X-VERSION:' + str(stream_obj.multivariant.version) + "\n" + master_text
                        best_text = '#EXT-X-VERSION:' + str(stream_obj.multivariant.version) + "\n" + best_text
                    master_text = '#EXTM3U\n' + master_text
                    best_text = '#EXTM3U\n' + best_text
                
                if http_flag and plugin_name == "cinergroup":
                    master_text = master_text.replace("https://", "http://")
                    best_text = best_text.replace("https://", "http://")

            # SENARYO 2: Yayın, doğrudan bir stream linki (YouTube, Kick'in bazen)
            else:
                print(f"  ℹ️  Direct stream found (e.g., YouTube/Kick). Using direct .url.")
                best_stream_url = stream_obj.url
                master_text = create_simple_m3u8(best_stream_url)
                best_text = master_text 

            # 7. Dosyaları Yaz
            if master_text:
                with open(master_file_path, "w+", encoding="utf-8") as master_file:
                    master_file.write(master_text)
                if best_file_path != master_file_path:
                    with open(best_file_path, "w+", encoding="utf-8") as best_file:
                        best_file.write(best_text)
                print(f"  ✅ Success - Files created")
                success_count += 1
            else:
                print(f"  ⚠️  No content generated for {slug}. Cleaning up old files.")
                if os.path.isfile(master_file_path): os.remove(master_file_path)
                if os.path.isfile(best_file_path): os.remove(best_file_path)
                fail_count += 1

        except Exception as e:
            print(f"  ❌ ERROR processing {slug}: {str(e)}")
            # YENİ: Hatanın tam detayını loglara yazdır
            print(f"  {traceback.format_exc()}")
            if os.path.isfile(master_file_path): os.remove(master_file_path)
            if os.path.isfile(best_file_path): os.remove(best_file_path)
            fail_count += 1

    print(f"\n=== Summary ===")
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed: {fail_count}")
    print(f"Total: {len(channels)}")

if __name__ == "__main__":
    main()
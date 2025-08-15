#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DMAX scraper (yalnızca M3U üretir)
- all.m3u       → bu .py dosyasının olduğu klasöre
- programlar/*  → her dizi için ayrı M3U (aynı klasör altındaki 'programlar' klasörüne)

Kullanım:
  python dmax_scraper.py
  python dmax_scraper.py 10
  python dmax_scraper.py 10 50
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from requests.adapters import HTTPAdapter, Retry
from slugify import slugify

# ============================
# ÇIKTI KONUMU (.py ile aynı klasör)
# ============================
BASE_DIR = Path(__file__).resolve().parent

# Tek dosyalık birleşik liste: ./all.m3u
ALL_M3U_DIR = str(BASE_DIR)
ALL_M3U_NAME = "DMAX"  # all.m3u

# Dizi bazlı listeler: ./programlar/*.m3u
SERIES_M3U_DIR = str(BASE_DIR / "programlar")
SERIES_MASTER = False  # True yaparsan ./programlar/0.m3u da üretir

# ============================
# M3U YARDIMCILARI
# ============================

def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def _atomic_write(path: str, text: str) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(tmp, path)

def _safe_series_filename(name: str) -> str:
    return slugify((name or "dizi").lower()) + ".m3u"

def _pick_stream_url(ep: Dict[str, Any]) -> Optional[str]:
    url = ep.get("stream_url")
    if url:
        return url
    cands = ep.get("stream_url_candidates")
    if isinstance(cands, (list, tuple)) and cands:
        return cands[0]
    return None

def create_m3us(channel_folder_path: str,
                data: List[Dict[str, Any]],
                master: bool = False,
                base_url: str = "") -> None:
    """
    Her dizi için ayrı .m3u üretir, opsiyonel master (0.m3u) oluşturur.
    NOT: Bölüm satırlarında tvg-logo olarak SERİ (program) posteri kullanılır.
    """
    _ensure_dir(channel_folder_path)
    master_lines: List[str] = ["#EXTM3U"] if master else []

    if base_url and not base_url.endswith(("/", "\\")):
        base_url = base_url + "/"

    for serie in (data or []):
        episodes = serie.get("episodes") or []
        if not episodes:
            continue

        series_name = (serie.get("name") or "Bilinmeyen Seri").strip()
        series_logo = (serie.get("img") or "").strip()  # seri posteri
        plist_name = _safe_series_filename(series_name)
        plist_path = os.path.join(channel_folder_path, plist_name)

        lines: List[str] = ["#EXTM3U"]
        for ep in episodes:
            stream = _pick_stream_url(ep)
            if not stream:
                continue
            ep_name = ep.get("name") or "Bölüm"

            # Seri posteri yoksa son çare bölüm resmi
            logo_for_line = series_logo or ep.get("img") or ""
            group = series_name.replace('"', "'")
            lines.append(f'#EXTINF:-1 tvg-logo="{logo_for_line}" group-title="{group}",{ep_name}')
            lines.append(stream)

        if len(lines) > 1:
            _atomic_write(plist_path, "\n".join(lines) + "\n")
            if master:
                master_lines.append(f'#EXTINF:-1 tvg-logo="{series_logo}", {series_name}')
                master_lines.append(f'{base_url}{plist_name}')

    if master:
        master_path = os.path.join(channel_folder_path, "0.m3u")
        _atomic_write(master_path, "\n".join(master_lines) + "\n")

def create_single_m3u(channel_folder_path: str,
                      data: List[Dict[str, Any]],
                      custom_path: str = "0") -> None:
    """
    Tüm dizilerin tüm bölümlerini tek bir .m3u dosyasında toplar.
    NOT: Bölüm satırlarında tvg-logo olarak SERİ (program) posteri kullanılır.
    """
    _ensure_dir(channel_folder_path)
    master_path = os.path.join(channel_folder_path, f"{custom_path}.m3u")

    lines: List[str] = ["#EXTM3U"]
    for serie in (data or []):
        series_name = (serie.get("name") or "Bilinmeyen Seri").strip()
        series_logo = (serie.get("img") or "").strip()  # seri posteri
        episodes = serie.get("episodes") or []
        for ep in episodes:
            stream = _pick_stream_url(ep)
            if not stream:
                continue
            ep_name = ep.get("name") or "Bölüm"

            logo_for_line = series_logo or ep.get("img") or ""
            group = series_name.replace('"', "'")
            lines.append(f'#EXTINF:-1 tvg-logo="{logo_for_line}" group-title="{group}",{ep_name}')
            lines.append(stream)

    _atomic_write(master_path, "\n".join(lines) + "\n")

# ============================
# SCRAPER (DAYANIKLI SÜRÜM)
# ============================

BASE_URL = "https://www.dmax.com.tr/"
AJAX_URL = urljoin(BASE_URL, "ajax/more")
SITE_REFERER = BASE_URL
STREAM_BASE = "https://dygvideo.dygdigital.com/api/redirect"
PUBLISHER_IDS = (27, 20)          # DMAX genelde 27; alternatif olarak 20'yi de dene
SECRET_KEY = "NtvApiSecret2014*"   # site yapısı değişirse çalışmayabilir

REQUEST_TIMEOUT = 15
REQUEST_PAUSE = 0.2
BACKOFF_FACTOR = 0.6
MAX_RETRIES = 5

DEFAULT_HEADERS = {
    "Referer": SITE_REFERER,
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("dmax-scraper")

SESSION = requests.Session()
retries = Retry(
    total=MAX_RETRIES,
    backoff_factor=BACKOFF_FACTOR,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=frozenset(["GET", "POST"]),
    raise_on_status=False,
)
SESSION.mount("https://", HTTPAdapter(max_retries=retries))
SESSION.mount("http://", HTTPAdapter(max_retries=retries))
SESSION.headers.update(DEFAULT_HEADERS)

def safe_soup_get(attr_getter, default=None):
    try:
        return attr_getter()
    except Exception:
        return default

def get_soup_from_post(url: str, data: Dict[str, Any]) -> Optional[BeautifulSoup]:
    time.sleep(REQUEST_PAUSE)
    try:
        r = SESSION.post(url, data=data, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return BeautifulSoup(r.content, "html.parser")
    except Exception as e:
        log.warning("POST %s hatası: %s", url, e)
        return None

def get_soup_from_get(url: str) -> Optional[BeautifulSoup]:
    time.sleep(REQUEST_PAUSE)
    try:
        r = SESSION.get(url, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return BeautifulSoup(r.content, "html.parser")
    except Exception as e:
        log.warning("GET %s hatası: %s", url, e)
        return None

def build_candidate_stream_urls(reference_id: str) -> List[str]:
    # .m3u8 eklemiyoruz; endpoint genelde redirect ediyor.
    return [
        f"{STREAM_BASE}?PublisherId={pid}&ReferenceId={reference_id}&SecretKey={SECRET_KEY}"
        for pid in PUBLISHER_IDS
    ]

def extract_img_url(img_tag) -> str:
    """Poster <img> tag'inden en iyi görsel URL'sini seç (data-src > srcset > src)."""
    if not img_tag:
        return ""
    data_src = img_tag.get("data-src") or img_tag.get("data-original") or img_tag.get("data-lazy-src")
    if data_src:
        return data_src.strip()
    srcset = img_tag.get("srcset")
    if srcset:
        parts = [p.strip().split(" ")[0] for p in srcset.split(",") if p.strip()]
        if parts:
            return parts[-1]
    return (img_tag.get("src") or "").strip()

def get_single_program_page(page: int = 0) -> List[Dict[str, str]]:
    """
    Keşfet / A-Z sayfasından program adı, sayfa URL'si ve POSTER görselini alır.
    """
    all_programs: List[Dict[str, str]] = []
    data = {"type": "discover", "slug": "a-z", "page": page}
    soup = get_soup_from_post(AJAX_URL, data=data)
    if not soup:
        return all_programs

    programs = soup.find_all("div", {"class": "poster"})
    for program in programs:
        a = program.find("a")
        img_tag = program.find("img")

        program_url_rel = a.get("href") if a else ""
        program_url = urljoin(BASE_URL, program_url_rel)

        # Poster: keşfet/a-z'deki poster (lazy-load destekli)
        poster_rel = extract_img_url(img_tag)
        program_img = urljoin(BASE_URL, poster_rel)

        # Ad: onclick > alt > text
        onclick_name = a.get("onclick") if a else None
        if onclick_name and "GAEventTracker" in onclick_name:
            program_name = (
                onclick_name.replace("GAEventTracker('DISCOVER_PAGE_EVENTS', 'POSTER_CLICKED', '", "")
                            .replace("');", "")
                            .strip()
            )
        else:
            program_name = (
                (img_tag.get("alt").strip() if img_tag and img_tag.get("alt") else None)
                or (a.get_text(strip=True) if a else None)
                or "İsimsiz Program"
            )

        all_programs.append({"img": program_img, "url": program_url, "name": program_name})
    return all_programs

def get_all_programs(max_empty_pages: int = 2) -> List[Dict[str, str]]:
    all_programs: List[Dict[str, str]] = []
    empty_seen = 0
    page = 0
    while True:
        page_programs = get_single_program_page(page)
        if not page_programs:
            empty_seen += 1
            log.info("Boş/hatali sayfa: %d (ardışık=%d)", page, empty_seen)
            if empty_seen >= max_empty_pages:
                log.info("Toplam sayfa: %d", page)
                break
        else:
            empty_seen = 0
            all_programs.extend(page_programs)
        page += 1
    return all_programs

def get_program_id(url: str) -> Tuple[str, List[str]]:
    season_list: List[str] = []
    soup = get_soup_from_get(url)
    if not soup:
        return "0", season_list
    dyn_link = soup.find("a", {"class": "dyn-link"})
    program_id = safe_soup_get(lambda: dyn_link.get("data-program-id"), "0")
    season_selector = soup.find("select", {"class": "custom-dropdown"})
    if season_selector:
        for opt in season_selector.find_all("option"):
            val = safe_soup_get(lambda: opt.get("value"), None)
            if val and val not in season_list:
                season_list.append(val)
    return program_id, season_list

def parse_episodes_page(program_id: str, page: int, season: str, serie_name: str) -> List[Dict[str, str]]:
    all_episodes: List[Dict[str, str]] = []
    data = {"type": "episodes", "program_id": program_id, "page": page, "season": season}
    soup = get_soup_from_post(AJAX_URL, data=data)
    if not soup:
        return all_episodes
    items = soup.find_all("div", {"class": "item"})
    for it in items:
        strong = it.find("strong")
        img_tag = it.find("img")
        a = it.find("a")
        ep_title = safe_soup_get(lambda: strong.get_text().strip(), "Bölüm")
        name = f"{serie_name} - {ep_title}"
        img = safe_soup_get(lambda: img_tag.get("src"), "")
        url = safe_soup_get(lambda: a.get("href"), "")
        if url:
            all_episodes.append({"name": name, "img": img, "url": url})
    return all_episodes

def get_episodes_by_program_id(program_id: str, season_list: List[str], serie_name: str) -> List[Dict[str, str]]:
    all_episodes: List[Dict[str, str]] = []
    for season in tqdm(season_list, desc="Sezonlar", leave=False):
        page = 0
        empty_count = 0
        while True:
            page_eps = parse_episodes_page(program_id, page, season, serie_name)
            if not page_eps:
                empty_count += 1
                if empty_count >= 2:
                    break
            else:
                empty_count = 0
                all_episodes.extend(page_eps)
            page += 1
    return all_episodes

def get_stream_urls(episode_url: str) -> List[str]:
    soup = get_soup_from_get(episode_url)
    if not soup:
        return []
    player_div = soup.find("div", {"class": "video-player"})
    reference_id = safe_soup_get(lambda: player_div.get("data-video-code"), None)
    if not reference_id:
        return []
    return build_candidate_stream_urls(reference_id)

def run(start: int = 0, end: int = 0) -> Dict[str, Any]:
    output: List[Dict[str, Any]] = []
    programs_list = get_all_programs()
    if not programs_list:
        log.warning("Hiç program bulunamadı.")
        return {"programs": []}

    end_index = len(programs_list) if end == 0 else min(end, len(programs_list))
    start_index = max(0, start)

    for i in tqdm(range(start_index, end_index), desc="Programlar"):
        program = programs_list[i]
        log.info("%d | %s", i, program.get("name", ""))

        program_id, season_list = get_program_id(program["url"])
        if program_id == "0":
            log.warning("Program ID alınamadı: %s", program.get("name"))
            continue

        episodes = get_episodes_by_program_id(program_id, season_list, program["name"])
        if not episodes:
            continue

        temp_program = dict(program)
        temp_program["episodes"] = []

        for ep in tqdm(episodes, desc="Bölümler", leave=False):
            temp_episode = dict(ep)
            stream_candidates = get_stream_urls(ep["url"])
            if stream_candidates:
                temp_episode["stream_url"] = stream_candidates[0]
                temp_episode["stream_url_candidates"] = stream_candidates
                temp_program["episodes"].append(temp_episode)

        if temp_program["episodes"]:
            output.append(temp_program)

    return {"programs": output}

def save_outputs_only_m3u(data: Dict[str, Any]) -> None:
    """
    JSON YAZMAZ. Sadece M3U dosyaları üretir:
      - ./all.m3u
      - ./programlar/<dizi-adi>.m3u
      - (SERIES_MASTER=True ise) ./programlar/0.m3u
    """
    programs = data.get("programs", [])
    try:
        create_single_m3u(ALL_M3U_DIR, programs, ALL_M3U_NAME)
        create_m3us(SERIES_M3U_DIR, programs, master=SERIES_MASTER)
        log.info("M3U dosyaları oluşturuldu.")
    except Exception as e:
        log.error("M3U oluşturma hatası: %s", e)

def parse_args(argv: List[str]) -> Tuple[int, int]:
    # Kullanım:
    #   python dmax_scraper.py
    #   python dmax_scraper.py 10
    #   python dmax_scraper.py 10 50
    start, end = 0, 0
    if len(argv) >= 2:
        try:
            start = int(argv[1])
        except Exception:
            pass
    if len(argv) >= 3:
        try:
            end = int(argv[2])
        except Exception:
            pass
    return start, end

def main():
    start, end = parse_args(sys.argv)
    data = run(start=start, end=end)
    save_outputs_only_m3u(data)

if __name__ == "__main__":
    main()

import requests
import json
import re
import concurrent.futures
import time
from urllib.parse import urljoin

# ==================== AYARLAR ====================
# GitHub'daki kaynak kod adresi (Güncel Key ve Domain buradan çekilir)
GITHUB_SOURCE_URL = 'https://raw.githubusercontent.com/nikyokki/nik-cloudstream/refs/heads/master/RecTV/src/main/kotlin/com/keyiflerolsun/RecTV.kt'

TIMEOUT = 20
MAX_WORKERS = 15  # Paralel işlem hızı
CATEGORI_ID = "23" # Yerli Diziler

class RecTVScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Dart/3.7 (dart:io)',
            'Accept-Encoding': 'gzip'
        }
        self.main_url = "https://a.prectv70.lol" # Varsayılan
        self.sw_key = ""
        self.all_entries = []

    def log(self, message):
        print(f"[{time.strftime('%H:%M:%S')}] {message}")

    def fetch_github_config(self):
        """GitHub'dan güncel Key ve URL bilgilerini otomatik çeker"""
        self.log("GitHub'dan yapılandırma çekiliyor...")
        try:
            r = requests.get(GITHUB_SOURCE_URL, timeout=10)
            if r.status_code == 200:
                content = r.text
                # Ana URL'yi bul
                m_url = re.search(r'override\s+var\s+mainUrl\s*=\s*"([^"]+)"', content)
                if m_url: self.main_url = m_url.group(1).replace("m.", "a.") # API için 'a.' kullanıyoruz
                
                # SwKey'i bul
                s_key = re.search(r'private\s+(val|var)\s+swKey\s*=\s*"([^"]+)"', content)
                if s_key: self.sw_key = s_key.group(2)
                
                self.log(f"Yapılandırma Güncellendi: {self.main_url}")
                return True
        except Exception as e:
            self.log(f"GitHub hatası: {e}")
        return False

    def fetch_episode_details(self, serie_item):
        """Dizi detayına girer ve seri m3u formatında linkleri toplar"""
        serie_id = serie_item.get('id')
        title = serie_item.get('title', 'Dizi')
        image = serie_item.get('image', '')
            
        url = f"{self.main_url}/api/season/by/serie/{serie_id}/{self.sw_key}"
        try:
            r = requests.get(url, headers=self.headers, timeout=TIMEOUT, verify=False)
            if r.status_code != 200: return
            seasons = r.json()
            
            for season in seasons:
                s_name = season.get('title', 'Sezon')
                for ep in season.get('episodes', []):
                    ep_name = ep.get('title', 'Bolum')
                    for source in ep.get('sources', []):
                        src_url = source.get('url')
                        if src_url:
                            quality = source.get('quality', 'HD').upper()
                            full_title = f"{title} - {s_name} - {ep_name} [{quality}]"
                            
                            # İSTEDİĞİN TEMİZ SERİ YAPI (Referer satırları kaldırıldı)
                            entry = (
                                f'#EXTINF:-1 group-title="Yerli Diziler" tvg-logo="{image}",{full_title}\n'
                                f'{src_url}'
                            )
                            self.all_entries.append(entry)
        except:
            pass

    def run(self):
        # 1. Güncel bilgileri al
        self.fetch_github_config()

        page = 0
        while page < 20: # İlk 20 sayfayı tara
            url = f"{self.main_url}/api/serie/by/filtres/{CATEGORI_ID}/created/{page}/{self.sw_key}"
            self.log(f"Sayfa {page} taranıyor...")
            
            try:
                r = requests.get(url, headers=self.headers, timeout=TIMEOUT, verify=False)
                series_list = r.json()
                if not series_list: break

                with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    executor.map(self.fetch_episode_details, series_list)
                
                page += 1
            except:
                break

        # --- DOSYALARI İKİYE BÖLME ---
        total = len(self.all_entries)
        if total > 0:
            self.all_entries.sort() # Alfabetik sırala
            mid = total // 2
            
            with open("diziler_1.m3u", "w", encoding="utf-8") as f1:
                f1.write("#EXTM3U\n" + "\n".join(self.all_entries[:mid]))
            
            with open("diziler_2.m3u", "w", encoding="utf-8") as f2:
                f2.write("#EXTM3U\n" + "\n".join(self.all_entries[mid:]))
                
            self.log(f"BAŞARILI: {total} link toplandı ve 2 dosyaya bölündü.")
        else:
            self.log("HATA: Hiç link bulunamadı.")

if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings()
    scraper = RecTVScraper()
    scraper.run()

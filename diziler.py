import requests
import json
import re
import concurrent.futures
import time
from urllib.parse import urljoin

# ==================== AYARLAR ====================
TIMEOUT = 15
MAX_WORKERS = 5 
FILE_SERIES = 'yerli_diziler_tum_kaliteler.m3u'

class RecTVScraper:
    def __init__(self):
        # User-Agent bilgisini güncelledim (0 link hatasını önlemek için kritik)
        self.headers = {
            'User-Agent': 'Dart/3.7 (dart:io)',
            'Accept-Encoding': 'gzip',
            'Connection': 'Keep-Alive'
        }
        # Güncel olması muhtemel domain (Eğer 0 gelirse 70, 71, 72 deneyebilirsin)
        self.main_url = "https://m.prectv70.lol" 
        # Bu key değişmiş olabilir, son paylaştığın linkteki keyi buraya koydum
        self.sw_key = "4F5A9C3D9A86FA54EACEDDD635185/c3c5bd17-e37b-4b94-a944-8a3688a30452"
        self.series_buffer = ["#EXTM3U"]
        self.total_links = 0

    def log(self, message):
        print(f"[{time.strftime('%H:%M:%S')}] {message}")

    def fetch_episode_details(self, serie_item):
        serie_id = serie_item.get('id')
        title = serie_item.get('title', 'Bilinmeyen')
        image = serie_item.get('image', '')
        
        local_entries = []
        # Sezon ve bölüm linklerini çeken API
        url = f"{self.main_url}/api/season/by/serie/{serie_id}/{self.sw_key}"
        
        try:
            r = requests.get(url, headers=self.headers, timeout=TIMEOUT, verify=False)
            if r.status_code != 200: return []
            seasons = r.json()
            
            for season in seasons:
                season_name = season.get('title', 'Sezon')
                for ep in season.get('episodes', []):
                    ep_title = ep.get('title', 'Bölüm')
                    for source in ep.get('sources', []):
                        src_url = source.get('url')
                        quality = source.get('quality', 'HD').upper()
                        if src_url:
                            full_title = f"{title} - {season_name} - {ep_title} [{quality}]"
                            entry = (
                                f'#EXTINF:-1 tvg-logo="{image}" group-title="Yerli Diziler", {full_title}\n'
                                f'{src_url}'
                            )
                            local_entries.append(entry)
        except: return []
        return local_entries

    def run(self):
        self.log(f"Tarama başlıyor: {self.main_url}")
        page = 0
        
        # Sadece Yerli Dizi Kategorisi (id: 23)
        while True:
            url = f"{self.main_url}/api/serie/by/filtres/23/created/{page}/{self.sw_key}"
            try:
                r = requests.get(url, headers=self.headers, timeout=TIMEOUT, verify=False)
                
                if r.status_code != 200:
                    self.log(f"Hata: Sunucu {r.status_code} hatası verdi. Sayfa: {page}")
                    break
                
                series_list = r.json()
                if not series_list or len(series_list) == 0:
                    self.log("Dizi listesi boş geldi, işlem sonlandırılıyor.")
                    break

                with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    futures = [executor.submit(self.fetch_episode_details, s) for s in series_list]
                    for future in concurrent.futures.as_completed(futures):
                        res = future.result()
                        if res:
                            self.series_buffer.extend(res)
                            self.total_links += len(res)

                self.log(f"Sayfa {page} bitti. Toplam Link: {self.total_links}")
                page += 1
                if page > 5: break # Test amaçlı ilk 5 sayfada durdurabilirsin
                
            except Exception as e:
                self.log(f"Bağlantı Hatası: {e}")
                break

        with open(FILE_SERIES, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.series_buffer))
        self.log(f"BİTTİ! Dosya: {FILE_SERIES}")

if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings()
    scraper = RecTVScraper()
    scraper.run()

import requests
import json
import re
import concurrent.futures
import time
from urllib.parse import urljoin

# ==================== AYARLAR ====================
TIMEOUT = 20
MAX_WORKERS = 10 
FILE_SERIES = 'yerli_diziler_guncel.m3u'

class RecTVScraper:
    def __init__(self):
        # Kotlin dosyasındaki güncel Header yapısı
        self.headers = {
            'User-Agent': 'Dart/3.7 (dart:io)',
            'Referer': 'https://twitter.com/'
        }
        # Kotlin dosyasındaki en güncel bilgiler
        self.main_url = "https://m.prectv50.sbs" 
        self.sw_key = "4F5A9C3D9A86FA54EACEDDD635185/64f9535b-bd2e-4483-b234-89060b1e631c"
        
        self.series_buffer = ["#EXTM3U"]
        self.total_links = 0

    def log(self, message):
        print(f"[{time.strftime('%H:%M:%S')}] {message}")

    def fetch_episode_details(self, serie_item):
        """Detayları çeker: Sadece Yerli (23) olanların TÜM kaynaklarını alır"""
        
        # Yerli Filtresi (id: 23 genelde yerli dizilerdir)
        genres = serie_item.get('genres', [])
        is_yerli = any(genre.get('id') == 23 for genre in genres)
        
        # Eğer türler içinde 23 yoksa ama başlıkta "Yerli" geçiyorsa yine de alalım (Garantici yöntem)
        if not is_yerli and "yerli" not in serie_item.get('title', '').lower():
            return []

        serie_id = serie_item.get('id')
        title = serie_item.get('title', 'Bilinmeyen')
        image = serie_item.get('image', '')
        
        local_entries = []
        # Kotlin kodundaki detay çekme URL yapısı
        url = f"{self.main_url}/api/season/by/serie/{serie_id}/{self.sw_key}"
        
        try:
            r = requests.get(url, headers=self.headers, timeout=TIMEOUT, verify=False)
            if r.status_code != 200: return []
            seasons = r.json()
            
            if not seasons or not isinstance(seasons, list): return []

            for season in seasons:
                season_name = season.get('title', 'Sezon')
                episodes = season.get('episodes', [])
                
                for ep in episodes:
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
        except:
            return []
            
        return local_entries

    def run(self):
        self.log(f"Güncel bilgilerle tarama başlıyor: {self.main_url}")
        page = 0
        
        while True:
            # API URL: Yerli kategorisi (23) için istek atıyoruz
            url = f"{self.main_url}/api/serie/by/filtres/23/created/{page}/{self.sw_key}"
            
            try:
                r = requests.get(url, headers=self.headers, timeout=TIMEOUT, verify=False)
                
                if r.status_code != 200:
                    self.log(f"Sayfa {page} alınamadı (Kod: {r.status_code}). Bitiyor olabilir.")
                    break
                
                series_list = r.json()
                if not series_list:
                    self.log("İçerik bitti.")
                    break

                with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    futures = [executor.submit(self.fetch_episode_details, s) for s in series_list]
                    for future in concurrent.futures.as_completed(futures):
                        res = future.result()
                        if res:
                            self.series_buffer.extend(res)
                            self.total_links += len(res)

                self.log(f"Sayfa {page} tamamlandı. Eklenen Link: {self.total_links}")
                page += 1
                
            except Exception as e:
                self.log(f"Hata oluştu: {e}")
                break

        # Dosyayı yazdır
        if self.total_links > 0:
            with open(FILE_SERIES, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.series_buffer))
            self.log(f"İŞLEM BAŞARILI! {self.total_links} link '{FILE_SERIES}' dosyasına kaydedildi.")
        else:
            self.log("HATA: Hiç link bulunamadı. Lütfen internetini ve site adresini kontrol et.")

if __name__ == "__main__":
    # SSL uyarılarını kapat (Hız ve sorunsuz bağlantı için)
    requests.packages.urllib3.disable_warnings()
    scraper = RecTVScraper()
    scraper.run()

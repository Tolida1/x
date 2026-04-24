import requests
import json
import re
import concurrent.futures
import time
from urllib.parse import urljoin

# ==================== AYARLAR ====================
GITHUB_SOURCE_URL = 'https://raw.githubusercontent.com/nikyokki/nik-cloudstream/refs/heads/master/RecTV/src/main/kotlin/com/keyiflerolsun/RecTV.kt'
PROXY_URL = 'https://api.codetabs.com/v1/proxy/?quest=' + requests.utils.quote(GITHUB_SOURCE_URL)

# Sabitler
TIMEOUT = 20
MAX_WORKERS = 10 
FILE_SERIES = 'yerli_diziler_tum_kaliteler.m3u'

class RecTVScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'okhttp/4.12.0',
            'Referer': 'https://twitter.com/'
        }
        self.main_url = "https://m.prectv60.lol" 
        self.sw_key = ""
        self.series_buffer = ["#EXTM3U"]
        self.total_links = 0

    def log(self, message):
        print(f"[{time.strftime('%H:%M:%S')}] {message}")

    def fetch_github_config(self):
        """GitHub'dan güncel Key ve URL bilgilerini çeker"""
        self.log("Yapılandırma güncelleniyor...")
        content = None
        try:
            r = requests.get(GITHUB_SOURCE_URL, timeout=10)
            if r.status_code == 200: content = r.text
        except: pass
        
        if not content:
            try:
                r = requests.get(PROXY_URL, timeout=10)
                if r.status_code == 200: content = r.text
            except: pass

        if content:
            m_url = re.search(r'override\s+var\s+mainUrl\s*=\s*"([^"]+)"', content)
            if m_url: self.main_url = m_url.group(1)
            
            s_key = re.search(r'private\s+(val|var)\s+swKey\s*=\s*"([^"]+)"', content)
            if s_key: self.sw_key = s_key.group(2)
            
            ua = re.search(r'headers\s*=\s*mapOf\([^)]*"user-agent"[^)]*to[^"]*"([^"]+)"', content, re.IGNORECASE)
            if ua: self.headers['User-Agent'] = ua.group(1)

            self.log(f"Config Hazır: {self.main_url}")
            return True
        return False

    def find_working_domain(self):
        """Domain testi"""
        if self.test_domain(self.main_url): return
        for i in range(70, 50, -1):
            domain = f"https://m.prectv{i}.lol"
            if self.test_domain(domain):
                self.main_url = domain
                break

    def test_domain(self, url):
        try:
            test_url = f"{url}/api/serie/by/filtres/23/created/0/{self.sw_key}"
            r = requests.get(test_url, headers=self.headers, timeout=5, verify=False)
            return r.status_code == 200
        except: return False

    def fetch_episode_details(self, serie_item):
        """Detayları çeker: Yerli (23) olanların TÜM kaynaklarını/kalitelerini alır"""
        
        # 1. Yerli Filtresi
        genres = serie_item.get('genres', [])
        is_yerli = any(genre.get('id') == 23 for genre in genres)
        if not is_yerli: return []

        serie_id = serie_item.get('id')
        title = serie_item.get('title', 'Bilinmeyen')
        image = serie_item.get('image', '')
        if image and not image.startswith('http'):
            image = urljoin(self.main_url, image)
            
        local_entries = []
        url = f"{self.main_url}/api/season/by/serie/{serie_id}/{self.sw_key}"
        
        try:
            r = requests.get(url, headers=self.headers, timeout=TIMEOUT, verify=False)
            if r.status_code != 200: return []
            seasons = r.json()
        except: return []

        if not seasons or not isinstance(seasons, list): return []

        for season in seasons:
            season_name = season.get('title', 'Sezon')
            episodes = season.get('episodes', [])
            
            for ep in episodes:
                ep_title = ep.get('title', 'Bölüm')
                
                # TÜM KAYNAKLARI (SD, HD, FHD) DÖNGÜYE ALIYORUZ
                for source in ep.get('sources', []):
                    src_url = source.get('url')
                    quality = source.get('quality', 'Dinamik').upper()
                    
                    if src_url:
                        # Başlığa kaliteyi ekliyoruz (Örn: Dizi Adı - 1. Sezon - 1. Bölüm [FHD])
                        full_title = f"{title} - {season_name} - {ep_title} [{quality}]"

                        entry = (
                            f'#EXTINF:-1 tvg-id="{serie_id}" tvg-name="{full_title}" tvg-logo="{image}" group-title="Yerli Diziler", {full_title}\n'
                            f'#EXTVLCOPT:http-user-agent={self.headers["User-Agent"]}\n'
                            f'#EXTVLCOPT:http-referrer={self.headers["Referer"]}\n'
                            f'{src_url}'
                        )
                        local_entries.append(entry)
        
        return local_entries

    def run(self):
        if not self.fetch_github_config(): self.log("Hata: Config!")
        self.find_working_domain()

        self.log("Tüm kalitelerle yerli dizi taraması başladı...")
        page = 0
        while True:
            url = f"{self.main_url}/api/serie/by/filtres/23/created/{page}/{self.sw_key}"
            try:
                r = requests.get(url, headers=self.headers, timeout=TIMEOUT, verify=False)
                series_list = r.json()
                if not series_list: break

                with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    futures = [executor.submit(self.fetch_episode_details, s) for s in series_list]
                    for future in concurrent.futures.as_completed(futures):
                        res = future.result()
                        if res:
                            self.series_buffer.extend(res)
                            self.total_links += len(res)

                self.log(f"Sayfa {page} bitti. Toplam Link: {self.total_links}")
                page += 1
            except: break

        with open(FILE_SERIES, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.series_buffer))
        
        self.log(f"BİTTİ! {self.total_links} adet link '{FILE_SERIES}' dosyasına yazıldı.")

if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings()
    scraper = RecTVScraper()
    scraper.run()

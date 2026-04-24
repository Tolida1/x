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
FILE_SERIES = 'yerli_diziler.m3u'

class RecTVScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'okhttp/4.12.0',
            'Referer': 'https://twitter.com/'
        }
        self.main_url = "https://m.prectv60.lol" 
        self.sw_key = ""
        self.series_buffer = ["#EXTM3U"]
        self.total_episodes = 0

    def log(self, message):
        print(f"[{time.strftime('%H:%M:%S')}] {message}")

    def fetch_github_config(self):
        """GitHub'dan güncel Key ve URL bilgilerini çeker"""
        self.log("GitHub'dan yapılandırma çekiliyor...")
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

            ref = re.search(r'headers\s*=\s*mapOf\([^)]*"Referer"[^)]*to[^"]*"([^"]+)"', content, re.IGNORECASE)
            if ref: self.headers['Referer'] = ref.group(1)
            
            self.log(f"Config Güncellendi: URL={self.main_url}")
            return True
        return False

    def find_working_domain(self):
        """Çalışan domaini test eder"""
        if self.test_domain(self.main_url):
            return

        self.log("Domain kontrol ediliyor...")
        for i in range(75, 50, -1):
            domain = f"https://m.prectv{i}.lol"
            if self.test_domain(domain):
                self.main_url = domain
                self.log(f"Çalışan domain: {domain}")
                return

    def test_domain(self, url):
        try:
            test_url = f"{url}/api/serie/by/filtres/23/created/0/{self.sw_key}"
            r = requests.get(test_url, headers=self.headers, timeout=5, verify=False)
            return r.status_code == 200
        except:
            return False

    def fetch_episode_details(self, serie_item):
        """Detayları çeker ve sadece Yerli (id:23) olanları işler"""
        
        # --- Yerli Filtresi ---
        genres = serie_item.get('genres', [])
        is_yerli = any(genre.get('id') == 23 for genre in genres)
        
        if not is_yerli:
            return []
        # ---------------------

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
        except:
            return []

        if not seasons or not isinstance(seasons, list): return []

        for season in seasons:
            season_name = season.get('title', 'Sezon')
            episodes = season.get('episodes', [])
            
            for ep in episodes:
                ep_title = ep.get('title', 'Bölüm')
                for source in ep.get('sources', []):
                    src_url = source.get('url')
                    if src_url and ("m3u8" in src_url or "mp4" in src_url):
                        full_title = f"{title} - {season_name} - {ep_title}"
                        quality = source.get('quality', '')
                        if quality: full_title += f" [{quality}]"

                        entry = (
                            f'#EXTINF:-1 tvg-id="{serie_id}" tvg-name="{full_title}" tvg-logo="{image}" group-title="Yerli Diziler", {full_title}\n'
                            f'#EXTVLCOPT:http-user-agent={self.headers["User-Agent"]}\n'
                            f'#EXTVLCOPT:http-referrer={self.headers["Referer"]}\n'
                            f'{src_url}'
                        )
                        local_entries.append(entry)
        
        return local_entries

    def run(self):
        if not self.fetch_github_config():
            self.log("HATA: Config alınamadı!")
        self.find_working_domain()

        self.log("Yerli dizi taraması başlıyor...")
        page = 0
        empty_streak = 0

        while True:
            # 23 ID'si Yerli Dizi filtresidir
            url = f"{self.main_url}/api/serie/by/filtres/23/created/{page}/{self.sw_key}"
            self.log(f"Sayfa {page} taranıyor...")
            
            try:
                r = requests.get(url, headers=self.headers, timeout=TIMEOUT, verify=False)
                if r.status_code != 200: break
                
                series_list = r.json()
                if not series_list:
                    empty_streak += 1
                    if empty_streak >= 2: break
                    page += 1
                    continue
                else:
                    empty_streak = 0

                with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    futures = [executor.submit(self.fetch_episode_details, s) for s in series_list]
                    for future in concurrent.futures.as_completed(futures):
                        res = future.result()
                        if res:
                            self.series_buffer.extend(res)
                            self.total_episodes += len(res)

                self.log(f"Sayfa {page} bitti. Toplam Yerli Bölüm: {self.total_episodes}")
                page += 1
                
            except Exception as e:
                self.log(f"Hata: {e}")
                break

        with open(FILE_SERIES, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.series_buffer))
        
        self.log(f"TAMAMLANDI! {self.total_episodes} bölüm '{FILE_SERIES}' dosyasına kaydedildi.")

if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings()
    scraper = RecTVScraper()
    scraper.run()

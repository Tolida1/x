import requests
import json
import time
import concurrent.futures

# ==================== AYARLAR ====================
DOMAIN = "https://a.prectv70.lol"
# Senin paylaştığın en güncel anahtar
SW_KEY = "4F5A9C3D9A86FA54EACEDDD635185/c3c5bd17-e37b-4b94-a944-8a3688a30452"
CATEGORI_ID = "23" # Yerli Dizi / Film
FILE_NAME = "yerli_dizi_arsivi.m3u"

HEADERS = {
    'User-Agent': 'Dart/3.7 (dart:io)',
    'Accept-Encoding': 'gzip'
}

class RecTVPro:
    def __init__(self):
        self.buffer = ["#EXTM3U"]
        self.counter = 0

    def get_links(self, serie):
        """Her dizinin içine girip bölümleri toplar"""
        s_id = serie.get('id')
        s_title = serie.get('title')
        s_image = serie.get('image')
        
        # Detay API linkini oluşturuyoruz
        detail_url = f"{DOMAIN}/api/season/by/serie/{s_id}/{SW_KEY}"
        
        try:
            r = requests.get(detail_url, headers=HEADERS, timeout=15, verify=False)
            if r.status_code != 200: return
            
            seasons = r.json()
            for season in seasons:
                s_name = season.get('title', 'Sezon')
                for episode in season.get('episodes', []):
                    e_title = episode.get('title', 'Bölüm')
                    for source in episode.get('sources', []):
                        url = source.get('url')
                        quality = source.get('quality', 'HD')
                        
                        if url:
                            full_name = f"{s_title} - {s_name} - {e_title} [{quality}]"
                            entry = (
                                f'#EXTINF:-1 tvg-logo="{s_image}" group-title="Yerli Diziler", {full_name}\n'
                                f'{url}'
                            )
                            self.buffer.append(entry)
                            self.counter += 1
        except:
            pass

    def run(self):
        print(f"[*] Tarama Başlıyor: {DOMAIN}")
        page = 0
        
        while True:
            # Liste API linki
            list_url = f"{DOMAIN}/api/serie/by/filtres/{CATEGORI_ID}/created/{page}/{SW_KEY}"
            print(f"[>] Sayfa {page} taranıyor...")
            
            try:
                r = requests.get(list_url, headers=HEADERS, timeout=15, verify=False)
                series = r.json()
                
                if not series or len(series) == 0:
                    break
                
                # Dizileri paralel işle (Hız için)
                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                    executor.map(self.get_links, series)
                
                print(f"[+] Şu ana kadar {self.counter} link toplandı.")
                page += 1
                
            except Exception as e:
                print(f"[!] Hata: {e}")
                break

        # Dosyaya Yaz
        with open(FILE_NAME, "w", encoding="utf-8") as f:
            f.write("\n".join(self.buffer))
        print(f"\n[OK] İşlem bitti! {self.counter} link '{FILE_NAME}' dosyasına kaydedildi.")

if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings()
    app = RecTVPro()
    app.run()

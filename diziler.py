import requests
import json
import time
import concurrent.futures

# ==================== YAPILANDIRMA ====================
DOMAIN = "https://a.prectv70.lol"
# Senin verdiğin güncel swKey
SW_KEY = "4F5A9C3D9A86FA54EACEDDD635185/c3c5bd17-e37b-4b94-a944-8a3688a30452"
CATEGORI_ID = "23"  # Yerli Diziler
FILE_NAME = "diziler.m3u" # YAML dosyanla aynı isim olmalı

HEADERS = {
    'User-Agent': 'Dart/3.7 (dart:io)',
    'Accept-Encoding': 'gzip'
}

class RecTVCrawler:
    def __init__(self):
        self.m3u_list = ["#EXTM3U"]
        self.found_count = 0

    def fetch_details(self, serie):
        """Her bir dizi ID'si için Sezon/Bölüm API'sine gider"""
        serie_id = serie.get('id')
        serie_title = serie.get('title', 'Bilinmeyen Dizi')
        serie_img = serie.get('image', '')

        # Sezon detay linkini senin istediğin formatta oluşturuyoruz
        detail_url = f"{DOMAIN}/api/season/by/serie/{serie_id}/{SW_KEY}"
        
        try:
            r = requests.get(detail_url, headers=HEADERS, timeout=15, verify=False)
            if r.status_code != 200:
                return

            seasons = r.json()
            for season in seasons:
                s_title = season.get('title', 'Sezon')
                for ep in season.get('episodes', []):
                    ep_title = ep.get('title', 'Bölüm')
                    for src in ep.get('sources', []):
                        video_url = src.get('url')
                        quality = src.get('quality', 'HD')

                        if video_url:
                            # M3U formatına uygun başlık ve link ekleme
                            display_name = f"{serie_title} - {s_title} - {ep_title} [{quality}]"
                            entry = (
                                f'#EXTINF:-1 tvg-logo="{serie_img}" group-title="Yerli Diziler", {display_name}\n'
                                f'{video_url}'
                            )
                            self.m3u_list.append(entry)
                            self.found_count += 1
        except Exception:
            pass

    def run(self):
        print(f"[*] İşlem Başlıyor... Domain: {DOMAIN}")
        page = 0
        
        while True:
            # Ana liste API'si (Buradan ID'leri alıyoruz)
            list_url = f"{DOMAIN}/api/serie/by/filtres/{CATEGORI_ID}/created/{page}/{SW_KEY}"
            
            try:
                response = requests.get(list_url, headers=HEADERS, timeout=15, verify=False)
                series_data = response.json()

                if not series_data or len(series_data) == 0:
                    print("[!] Sayfa boş, tarama bitti.")
                    break

                print(f"[>] Sayfa {page} işleniyor... ({len(series_data)} dizi bulundu)")

                # Her diziyi paralel olarak tara (Hız için 10 işçi)
                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                    executor.map(self.fetch_details, series_data)

                page += 1
                # GitHub Actions'da takılmaması için küçük bir sınır (Opsiyonel)
                if page > 20: break 

            except Exception as e:
                print(f"[!] Hata oluştu: {e}")
                break

        # Dosyaya Yazma
        if self.found_count > 0:
            with open(FILE_NAME, "w", encoding="utf-8") as f:
                f.write("\n".join(self.m3u_list))
            print(f"[*] BAŞARILI: {self.found_count} link '{FILE_NAME}' dosyasına yazıldı.")
        else:
            print("[!] HATA: Hiç link bulunamadı!")

if __name__ == "__main__":
    # SSL Sertifika hatalarını görmezden gel
    requests.packages.urllib3.disable_warnings()
    crawler = RecTVCrawler()
    crawler.run()

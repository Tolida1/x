import requests
import json
import time
import concurrent.futures

# ==================== YAPILANDIRMA ====================
DOMAIN = "https://a.prectv70.lol"
SW_KEY = "4F5A9C3D9A86FA54EACEDDD635185/c3c5bd17-e37b-4b94-a944-8a3688a30452"
CATEGORI_ID = "23" 
HEADERS = {
    'User-Agent': 'Dart/3.7 (dart:io)',
    'Accept-Encoding': 'gzip'
}

class RecTVCrawler:
    def __init__(self):
        self.all_entries = [] # Tüm linkleri burada toplayacağız

    def fetch_details(self, serie):
        """Dizi ID'sini kullanarak bölüm linklerini çeker"""
        serie_id = serie.get('id')
        serie_title = serie.get('title', 'Bilinmeyen')
        serie_img = serie.get('image', '')
        
        # Senin istediğin detay API yapısı
        detail_url = f"{DOMAIN}/api/season/by/serie/{serie_id}/{SW_KEY}"
        
        try:
            r = requests.get(detail_url, headers=HEADERS, timeout=15, verify=False)
            if r.status_code != 200: return
            
            seasons = r.json()
            for season in seasons:
                s_title = season.get('title', 'Sezon')
                for ep in season.get('episodes', []):
                    ep_name = ep.get('title', 'Bolum')
                    for src in ep.get('sources', []):
                        video_url = src.get('url')
                        quality = src.get('quality', 'HD')
                        
                        if video_url:
                            display_name = f"{serie_title} - {s_title} - {ep_name} [{quality}]"
                            entry = (
                                f'#EXTINF:-1 tvg-logo="{serie_img}" group-title="Yerli Diziler", {display_name}\n'
                                f'{video_url}'
                            )
                            self.all_entries.append(entry)
        except:
            pass

    def run(self):
        print(f"[*] İşlem Başlıyor: {DOMAIN}")
        page = 0
        
        # İlk 20 sayfadaki dizileri tarar (Gerekiyorsa artırabilirsin)
        while page < 20:
            list_url = f"{DOMAIN}/api/serie/by/filtres/{CATEGORI_ID}/created/{page}/{SW_KEY}"
            print(f"[>] Sayfa {page} taranıyor...")
            
            try:
                r = requests.get(list_url, headers=HEADERS, timeout=15, verify=False)
                series_data = r.json()
                
                if not series_data or len(series_data) == 0:
                    break
                
                # Paralel tarama ile hızı 10 katına çıkarıyoruz
                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                    executor.map(self.fetch_details, series_data)
                
                page += 1
            except:
                break

        # --- DOSYALARI İKİYE BÖLME VE KAYDETME ---
        total = len(self.all_entries)
        if total > 0:
            # Alfabetik sırala (Daha düzenli liste için)
            self.all_entries.sort()
            
            mid = total // 2
            
            # 1. Dosyayı Yaz (diziler_1.m3u)
            with open("diziler_1.m3u", "w", encoding="utf-8") as f1:
                f1.write("#EXTM3U\n" + "\n".join(self.all_entries[:mid]))
            
            # 2. Dosyayı Yaz (diziler_2.m3u)
            with open("diziler_2.m3u", "w", encoding="utf-8") as f2:
                f2.write("#EXTM3U\n" + "\n".join(self.all_entries[mid:]))
                
            print(f"\n[OK] Toplam {total} link başarıyla çekildi.")
            print("[+] diziler_1.m3u ve diziler_2.m3u oluşturuldu.")
        else:
            print("[!] Hata: Hiç link toplanamadı!")

if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings()
    RecTVCrawler().run()

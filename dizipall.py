import asyncio
import re
from bs4 import BeautifulSoup
from curl_cffi import requests

# --- AYARLAR ---
MAIN_URL = "https://dizipal.bar" # Çalışmazsa güncel adresi buraya yazmalısın
MAX_PAGE = 1 

KATEGORILER = {
    "Aksiyon": f"{MAIN_URL}/kategori/aksiyon/page/",
    "Bilim Kurgu": f"{MAIN_URL}/kategori/bilim-kurgu/page/",
    "Komedi": f"{MAIN_URL}/kategori/komedi/page/"
}

HEADERS = {
    "Referer": f"{MAIN_URL}/"
}

async def fetch_html(client, url):
    """Gerçek bir Chrome tarayıcısı gibi davranarak sayfayı çeker."""
    try:
        resp = await client.get(url, headers=HEADERS, timeout=20.0)
        
        if resp.status_code == 200:
            return resp.text
        elif resp.status_code in [403, 503]:
            print(f"  [-] Cloudflare Korumasına Takıldık! (Hata: {resp.status_code})")
            return None
        else:
            print(f"  [-] Sunucu Hatası: {resp.status_code}")
            return None
            
    except Exception as e:
        print(f"  [-] Bağlantı Hatası: {e}")
    return None

async def extract_video_data(client, page_url):
    html = await fetch_html(client, page_url)
    if not html: return None

    soup = BeautifulSoup(html, "html.parser")
    iframe = soup.select_one("div.video-player-area iframe") or soup.select_one("div.responsive-player iframe")
    
    if not iframe or not iframe.get("src"):
        return None

    iframe_src = iframe.get("src")
    if iframe_src.startswith("//"):
        iframe_src = "https:" + iframe_src

    iframe_html = await fetch_html(client, iframe_src)
    if not iframe_html: return None

    m3u_match = re.search(r'file\s*:\s*["\']([^"\']+)["\']', iframe_html)
    sub_match = re.search(r'"subtitle"\s*:\s*["\']([^"\']+)["\']', iframe_html)

    if m3u_match:
        data = {"m3u8": m3u_match.group(1), "subtitles": []}
        if sub_match:
            sub_text = sub_match.group(1)
            for sub in sub_text.split(","):
                lang = re.search(r'\[(.*?)\]', sub)
                lang_code = lang.group(1) if lang else "TR"
                sub_url = re.sub(r'\[.*?\]', '', sub).strip()
                data["subtitles"].append(f"{lang_code}: {sub_url}")
        return data
    return None

async def process_item(client, item_url, item_title):
    results = []
    if "/dizi/" in item_url:
        print(f"  [DİZİ] Bölümler taranıyor: {item_title}")
        html = await fetch_html(client, item_url)
        if not html: return []
        
        soup = BeautifulSoup(html, "html.parser")
        episodes = soup.select("div.episode-item")
        
        for ep in episodes:
            a_tag = ep.select_one("a")
            if a_tag and a_tag.get("href"):
                ep_url = a_tag.get("href")
                ep_title = ep.select_one("h4").text.strip() if ep.select_one("h4") else "Bölüm"
                full_title = f"{item_title} - {ep_title}"
                
                print(f"    -> {full_title} çıkarılıyor...")
                video_data = await extract_video_data(client, ep_url)
                if video_data:
                    results.append({"title": full_title, "m3u8": video_data["m3u8"]})
                await asyncio.sleep(1) # Hız sınırı için bekleme süresini artırdık
                
    else:
        print(f"  [FİLM] Link çıkarılıyor: {item_title}")
        video_data = await extract_video_data(client, item_url)
        if video_data:
            results.append({"title": item_title, "m3u8": video_data["m3u8"]})
            
    return results

async def main():
    m3u_content = "#EXTM3U\n"
    total_links = 0
    
    # impersonate="chrome" kısmı bizi Cloudflare'den koruyan asıl kalkan
    async with requests.AsyncSession(impersonate="chrome") as client:
        for cat_name, cat_url in KATEGORILER.items():
            print(f"\n=============================")
            print(f"[*] KATEGORİ: {cat_name}")
            print(f"=============================")
            
            for page in range(1, MAX_PAGE + 1):
                url = f"{cat_url}{page}/"
                print(f"\n[*] Sayfa {page} taranıyor: {url}")
                
                html = await fetch_html(client, url)
                if not html: 
                    print("  [!] Sayfa kaynağı alınamadı, atlanıyor.")
                    continue
                
                soup = BeautifulSoup(html, "html.parser")
                items = soup.select("div.grid div.post-item")
                
                if not items:
                    print("  [!] Bu sayfada hiç içerik bulunamadı. Domain değişmiş veya koruma aktif olabilir.")
                
                for item in items:
                    a_tag = item.select_one("a")
                    if a_tag and a_tag.get("href"):
                        title = a_tag.get("title", "İsimsiz")
                        href = a_tag.get("href")
                        
                        videos = await process_item(client, href, title)
                        
                        for vid in videos:
                            m3u_content += f"#EXTINF:-1, {vid['title']}\n"
                            m3u_content += f"{vid['m3u8']}\n"
                            total_links += 1
                            
                        await asyncio.sleep(1)

    with open("dizipal_full.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)
        
    print(f"\n[✓] İŞLEM BİTTİ! Toplam {total_links} adet video linki dizipal_full.m3u dosyasına kaydedildi.")

if __name__ == "__main__":
    asyncio.run(main())

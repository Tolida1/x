import requests

def download_m3u():
    url = "https://uc0918e4d42505e97508ad1cf6a1.dl.dropboxusercontent.com/cd/0/get/C_N5Qd5Ml9JIsKvL9n09PovrcWgUh7swH-YzyePGaKKl6HdGKYi3fTtGxfv1wpcegaqpBwOajjzG7gWKKy5c95XReJJiGkvr7wFJC-u72ax27r4Xgdnp0E5UFOC9UgttmMqubQLobb5jiUIz-W-lUsza/file?dl=1"
    
    # Paylaştığın tüm header bilgilerini buraya ekledik
    headers = {
        "User-Agent": "Mozilla/5.0 (Android)",
        "If-None-Match": "1767621424276840d",
        "Host": "uc0918e4d42505e97508ad1cf6a1.dl.dropboxusercontent.com",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip"
    }

    try:
        print("Özel header bilgileriyle istek gönderiliyor...")
        # Stream=True kullanarak ve headers ekleyerek isteği yapıyoruz
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        
        # 304 Not Modified dönerse dosya değişmemiştir, 200 dönerse yeni dosyayı indirir
        if response.status_code == 304:
            print("Dosya değişmemiş (304 Not Modified).")
            return
            
        response.raise_for_status()
        
        with open("tv.m3u", "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print("tv.m3u başarıyla güncellendi.")

    except Exception as e:
        print(f"Hata oluştu: {e}")
        # Hata durumunda Action'ın durması için exit kodunu kullanabilirsin
        # exit(1) 

if __name__ == "__main__":
    download_m3u()

import requests

URL = "https://m3u.work/VYaQo6he.m3u"

def get_m3u():
    r = requests.get(URL, timeout=30)
    r.raise_for_status()
    return r.text.splitlines()

lines = [l for l in get_m3u() if l.strip()]

half = len(lines) // 2

part1 = lines[:half]
part2 = lines[half:]

with open("1.m3u", "w", encoding="utf-8") as f:
    f.write("\n".join(part1))

with open("2.m3u", "w", encoding="utf-8") as f:
    f.write("\n".join(part2))

print("M3U split tamamlandı")

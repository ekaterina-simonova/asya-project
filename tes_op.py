import requests

# Тест с разными DNS-серверами
domains = {
    "Google DNS (8.8.8.8)": "https://dns.google/resolve?name=api.openrouter.ai&type=A",
    "Cloudflare (1.1.1.1)": "https://cloudflare-dns.com/dns-query?name=api.openrouter.ai&type=A"
}

for name, url in domains.items():
    try:
        response = requests.get(url, headers={"Accept": "application/dns-json"})
        print(f"{name}: {'Работает' if response.status_code == 200 else 'Ошибка'}")
        if response.status_code == 200:
            print("IP-адреса:", [answer['data'] for answer in response.json().get('Answer', [])])
    except Exception as e:
        print(f"{name}: Ошибка - {str(e)}")
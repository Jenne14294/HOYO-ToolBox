import json
import requests

url = "https://raw.githubusercontent.com/EnkaNetwork/API-docs/refs/heads/master/store/zzz/avatars.json"

response = requests.get(url)
if response.status_code == 200:
    data = response.json()
    print(data)
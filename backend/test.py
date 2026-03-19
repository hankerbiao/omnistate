import json

import requests

with open("demo.json") as f:
    config = json.load(f)

url = 'http://127.0.0.1:8000/api/v1/automation-test-cases/report'

response = requests.post(url, json=config)
print(response.json())

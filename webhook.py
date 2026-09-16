import requests
import json

webhook_url = 'http://127.0.0.1:8000/webhook/invoice'


data = { 'name': 'lolik',
        'Url_channel': 'bolik',
        'secret_key': 'blablabla123',
        'status': 'paid',
        'invoice_id': 'INV6P2yg' }

# r = requests.post(webhook_url, data = json.dumps(data), headers={'Content-Type':'application/json'})

r = requests.post(webhook_url, json=data)
print(r.status_code, r.text)
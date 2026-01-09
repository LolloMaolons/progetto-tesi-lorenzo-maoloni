import requests
import csv
import os

API_URL = os.environ.get('REST_API_URL', 'http://localhost:8080')
THRESHOLD = int(os.environ.get('LOW_STOCK_THRESHOLD', '25'))
DISCOUNT = float(os.environ.get('DISCOUNT_PERCENTAGE', '10'))

JWT = os.environ.get('JWT', '')
headers = {"Authorization": f"Bearer {JWT}"} if JWT else {}

products = requests.get(f"{API_URL}/products", headers=headers).json()
with open('products.csv', 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['productId', 'oldPrice', 'newPrice'])
    for p in products:
        if p['stock'] < THRESHOLD:
            writer.writerow([p['id'], p['price'], round(p['price'] * (1 - DISCOUNT / 100), 2)])
            
print("Generato products.csv")
print(products)
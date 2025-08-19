import json
import csv
import re
import requests

# Fetch live EUR to USD rate
def get_eur_to_usd_rate():
    url = "https://api.frankfurter.app/latest?from=EUR&to=USD"
    response = requests.get(url)
    data = response.json()
    return data["rates"]["USD"]

def parse_price(price_str):
    """
    Extract numeric value and currency symbol.
    Returns (amount: float, currency: str)
    """
    match = re.match(r'([€$])\s*([0-9,.]+)', price_str)
    if not match:
        return None, None
    currency = match.group(1)
    amount = float(match.group(2).replace(',', ''))
    return amount, currency

# Get live rate
EUR_TO_USD = get_eur_to_usd_rate()
print(f"Live EUR → USD rate: {EUR_TO_USD}")

# Load JSON data
with open("multi_cloud_h100_prices.json", "r", encoding="utf-8") as f:
    data = json.load(f)

providers = data.get("providers", {})

rows = []
for provider, variants in providers.items():
    for variant, price_str in variants.items():
        amount, currency = parse_price(price_str)
        if amount is None:
            continue
        
        if currency == '€':
            usd_price = round(amount * EUR_TO_USD, 4)
            price = f"${usd_price}"
        else:
            price = price_str
        
        rows.append({
            "Provider": provider,
            "Variant": variant,
            "Price (USD)": price
        })

# Write to CSV
with open("providers_prices_usd.csv", "w", newline="", encoding="utf-8") as csvfile:
    fieldnames = ["Provider", "Variant", "Price (USD)"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

    writer.writeheader()
    writer.writerows(rows)

print("✅ CSV file 'providers_prices_usd.csv' created successfully!")

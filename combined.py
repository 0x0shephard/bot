import json
import os
from datetime import datetime

# Input file paths
azure_file = "azure_h100_prices_fixed.json"  # path to your 1st file
main_file = "multi_cloud_h100_prices.json"  # path to your 2nd file

# Load Azure data
if not os.path.exists(azure_file):
    print(f"❌ Azure file not found: {azure_file}")
    exit(1)

with open(azure_file, "r", encoding="utf-8") as f:
    azure_data = json.load(f)

# Load main data
if not os.path.exists(main_file):
    print(f"❌ Main JSON file not found: {main_file}")
    exit(1)

with open(main_file, "r", encoding="utf-8") as f:
    main_data = json.load(f)

# Extract Azure info
provider_name = azure_data.get("provider", "Microsoft Azure")
prices = azure_data.get("prices", {})

# Ensure "providers" exists
if "providers" not in main_data:
    main_data["providers"] = {}

# Insert or update Microsoft Azure section
main_data["providers"][provider_name] = prices

# Update summary
main_data["summary"]["total_providers"] = len(main_data["providers"])
main_data["summary"]["total_h100_variants"] = sum(len(v) for v in main_data["providers"].values())
main_data["summary"]["last_updated"] = datetime.now().isoformat()

# Update cheapest / most expensive logic (optional)
all_prices = []
for p_name, variants in main_data["providers"].items():
    for variant, price in variants.items():
        # Extract numeric price if possible
        try:
            num_price = float(price.replace("$", "").replace("/hr", "").replace("€", "").replace(",", ""))
            all_prices.append((p_name, variant, num_price))
        except:
            pass

if all_prices:
    cheapest = min(all_prices, key=lambda x: x[2])
    most_expensive = max(all_prices, key=lambda x: x[2])
    main_data["summary"]["cheapest"] = {
        "provider": cheapest[0],
        "variant": cheapest[1],
        "price": f"${cheapest[2]}"
    }
    main_data["summary"]["most_expensive"] = {
        "provider": most_expensive[0],
        "variant": most_expensive[1],
        "price": f"${most_expensive[2]}"
    }

# Save updated file
with open(main_file, "w", encoding="utf-8") as f:
    json.dump(main_data, f, indent=2, ensure_ascii=False)

print(f"✅ Successfully added {provider_name} pricing to {main_file}")

import json
import os
from datetime import datetime

# === File paths ===
provider_file = "runpod_h100_prices.json"           # The new JSON file (e.g., RunPod)
main_file = "multi_cloud_h100_prices.json"     # The main consolidated file

# === Load provider data ===
if not os.path.exists(provider_file):
    print(f"❌ Provider file not found: {provider_file}")
    exit(1)

with open(provider_file, "r", encoding="utf-8") as f:
    provider_data = json.load(f)

# === Load main data ===
if not os.path.exists(main_file):
    print(f"❌ Main file not found: {main_file}")
    exit(1)

with open(main_file, "r", encoding="utf-8") as f:
    main_data = json.load(f)

# === Extract provider info ===
if "providers" not in provider_data or not provider_data["providers"]:
    print("❌ No 'providers' key found in provider file.")
    exit(1)

# Merge each provider in the new file
for provider_name, provider_info in provider_data["providers"].items():
    # Extract variants and format them for consistency
    if "variants" in provider_info:
        formatted_variants = {}
        for variant_name, variant_info in provider_info["variants"].items():
            price = variant_info.get("price_per_hour")
            currency = variant_info.get("currency", "USD")
            formatted_variants[variant_name] = f"{currency} {price}/hr" if price is not None else "N/A"
    else:
        formatted_variants = {}

    # Update or insert the provider into the main JSON
    main_data["providers"][provider_name] = formatted_variants
    print(f"✅ Added/updated provider: {provider_name} with {len(formatted_variants)} variants")

# === Update summary ===
main_data["summary"]["total_providers"] = len(main_data["providers"])
main_data["summary"]["total_h100_variants"] = sum(len(v) for v in main_data["providers"].values())
main_data["summary"]["last_updated"] = datetime.now().isoformat()

# === Recalculate cheapest and most expensive ===
all_prices = []
for pname, variants in main_data["providers"].items():
    for vname, price_str in variants.items():
        try:
            clean = price_str.replace("$", "").replace("USD", "").replace("€", "").replace("/hr", "").strip()
            price = float(clean)
            all_prices.append((pname, vname, price))
        except:
            continue

if all_prices:
    cheapest = min(all_prices, key=lambda x: x[2])
    most_expensive = max(all_prices, key=lambda x: x[2])
    main_data["summary"]["cheapest"] = {
        "provider": cheapest[0],
        "variant": cheapest[1],
        "price": f"${cheapest[2]}/hr"
    }
    main_data["summary"]["most_expensive"] = {
        "provider": most_expensive[0],
        "variant": most_expensive[1],
        "price": f"${most_expensive[2]}/hr"
    }

# === Save updated JSON ===
with open(main_file, "w", encoding="utf-8") as f:
    json.dump(main_data, f, indent=2, ensure_ascii=False)

print(f"\n🎯 Successfully merged provider data into {main_file}")


import json
import os
from datetime import datetime

# === File paths ===
provider_file = "atlanticnet_h100_prices.json"         # The new provider JSON file
main_file = "multi_cloud_h100_prices.json"       # The main consolidated file

# === Load provider data ===
if not os.path.exists(provider_file):
    print(f"❌ Provider file not found: {provider_file}")
    exit(1)

with open(provider_file, "r", encoding="utf-8") as f:
    provider_data = json.load(f)

# === Load main data ===
if not os.path.exists(main_file):
    print(f"❌ Main file not found: {main_file}")
    exit(1)

with open(main_file, "r", encoding="utf-8") as f:
    main_data = json.load(f)

# === Extract and merge provider info ===
if "providers" not in provider_data or not provider_data["providers"]:
    print("❌ No 'providers' key found in provider file.")
    exit(1)

for provider_name, provider_info in provider_data["providers"].items():
    # Ensure proper structure (look inside variants)
    if "variants" in provider_info:
        formatted_variants = {}
        for variant_name, variant_info in provider_info["variants"].items():
            price = variant_info.get("price_per_hour")
            currency = variant_info.get("currency", "USD")
            formatted_variants[f"{variant_name} (On-Demand)"] = f"${price}/hr" if price is not None else "N/A"
    else:
        formatted_variants = {}

    # If the provider already exists, merge with existing variants
    if provider_name in main_data["providers"]:
        existing = main_data["providers"][provider_name]
        existing.update(formatted_variants)
        main_data["providers"][provider_name] = existing
        print(f"🔁 Updated existing provider: {provider_name} with {len(formatted_variants)} new variants")
    else:
        main_data["providers"][provider_name] = formatted_variants
        print(f"✅ Added new provider: {provider_name} with {len(formatted_variants)} variants")

# === Update summary ===
main_data["summary"]["total_providers"] = len(main_data["providers"])
main_data["summary"]["total_h100_variants"] = sum(len(v) for v in main_data["providers"].values())
main_data["summary"]["last_updated"] = datetime.now().isoformat()

# === Recalculate cheapest and most expensive ===
all_prices = []
for pname, variants in main_data["providers"].items():
    for vname, price_str in variants.items():
        try:
            clean = price_str.replace("$", "").replace("USD", "").replace("€", "").replace("/hr", "").strip()
            price = float(clean)
            all_prices.append((pname, vname, price))
        except:
            continue

if all_prices:
    cheapest = min(all_prices, key=lambda x: x[2])
    most_expensive = max(all_prices, key=lambda x: x[2])
    main_data["summary"]["cheapest"] = {
        "provider": cheapest[0],
        "variant": cheapest[1],
        "price": f"${cheapest[2]}/hr"
    }
    main_data["summary"]["most_expensive"] = {
        "provider": most_expensive[0],
        "variant": most_expensive[1],
        "price": f"${most_expensive[2]}/hr"
    }

# === Save updated JSON ===
with open(main_file, "w", encoding="utf-8") as f:
    json.dump(main_data, f, indent=2, ensure_ascii=False)

print(f"\n🎯 Successfully merged provider data from '{provider_file}' into '{main_file}'")

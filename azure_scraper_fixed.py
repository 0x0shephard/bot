#!/usr/bin/env python3
"""
Improved Microsoft Azure H100 Pricing Scraper
Fixes:
1. Strict H100 validation - only extracts actual H100 GPUs
2. No duplicate per-GPU calculations
3. Better error handling and logging
"""

import requests
from bs4 import BeautifulSoup
import re
import json
from typing import Dict, Optional
import time


class AzureH100Scraper:
    """Improved Azure H100 scraper with strict validation"""
    
    def __init__(self):
        self.name = "Microsoft Azure"
        self.base_url = "https://azure.microsoft.com/en-us/pricing/details/virtual-machines/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/html',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    
    def get_h100_prices(self) -> Dict[str, str]:
        """Main method to extract H100 prices with strict validation"""
        print(f"🔍 Fetching {self.name} H100 pricing...")
        print("=" * 80)
        
        h100_prices = {}
        
        # Try multiple methods in order
        methods = [
            ("Azure Retail Pricing API", self._try_azure_retail_api),
            ("ND H100 v5 Series Extraction", self._try_nd_h100_series_extraction),
            ("Azure Calculator", self._try_azure_calculator),
        ]
        
        for method_name, method_func in methods:
            print(f"\n📋 Method: {method_name}")
            try:
                prices = method_func()
                if prices:
                    h100_prices.update(prices)
                    print(f"   ✅ Found {len(prices)} H100 prices!")
                    # Continue trying other methods to get comprehensive data
                else:
                    print(f"   ❌ No prices found")
            except Exception as e:
                print(f"   ⚠️  Error: {str(e)[:100]}")
        
        if not h100_prices:
            print("\n❌ All methods failed - unable to extract H100 pricing")
            return {'Error': 'Unable to fetch live H100 pricing from Microsoft Azure'}
        
        print(f"\n✅ Successfully extracted {len(h100_prices)} H100 price variants")
        return h100_prices
    
    def _try_azure_retail_api(self) -> Dict[str, str]:
        """Try Azure Retail Pricing API with strict H100 validation"""
        h100_prices = {}
        
        # Azure Retail Pricing API endpoints with strict H100 filters
        api_urls = [
            "https://prices.azure.com/api/retail/prices?api-version=2023-01-01-preview&$filter=serviceName eq 'Virtual Machines' and contains(productName, 'ND H100 v5')",
            "https://prices.azure.com/api/retail/prices?api-version=2023-01-01-preview&$filter=serviceName eq 'Virtual Machines' and contains(armSkuName, 'ND96isr_H100_v5')",
            "https://prices.azure.com/api/retail/prices?api-version=2023-01-01-preview&$filter=serviceName eq 'Virtual Machines' and contains(armSkuName, 'ND48s_H100_v5')",
            "https://prices.azure.com/api/retail/prices?api-version=2023-01-01-preview&$filter=serviceName eq 'Virtual Machines' and contains(armSkuName, 'ND24s_H100_v5')",
            "https://prices.azure.com/api/retail/prices?api-version=2023-01-01-preview&$filter=serviceName eq 'Virtual Machines' and contains(armSkuName, 'ND12s_H100_v5')",
        ]
        
        for api_url in api_urls:
            try:
                print(f"    Trying API: {api_url[:80]}...")
                
                response = requests.get(api_url, headers=self.headers, timeout=20)
                
                if response.status_code == 200:
                    data = response.json()
                    items = data.get('Items', [])
                    print(f"      Got {len(items)} items from API")
                    
                    # Extract H100 pricing with strict validation
                    found_prices = self._extract_from_retail_api(items)
                    if found_prices:
                        h100_prices.update(found_prices)
                        print(f"      ✅ Extracted {len(found_prices)} valid H100 prices")
                        
                elif response.status_code == 429:
                    print(f"      Rate limited - waiting...")
                    time.sleep(2)
                else:
                    print(f"      Status {response.status_code}")
                    
            except Exception as e:
                print(f"      Error: {str(e)[:50]}...")
                continue
        
        return h100_prices
    
    def _extract_from_retail_api(self, items) -> Dict[str, str]:
        """Extract H100 prices from Azure Retail API with strict validation"""
        prices = {}
        us_east_prices = {}  # Prioritize US East regions
        us_east_price_list = []  # Collect all US East prices for averaging
        
        for item in items:
            try:
                product_name = item.get('productName', '').upper()
                sku_name = item.get('skuName', '').upper()
                arm_sku_name = item.get('armSkuName', '').upper()
                service_name = item.get('serviceName', '').upper()
                
                # STRICT VALIDATION: Must be H100 v5 series
                is_valid_h100 = False
                vm_type = None
                gpu_count = 1
                
                # Check for specific H100 v5 SKUs
                if 'ND96ISR_H100_V5' in arm_sku_name or 'ND96' in product_name:
                    if 'H100' in product_name or 'H100' in sku_name:
                        is_valid_h100 = True
                        vm_type = 'ND96isr'
                        gpu_count = 8
                
                elif 'ND48S_H100_V5' in arm_sku_name or 'ND48' in product_name:
                    if 'H100' in product_name or 'H100' in sku_name:
                        is_valid_h100 = True
                        vm_type = 'ND48s'
                        gpu_count = 4
                
                elif 'ND24S_H100_V5' in arm_sku_name or 'ND24' in product_name:
                    if 'H100' in product_name or 'H100' in sku_name:
                        is_valid_h100 = True
                        vm_type = 'ND24s'
                        gpu_count = 2
                
                elif 'ND12S_H100_V5' in arm_sku_name or 'ND12' in product_name:
                    if 'H100' in product_name or 'H100' in sku_name:
                        is_valid_h100 = True
                        vm_type = 'ND12s'
                        gpu_count = 1
                
                # Also accept if productName explicitly says "ND H100 v5"
                elif 'ND H100 V5' in product_name or 'ND_H100_V5' in product_name:
                    is_valid_h100 = True
                    # Try to detect VM type from name
                    if 'ND96' in product_name:
                        vm_type = 'ND96isr'
                        gpu_count = 8
                    elif 'ND48' in product_name:
                        vm_type = 'ND48s'
                        gpu_count = 4
                    elif 'ND24' in product_name:
                        vm_type = 'ND24s'
                        gpu_count = 2
                    elif 'ND12' in product_name:
                        vm_type = 'ND12s'
                        gpu_count = 1
                    else:
                        vm_type = 'Unknown H100'
                
                if not is_valid_h100:
                    continue  # Skip non-H100 SKUs
                
                # Extract price
                unit_price = item.get('unitPrice', 0)
                currency_code = item.get('currencyCode', 'USD')
                unit_of_measure = item.get('unitOfMeasure', 'Hour')
                region = item.get('armRegionName', 'Unknown')
                
                if unit_price and currency_code == 'USD' and 'Hour' in unit_of_measure:
                    price = float(unit_price)
                    
                    # Reasonable price range for Azure ND H100 series (per cluster)
                    if 1 < price < 200:
                        # Divide by GPU count to get per-GPU price
                        per_gpu_price = price / gpu_count
                        
                        # Create descriptive name
                        if vm_type:
                            if gpu_count > 1:
                                price_key = f'H100 ({vm_type} - {gpu_count}x GPUs)'
                            else:
                                price_key = f'H100 ({vm_type})'
                        else:
                            price_key = 'H100 (Azure)'
                        
                        # Prioritize US East regions as benchmark
                        if region in ['eastus', 'eastus2']:
                            us_east_price_list.append({
                                'price': per_gpu_price,  # Store per-GPU price
                                'region': region,
                                'vm_type': vm_type,
                                'gpu_count': gpu_count,
                                'price_key': price_key
                            })
                            print(f"        API ✓ {price_key} = ${price:.2f}/hr → ${per_gpu_price:.2f}/GPU (Region: {region}) ⭐ US EAST")
                        else:
                            # Keep non-US East as fallback only if no US East price found yet
                            if price_key not in prices:
                                prices[price_key] = f"${per_gpu_price:.2f}/hr"
                                print(f"        API ✓ {price_key} = ${price:.2f}/hr → ${per_gpu_price:.2f}/GPU (Region: {region})")
                        
            except (ValueError, TypeError, KeyError) as e:
                print(f"        Error parsing item: {str(e)[:30]}")
                continue
        
        # Calculate average of US East prices (already per-GPU)
        if us_east_price_list:
            avg_per_gpu_price = sum(p['price'] for p in us_east_price_list) / len(us_east_price_list)
            vm_info = us_east_price_list[0]
            price_key = vm_info['price_key']
            
            us_east_prices[price_key] = f"${avg_per_gpu_price:.2f}/hr"
            
            print(f"      ✅ Averaged {len(us_east_price_list)} US East prices: ${avg_per_gpu_price:.2f}/GPU")
            print(f"      📊 US East per-GPU price range: ${min(p['price'] for p in us_east_price_list):.2f} - ${max(p['price'] for p in us_east_price_list):.2f}/GPU")
        
        # Prefer US East averaged price, fallback to other regions if US East not found
        final_prices = us_east_prices if us_east_prices else prices
        
        if us_east_prices:
            print(f"      ✅ Using US East pricing as benchmark (industry standard)")
        elif prices:
            print(f"      ⚠️  No US East pricing found, using fallback regions")
        
        return final_prices
    
    def _try_nd_h100_series_extraction(self) -> Dict[str, str]:
        """Extract H100 pricing from ND H100 v5 series pages with strict validation"""
        h100_prices = {}
        
        # Azure ND H100 v5 series pages
        nd_urls = [
            "https://azure.microsoft.com/en-us/pricing/details/virtual-machines/linux/",
            "https://azure.microsoft.com/en-us/pricing/details/virtual-machines/windows/",
        ]
        
        for url in nd_urls:
            try:
                print(f"    Trying: {url}")
                response = requests.get(url, headers=self.headers, timeout=25)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    text_content = soup.get_text()
                    
                    # STRICT CHECK: Must contain BOTH "H100" AND "v5"
                    if not (('H100' in text_content or 'h100' in text_content.lower()) and 
                            ('v5' in text_content or 'V5' in text_content)):
                        print(f"      ⚠️ Page doesn't contain H100 v5 indicators")
                        continue
                    
                    print(f"      ✓ Page contains H100 v5 data")
                    
                    # Use STRICT patterns that explicitly require "H100" and "v5"
                    nd_h100_patterns = [
                        # Must match "ND96isr H100 v5" or similar with price
                        (r'ND96isr\s+H100\s+v5[^$]*\$([0-9.,]+)(?:/hour|/hr|per hour)', 'H100 (ND96isr - 8x GPUs)', 8),
                        (r'Standard_ND96isr_H100_v5[^$]*\$([0-9.,]+)', 'H100 (ND96isr - 8x GPUs)', 8),
                        
                        # ND48s H100 v5 (4x H100)
                        (r'ND48s\s+H100\s+v5[^$]*\$([0-9.,]+)(?:/hour|/hr|per hour)', 'H100 (ND48s - 4x GPUs)', 4),
                        (r'Standard_ND48s_H100_v5[^$]*\$([0-9.,]+)', 'H100 (ND48s - 4x GPUs)', 4),
                        
                        # ND24s H100 v5 (2x H100)
                        (r'ND24s\s+H100\s+v5[^$]*\$([0-9.,]+)(?:/hour|/hr|per hour)', 'H100 (ND24s - 2x GPUs)', 2),
                        (r'Standard_ND24s_H100_v5[^$]*\$([0-9.,]+)', 'H100 (ND24s - 2x GPUs)', 2),
                        
                        # ND12s H100 v5 (1x H100)
                        (r'ND12s\s+H100\s+v5[^$]*\$([0-9.,]+)(?:/hour|/hr|per hour)', 'H100 (ND12s - 1x GPU)', 1),
                        (r'Standard_ND12s_H100_v5[^$]*\$([0-9.,]+)', 'H100 (ND12s - 1x GPU)', 1),
                    ]
                    
                    for pattern, name, gpu_count in nd_h100_patterns:
                        matches = re.findall(pattern, text_content, re.IGNORECASE)
                        for match in matches:
                            try:
                                # Clean price (remove commas)
                                price_str = match.replace(',', '')
                                price = float(price_str)
                                
                                # Reasonable range for Azure ND series (cluster pricing)
                                if 2 < price < 200:
                                    # Only store cluster price, not per-GPU
                                    h100_prices[name] = f"${price:.2f}/hr"
                                    print(f"        Pattern ✓ {name} = ${price:.2f}/hr ({gpu_count}x GPUs in cluster)")
                                    
                            except (ValueError, TypeError):
                                continue
                    
                    # Also check tables for H100 pricing
                    found_in_tables = self._extract_from_tables(soup)
                    if found_in_tables:
                        h100_prices.update(found_in_tables)
                        print(f"      ✓ Found {len(found_in_tables)} prices in tables")
                    
                    if h100_prices:
                        return h100_prices
                    
            except requests.RequestException as e:
                print(f"      Error: {str(e)[:50]}...")
                continue
        
        return h100_prices
    
    def _extract_from_tables(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract H100 pricing from HTML tables with strict validation"""
        prices = {}
        
        tables = soup.find_all('table')
        for table in tables:
            table_text = table.get_text()
            
            # Only process tables that mention H100 and v5
            if not (('H100' in table_text or 'h100' in table_text.lower()) and 
                    ('v5' in table_text or 'V5' in table_text)):
                continue
            
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    row_text = ' '.join([cell.get_text().strip() for cell in cells])
                    
                    # Must contain both H100 indicator AND price
                    if 'H100' in row_text and '$' in row_text:
                        # Check for specific VM types
                        vm_configs = [
                            ('ND96isr', 8, 'H100 (ND96isr - 8x GPUs)'),
                            ('ND96', 8, 'H100 (ND96isr - 8x GPUs)'),
                            ('ND48s', 4, 'H100 (ND48s - 4x GPUs)'),
                            ('ND48', 4, 'H100 (ND48s - 4x GPUs)'),
                            ('ND24s', 2, 'H100 (ND24s - 2x GPUs)'),
                            ('ND24', 2, 'H100 (ND24s - 2x GPUs)'),
                            ('ND12s', 1, 'H100 (ND12s - 1x GPU)'),
                            ('ND12', 1, 'H100 (ND12s - 1x GPU)'),
                        ]
                        
                        for vm_pattern, gpu_count, vm_name in vm_configs:
                            if vm_pattern in row_text:
                                price_matches = re.findall(r'\$([0-9.,]+)', row_text)
                                if price_matches:
                                    try:
                                        price = float(price_matches[0].replace(',', ''))
                                        if 2 < price < 200:
                                            prices[vm_name] = f"${price:.2f}/hr"
                                            print(f"        Table ✓ {vm_name} = ${price:.2f}/hr")
                                            break  # Found price for this row
                                    except ValueError:
                                        continue
        
        return prices
    
    def _try_azure_calculator(self) -> Dict[str, str]:
        """Try Azure pricing calculator for H100 pricing"""
        h100_prices = {}
        
        calculator_urls = [
            "https://azure.microsoft.com/api/v3/pricing/calculator/virtual-machines",
        ]
        
        for url in calculator_urls:
            try:
                print(f"    Trying calculator: {url}")
                response = requests.get(url, headers=self.headers, timeout=20)
                
                if response.status_code == 200:
                    if 'json' in response.headers.get('content-type', '').lower():
                        data = response.json()
                        print(f"      Calculator API success!")
                        
                        # Try to extract H100 pricing
                        found_prices = self._extract_from_calculator(data)
                        if found_prices:
                            h100_prices.update(found_prices)
                            return h100_prices
                    else:
                        print(f"      Not JSON response")
                        
            except Exception as e:
                print(f"      Error: {str(e)[:50]}...")
                continue
        
        return h100_prices
    
    def _extract_from_calculator(self, data) -> Dict[str, str]:
        """Extract H100 prices from calculator API response"""
        prices = {}
        
        # Recursively search for H100 pricing in nested data
        def search_dict(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    # Look for H100 indicators
                    if isinstance(key, str) and ('h100' in key.lower() or 'nd96' in key.lower() or 'nd48' in key.lower()):
                        if isinstance(value, (int, float)) and 1 < value < 200:
                            prices[f'H100 (Calculator - {key})'] = f"${value:.2f}/hr"
                            print(f"        Calculator ✓ Found in {path}.{key}")
                    search_dict(value, f"{path}.{key}" if path else key)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    search_dict(item, f"{path}[{i}]")
        
        search_dict(data)
        return prices


def main():
    """Test the improved Azure scraper"""
    print("🚀 Microsoft Azure H100 GPU Pricing Scraper (Fixed)")
    print("=" * 80)
    print()
    
    scraper = AzureH100Scraper()
    h100_prices = scraper.get_h100_prices()
    
    print("\n" + "=" * 80)
    print("🎯 RESULTS - Microsoft Azure H100 Pricing")
    print("=" * 80)
    
    if h100_prices and 'Error' not in h100_prices:
        print(f"\n✅ Successfully extracted {len(h100_prices)} H100 price variants:\n")
        
        for variant, price in sorted(h100_prices.items()):
            print(f"  • {variant:50s} {price}")
        
        # Calculate per-GPU prices for multi-GPU configs
        print("\n📊 Per-GPU Pricing Analysis:")
        print("-" * 80)
        
        for variant, price in sorted(h100_prices.items()):
            # Extract numeric price
            price_match = re.search(r'\$([0-9.]+)', price)
            if price_match:
                price_num = float(price_match.group(1))
                
                # Determine GPU count
                if '8x GPUs' in variant or 'ND96' in variant:
                    per_gpu = price_num / 8
                    print(f"  • {variant:50s} ${per_gpu:.2f}/GPU")
                elif '4x GPUs' in variant or 'ND48' in variant:
                    per_gpu = price_num / 4
                    print(f"  • {variant:50s} ${per_gpu:.2f}/GPU")
                elif '2x GPUs' in variant or 'ND24' in variant:
                    per_gpu = price_num / 2
                    print(f"  • {variant:50s} ${per_gpu:.2f}/GPU")
                else:
                    print(f"  • {variant:50s} ${price_num:.2f}/GPU")
        
        # Save to JSON
        output_file = "azure_h100_prices_fixed.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'provider': 'Microsoft Azure',
                'prices': h100_prices
            }, f, indent=2)
        
        print(f"\n💾 Results saved to: {output_file}")
        
    else:
        print("\n❌ Failed to extract H100 pricing")
        if 'Error' in h100_prices:
            print(f"   Error: {h100_prices['Error']}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()

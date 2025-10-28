#!/usr/bin/env python3
"""
RunPod H100 GPU Pricing Scraper
Extracts H100 pricing from runpod.io using Selenium for JavaScript-loaded content
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import time
from typing import Dict, Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException


class RunPodScraper:
    """Scraper for RunPod H100 pricing"""
    
    def __init__(self):
        self.name = "RunPod"
        self.base_url = "https://www.runpod.io"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
    
    def get_h100_prices(self) -> Dict[str, str]:
        """Main method to extract H100 prices"""
        print(f"🔍 Fetching {self.name} H100 pricing...")
        print("=" * 80)
        
        h100_prices = {}
        
        # Try multiple methods
        methods = [
            ("GPU Pricing API", self._try_gpu_pricing_api),
            ("Console API", self._try_console_api),
            ("Selenium Scraper", self._try_selenium_scraper),
            ("Pricing Page", self._try_pricing_page),
            ("GraphQL API", self._try_graphql_api),
        ]
        
        for method_name, method_func in methods:
            print(f"\n📋 Method: {method_name}")
            try:
                prices = method_func()
                if prices:
                    h100_prices.update(prices)
                    print(f"   ✅ Found {len(prices)} H100 prices!")
                    # Return on first success
                    return h100_prices
                else:
                    print(f"   ❌ No prices found")
            except Exception as e:
                print(f"   ⚠️  Error: {str(e)[:100]}")
        
        if not h100_prices:
            print("\n❌ All methods failed - unable to extract H100 pricing")
            return {'Error': 'Unable to fetch H100 pricing from RunPod'}
        
        return h100_prices
    
    def _try_gpu_pricing_api(self) -> Dict[str, str]:
        """Try RunPod GPU pricing API"""
        h100_prices = {}
        
        # RunPod API endpoints
        api_urls = [
            "https://api.runpod.io/graphql?api_key=public",
            "https://www.runpod.io/api/pricing",
            "https://www.runpod.io/api/v1/gpu-types",
            "https://api.runpod.io/v1/gpu-types",
        ]
        
        for api_url in api_urls:
            try:
                print(f"    Trying API: {api_url}")
                response = requests.get(api_url, headers=self.headers, timeout=20)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"      ✓ Got JSON response")
                        
                        # Search for H100 in the JSON
                        found_prices = self._extract_from_json(data)
                        if found_prices:
                            h100_prices.update(found_prices)
                            return h100_prices
                            
                    except json.JSONDecodeError:
                        print(f"      ⚠️  Response is not JSON")
                elif response.status_code == 404:
                    print(f"      Status 404")
                else:
                    print(f"      Status {response.status_code}")
                        
            except Exception as e:
                print(f"      Error: {str(e)[:50]}...")
                continue
        
        return h100_prices
    
    def _try_console_api(self) -> Dict[str, str]:
        """Try RunPod Console API (used by their web interface)"""
        h100_prices = {}
        
        # These are the actual endpoints the RunPod console uses
        api_urls = [
            "https://api.runpod.io/graphql",
        ]
        
        # GraphQL query to get GPU types and pricing
        graphql_query = {
            "query": """
                query GpuTypes {
                    gpuTypes {
                        id
                        displayName
                        memoryInGb
                        secureCloud
                        communityCloud
                        lowestPrice {
                            minimumBidPrice
                            uninterruptablePrice
                        }
                    }
                }
            """
        }
        
        for api_url in api_urls:
            try:
                print(f"    Trying Console API: {api_url}")
                
                # Try POST with GraphQL query
                response = requests.post(
                    api_url,
                    json=graphql_query,
                    headers={**self.headers, 'Content-Type': 'application/json'},
                    timeout=20
                )
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"      ✓ Got GraphQL response")
                        
                        if 'data' in data and 'gpuTypes' in data['data']:
                            gpu_types = data['data']['gpuTypes']
                            print(f"      📋 Found {len(gpu_types)} GPU types")
                            
                            for gpu in gpu_types:
                                if not isinstance(gpu, dict):
                                    continue
                                    
                                display_name = gpu.get('displayName', '')
                                
                                # Check for H100
                                if 'H100' in display_name or 'h100' in display_name.lower():
                                    print(f"      ✓ Found H100: {display_name}")
                                    
                                    lowest_price = gpu.get('lowestPrice')
                                    
                                    # Check if lowestPrice exists and is not None
                                    if lowest_price and isinstance(lowest_price, dict):
                                        # Get secure cloud price (uninterruptable)
                                        uninterruptable = lowest_price.get('uninterruptablePrice')
                                        if uninterruptable is not None:
                                            try:
                                                price = float(uninterruptable)
                                                if 0.5 < price < 50:
                                                    variant_name = f"H100 ({display_name} - Secure)"
                                                    h100_prices[variant_name] = f"${price:.2f}/hr"
                                                    print(f"        ✓ Secure Cloud: ${price:.2f}/hr")
                                            except (ValueError, TypeError):
                                                pass
                                        
                                        # Get community cloud price (spot/bid)
                                        minimum_bid = lowest_price.get('minimumBidPrice')
                                        if minimum_bid is not None:
                                            try:
                                                price = float(minimum_bid)
                                                if 0.5 < price < 50:
                                                    variant_name = f"H100 ({display_name} - Spot)"
                                                    h100_prices[variant_name] = f"${price:.2f}/hr"
                                                    print(f"        ✓ Community Cloud (Spot): ${price:.2f}/hr")
                                            except (ValueError, TypeError):
                                                pass
                                    else:
                                        print(f"        ⚠️  No pricing data available for {display_name}")
                            
                            if h100_prices:
                                return h100_prices
                                
                    except (json.JSONDecodeError, KeyError) as e:
                        print(f"      ⚠️  Error parsing response: {str(e)[:50]}")
                else:
                    print(f"      Status {response.status_code}")
                        
            except Exception as e:
                print(f"      Error: {str(e)[:50]}...")
                continue
        
        return h100_prices
    
    def _try_graphql_api(self) -> Dict[str, str]:
        """Try alternative GraphQL queries"""
        h100_prices = {}
        
        # Alternative GraphQL queries
        queries = [
            {
                "query": "{ gpuTypes { displayName lowestPrice { uninterruptablePrice minimumBidPrice } } }"
            },
            {
                "query": "query { podTypes { name price } }"
            },
        ]
        
        api_url = "https://api.runpod.io/graphql"
        
        for query in queries:
            try:
                print(f"    Trying GraphQL query...")
                response = requests.post(
                    api_url,
                    json=query,
                    headers={**self.headers, 'Content-Type': 'application/json'},
                    timeout=20
                )
                
                if response.status_code == 200:
                    data = response.json()
                    found_prices = self._extract_from_json(data)
                    if found_prices:
                        h100_prices.update(found_prices)
                        return h100_prices
                        
            except Exception as e:
                print(f"      Error: {str(e)[:30]}...")
                continue
        
        return h100_prices
    
    def _extract_from_json(self, data, path="") -> Dict[str, str]:
        """Recursively search JSON for H100 pricing"""
        prices = {}
        
        if isinstance(data, dict):
            # Check if this looks like a GPU type entry
            if 'displayName' in data or 'name' in data:
                name = data.get('displayName', data.get('name', ''))
                
                if isinstance(name, str) and ('h100' in name.lower() or 'H100' in name):
                    print(f"        Found H100 entry: {name}")
                    
                    # Look for pricing fields
                    price_fields = ['price', 'lowestPrice', 'uninterruptablePrice', 'minimumBidPrice', 
                                   'pricePerHour', 'hourlyPrice', 'cost']
                    
                    for field in price_fields:
                        if field in data:
                            price_val = data[field]
                            
                            if isinstance(price_val, (int, float)) and 0.5 < price_val < 50:
                                prices[f'H100 ({name})'] = f"${price_val:.2f}/hr"
                                print(f"        ✓ Found price: ${price_val:.2f}/hr")
                                return prices
                            
                            elif isinstance(price_val, dict):
                                # Nested price object
                                for sub_field in ['uninterruptablePrice', 'minimumBidPrice', 'price']:
                                    if sub_field in price_val:
                                        sub_price = price_val[sub_field]
                                        if isinstance(sub_price, (int, float)) and 0.5 < sub_price < 50:
                                            variant = 'Secure' if 'uninterruptable' in sub_field else 'Spot'
                                            prices[f'H100 ({name} - {variant})'] = f"${sub_price:.2f}/hr"
                                            print(f"        ✓ Found {variant} price: ${sub_price:.2f}/hr")
            
            # Recurse into nested structures
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    nested_prices = self._extract_from_json(value, f"{path}.{key}")
                    if nested_prices:
                        prices.update(nested_prices)
                        if prices:  # Return as soon as we find H100 prices
                            return prices
                        
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    nested_prices = self._extract_from_json(item, f"{path}[{i}]")
                    if nested_prices:
                        prices.update(nested_prices)
                        if prices:
                            return prices
        
        return prices
    
    def _try_pricing_page(self) -> Dict[str, str]:
        """Try to extract prices from pricing/GPU pages"""
        h100_prices = {}
        
        pricing_urls = [
            "https://www.runpod.io/console/gpu-cloud",
            "https://www.runpod.io/gpu-instance/pricing",
            "https://www.runpod.io/pricing",
            "https://runpod.io/console/gpu-cloud",
        ]
        
        for url in pricing_urls:
            try:
                print(f"    Trying: {url}")
                response = requests.get(url, headers=self.headers, timeout=20)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    html_content = str(soup)
                    text_content = soup.get_text()
                    
                    # Debug: check for GPU models
                    if 'GPU' in text_content or 'gpu' in text_content.lower():
                        print(f"      ✓ Page contains GPU references")
                        gpu_models = ['H100', 'A100', 'A40', 'RTX']
                        found_models = [model for model in gpu_models if model in text_content]
                        if found_models:
                            print(f"      📋 Found GPU models: {', '.join(found_models)}")
                    
                    if 'H100' not in text_content and 'h100' not in text_content.lower():
                        print(f"      ⚠️  Page doesn't contain H100 references")
                        continue
                    
                    print(f"      ✓ Page contains H100 data")
                    
                    # Debug: Find all prices near H100 mentions
                    h100_sections = re.findall(r'H100[^\n]{0,300}', text_content, re.IGNORECASE)
                    if h100_sections:
                        print(f"      🔍 Debug - Found {len(h100_sections)} H100 sections:")
                        for section in h100_sections[:5]:  # Show first 5
                            prices_in_section = re.findall(r'\$([0-9.]+)', section)
                            if prices_in_section:
                                print(f"         '{section[:150]}...' → Prices: {prices_in_section}")
                    
                    # Look for H100 pricing patterns matching the format: "H100 PCIe ... $1.99/hr"
                    h100_patterns = [
                        # Match "H100 PCIe" or "H100 SXM" followed by price
                        (r'H100\s+PCIe[^\$]{0,200}\$([0-9.]+)/hr', 'H100 PCIe'),
                        (r'H100\s+SXM[^\$]{0,200}\$([0-9.]+)/hr', 'H100 SXM'),
                        (r'H100\s+NVL[^\$]{0,200}\$([0-9.]+)/hr', 'H100 NVL'),
                        # Generic H100 with price
                        (r'H100[^\$\n]{0,200}\$([0-9.]+)/hr', 'H100'),
                    ]
                    
                    for pattern, default_variant in h100_patterns:
                        matches = re.findall(pattern, text_content, re.IGNORECASE | re.DOTALL)
                        for match in matches:
                            try:
                                price = float(match)
                                # Focus on on-demand prices ($1-$10 range), skip spot prices
                                if 1.0 <= price <= 10.0:
                                    variant_name = default_variant
                                    
                                    # Check if variant already exists
                                    if variant_name not in h100_prices:
                                        h100_prices[variant_name] = f"${price:.2f}/hr"
                                        print(f"        Pattern ✓ {variant_name} = ${price:.2f}/hr")
                            except ValueError:
                                continue
                    
                    if h100_prices:
                        return h100_prices
                    
                    # Try structured extraction with more detail
                    found_prices = self._extract_from_page_structure(soup)
                    if found_prices:
                        h100_prices.update(found_prices)
                        return h100_prices
                    
                    # Last resort: look for JSON data embedded in page
                    found_prices = self._extract_from_embedded_json(html_content)
                    if found_prices:
                        h100_prices.update(found_prices)
                        return h100_prices
                        
                else:
                    print(f"      Status {response.status_code}")
                    
            except Exception as e:
                print(f"      Error: {str(e)[:50]}...")
                continue
        
        return h100_prices
    
    def _extract_from_page_structure(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract H100 pricing from structured HTML elements"""
        prices = {}
        
        # Look for RunPod's specific pricing table structure
        # Based on the screenshot: div.gpu-pricing-table_section with w-dyn-item class
        pricing_items = soup.find_all('div', class_=re.compile(r'w-dyn-item'))
        
        if not pricing_items:
            # Fallback: look for any div with class containing 'gpu' or 'pricing'
            pricing_items = soup.find_all('div', class_=re.compile(r'(gpu|pricing)', re.I))
        
        print(f"      📋 Found {len(pricing_items)} pricing items")
        
        for item in pricing_items:
            item_text = item.get_text(separator=' ', strip=True)
            item_html = str(item)
            
            # Check if this item mentions H100
            if 'H100' in item_text or 'h100' in item_text.lower():
                # Look for price pattern with /hr
                price_matches = re.findall(r'\$([0-9.]+)/hr', item_text)
                
                for price_str in price_matches:
                    try:
                        price = float(price_str)
                        
                        # Filter for on-demand prices ($1-$10 range)
                        if 1.0 <= price <= 10.0:
                            # Identify variant
                            variant_name = "H100"
                            item_upper = item_text.upper()
                            
                            if 'SXM' in item_upper:
                                variant_name = "H100 SXM"
                            elif 'PCIE' in item_upper or 'PCI-E' in item_upper:
                                variant_name = "H100 PCIe"
                            elif 'NVL' in item_upper:
                                variant_name = "H100 NVL"
                            
                            # Skip if already added
                            if variant_name not in prices:
                                prices[variant_name] = f"${price:.2f}/hr"
                                print(f"        Item ✓ {variant_name} = ${price:.2f}/hr")
                    except ValueError:
                        continue
        
        # If dynamic content not loaded, try direct HTML search
        if not prices:
            # Search the raw HTML for the price patterns
            html_str = str(soup)
            
            # Look for patterns like "H100 PCIe" followed by "$1.99/hr"
            h100_blocks = re.findall(r'(H100\s+(?:PCIe|SXM|NVL).*?\$[0-9.]+/hr)', html_str, re.IGNORECASE | re.DOTALL)
            
            for block in h100_blocks:
                # Extract variant
                if 'PCIe' in block or 'PCIE' in block:
                    variant = "H100 PCIe"
                elif 'SXM' in block:
                    variant = "H100 SXM"
                elif 'NVL' in block:
                    variant = "H100 NVL"
                else:
                    variant = "H100"
                
                # Extract price
                price_match = re.search(r'\$([0-9.]+)/hr', block)
                if price_match:
                    try:
                        price = float(price_match.group(1))
                        if 1.0 <= price <= 10.0 and variant not in prices:
                            prices[variant] = f"${price:.2f}/hr"
                            print(f"        HTML ✓ {variant} = ${price:.2f}/hr")
                    except ValueError:
                        continue
        
        return prices
    
    def _extract_from_embedded_json(self, html_content: str) -> Dict[str, str]:
        """Extract H100 prices from embedded JSON in HTML"""
        prices = {}
        
        # Look for JSON data embedded in script tags or data attributes
        json_patterns = [
            r'<script[^>]*>.*?({.*?gpuTypes.*?})</script>',
            r'data-gpu-types=["\']({.*?})["\']',
            r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
            r'window\.gpuData\s*=\s*({.*?});',
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                try:
                    # Try to parse as JSON
                    data = json.loads(match)
                    found_prices = self._extract_from_json(data)
                    if found_prices:
                        prices.update(found_prices)
                        return prices
                except json.JSONDecodeError:
                    continue
        
        return prices
    
    def _try_selenium_scraper(self) -> Dict[str, str]:
        """Use Selenium to scrape JavaScript-loaded pricing from RunPod"""
        h100_prices = {}
        
        try:
            print("    Setting up Selenium WebDriver...")
            
            # Configure Chrome options
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # Run in background
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # Initialize the driver
            driver = webdriver.Chrome(options=chrome_options)
            
            try:
                print("    Loading pricing page...")
                driver.get("https://www.runpod.io/pricing")
                
                # Wait for the pricing table to load (wait for elements with pricing info)
                print("    Waiting for dynamic content to load...")
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "w-dyn-item"))
                )
                
                # Additional wait to ensure prices are loaded
                time.sleep(3)
                
                # Get the page source after JavaScript has loaded
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                
                print("    ✓ Page loaded, extracting prices...")
                
                # Look for pricing items
                pricing_items = soup.find_all('div', class_=re.compile(r'w-dyn-item'))
                print(f"      Found {len(pricing_items)} pricing items")
                
                for item in pricing_items:
                    item_text = item.get_text(separator=' ', strip=True)
                    
                    # Check if this item mentions H100
                    if 'H100' in item_text or 'h100' in item_text.lower():
                        # Look for price pattern with /hr
                        price_matches = re.findall(r'\$([0-9.]+)/hr', item_text)
                        
                        for price_str in price_matches:
                            try:
                                price = float(price_str)
                                
                                # Filter for on-demand prices ($1-$10 range)
                                if 1.0 <= price <= 10.0:
                                    # Identify variant
                                    variant_name = "H100"
                                    item_upper = item_text.upper()
                                    
                                    if 'SXM' in item_upper:
                                        variant_name = "H100 SXM"
                                    elif 'PCIE' in item_upper or 'PCI-E' in item_upper:
                                        variant_name = "H100 PCIe"
                                    elif 'NVL' in item_upper:
                                        variant_name = "H100 NVL"
                                    
                                    # Skip if already added
                                    if variant_name not in h100_prices:
                                        h100_prices[variant_name] = f"${price:.2f}/hr"
                                        print(f"        Selenium ✓ {variant_name} = ${price:.2f}/hr")
                            except ValueError:
                                continue
                
                # If no prices found with structured approach, try direct text search
                if not h100_prices:
                    print("      Trying direct text search...")
                    text_content = soup.get_text()
                    
                    # Look for H100 variants with prices
                    patterns = [
                        (r'H100\s+PCIe[^\$]{0,200}\$([0-9.]+)/hr', 'H100 PCIe'),
                        (r'H100\s+SXM[^\$]{0,200}\$([0-9.]+)/hr', 'H100 SXM'),
                        (r'H100\s+NVL[^\$]{0,200}\$([0-9.]+)/hr', 'H100 NVL'),
                    ]
                    
                    for pattern, variant in patterns:
                        matches = re.findall(pattern, text_content, re.IGNORECASE | re.DOTALL)
                        for match in matches:
                            try:
                                price = float(match)
                                if 1.0 <= price <= 10.0 and variant not in h100_prices:
                                    h100_prices[variant] = f"${price:.2f}/hr"
                                    print(f"        Selenium Text ✓ {variant} = ${price:.2f}/hr")
                            except ValueError:
                                continue
                
            finally:
                driver.quit()
                print("    WebDriver closed")
                
        except WebDriverException as e:
            print(f"      ⚠️  Selenium WebDriver error: {str(e)[:100]}")
            print(f"      Make sure Chrome and ChromeDriver are installed")
        except Exception as e:
            print(f"      ⚠️  Error: {str(e)[:100]}")
        
        return h100_prices


def main():
    """Test the RunPod scraper"""
    print("🚀 RunPod H100 GPU Pricing Scraper")
    print("=" * 80)
    print()
    
    scraper = RunPodScraper()
    h100_prices = scraper.get_h100_prices()
    
    print("\n" + "=" * 80)
    print("🎯 RESULTS - RunPod H100 Pricing")
    print("=" * 80)
    
    if h100_prices and 'Error' not in h100_prices:
        print(f"\n✅ Successfully extracted {len(h100_prices)} H100 price variants:\n")
        
        for variant, price in sorted(h100_prices.items()):
            print(f"  • {variant:50s} {price}")
        
        # Save to JSON
        output_file = "runpod_h100_prices.json"
        output_data = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'provider': 'RunPod',
            'providers': {
                'RunPod': {
                    'name': 'RunPod',
                    'url': 'https://www.runpod.io',
                    'variants': {}
                }
            }
        }
        
        # Add variants
        for variant, price in h100_prices.items():
            price_match = re.search(r'\$([0-9.]+)', price)
            if price_match:
                price_num = float(price_match.group(1))
                
                # Determine if it's spot or on-demand
                availability = 'spot' if 'Spot' in variant or 'Community' in variant else 'on-demand'
                
                output_data['providers']['RunPod']['variants'][variant] = {
                    'gpu_model': 'H100',
                    'gpu_memory': '80GB',
                    'price_per_hour': price_num,
                    'currency': 'USD',
                    'availability': availability
                }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\n💾 Results saved to: {output_file}")
        
    else:
        print("\n❌ Failed to extract H100 pricing")
        if 'Error' in h100_prices:
            print(f"   Error: {h100_prices['Error']}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()

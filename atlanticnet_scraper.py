#!/usr/bin/env python3
"""
Atlantic.net H100 GPU Pricing Scraper
Extracts H100 pricing from atlantic.net
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import time
from typing import Dict, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException


class AtlanticNetScraper:
    """Scraper for Atlantic.net H100 pricing"""
    
    def __init__(self):
        self.name = "Atlantic.net"
        self.base_url = "https://www.atlantic.net"
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
            ("Selenium Scraper", self._try_selenium_scraper),  # Try Selenium first for JavaScript content
            ("Pricing Page", self._try_pricing_page),
            ("GPU Cloud Page", self._try_gpu_cloud_page),
            ("API Endpoint", self._try_api_endpoint),
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
            return {'Error': 'Unable to fetch H100 pricing from Atlantic.net'}
        
        return h100_prices
    
    def _try_pricing_page(self) -> Dict[str, str]:
        """Try to extract prices from pricing pages"""
        h100_prices = {}
        
        pricing_urls = [
            "https://www.atlantic.net/vps-hosting/pricing/",
            "https://www.atlantic.net/cloud-hosting/pricing/",
            "https://www.atlantic.net/gpu-cloud-hosting/",
            "https://www.atlantic.net/products/gpu-cloud/",
            "https://atlantic.net/vps-hosting/pricing/",
        ]
        
        for url in pricing_urls:
            try:
                print(f"    Trying: {url}")
                response = requests.get(url, headers=self.headers, timeout=20)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    text_content = soup.get_text()
                    
                    # Debug: check for GPU models
                    if 'GPU' in text_content or 'gpu' in text_content.lower():
                        print(f"      ✓ Page contains GPU references")
                        gpu_models = ['H100', 'A100', 'A40', 'RTX', 'V100']
                        found_models = [model for model in gpu_models if model in text_content]
                        if found_models:
                            print(f"      📋 Found GPU models: {', '.join(found_models)}")
                    
                    if 'H100' not in text_content and 'h100' not in text_content.lower():
                        print(f"      ⚠️  Page doesn't contain H100 references")
                        continue
                    
                    print(f"      ✓ Page contains H100 data")
                    
                    # Look for H100 pricing patterns
                    found_prices = self._extract_from_text(text_content)
                    if found_prices:
                        h100_prices.update(found_prices)
                        return h100_prices
                    
                    # Try structured extraction
                    found_prices = self._extract_from_page_structure(soup)
                    if found_prices:
                        h100_prices.update(found_prices)
                        return h100_prices
                        
                else:
                    print(f"      Status {response.status_code}")
                    
            except Exception as e:
                print(f"      Error: {str(e)[:50]}...")
                continue
        
        return h100_prices
    
    def _try_gpu_cloud_page(self) -> Dict[str, str]:
        """Try GPU-specific pages"""
        h100_prices = {}
        
        gpu_urls = [
            "https://www.atlantic.net/gpu-cloud-hosting/",
            "https://www.atlantic.net/gpu/",
            "https://www.atlantic.net/dedicated-gpu/",
        ]
        
        for url in gpu_urls:
            try:
                print(f"    Trying: {url}")
                response = requests.get(url, headers=self.headers, timeout=20)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    text_content = soup.get_text()
                    
                    if 'H100' in text_content or 'h100' in text_content.lower():
                        print(f"      ✓ Page contains H100 data")
                        
                        found_prices = self._extract_from_text(text_content)
                        if found_prices:
                            h100_prices.update(found_prices)
                            return h100_prices
                        
                        found_prices = self._extract_from_page_structure(soup)
                        if found_prices:
                            h100_prices.update(found_prices)
                            return h100_prices
                    else:
                        print(f"      ⚠️  No H100 references")
                        
            except Exception as e:
                print(f"      Error: {str(e)[:50]}...")
                continue
        
        return h100_prices
    
    def _extract_from_text(self, text_content: str) -> Dict[str, str]:
        """Extract H100 prices from text content"""
        prices = {}
        
        # Look for H100 pricing patterns
        h100_patterns = [
            # Standard patterns with /hr or /month
            (r'H100[^\$]{0,200}\$\s*([0-9.,]+)\s*(?:/hr|/hour|per hour)', 'H100'),
            (r'H100\s+(?:PCIe|SXM|NVL)[^\$]{0,200}\$\s*([0-9.,]+)\s*(?:/hr|/hour)', None),
            (r'NVIDIA\s+H100[^\$]{0,200}\$\s*([0-9.,]+)', 'H100'),
            (r'H100[^\$]{0,200}\$([0-9.,]+)', 'H100'),
        ]
        
        for pattern, default_variant in h100_patterns:
            matches = re.finditer(pattern, text_content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                try:
                    price_str = match.group(1).replace(',', '')
                    price = float(price_str)
                    
                    # Reasonable range for H100 pricing
                    if 0.5 <= price <= 50.0:
                        # Try to determine variant from context
                        context_start = max(0, match.start() - 100)
                        context_end = min(len(text_content), match.end() + 100)
                        context = text_content[context_start:context_end].upper()
                        
                        variant_name = default_variant if default_variant else "H100"
                        
                        if 'SXM' in context:
                            variant_name = "H100 SXM"
                        elif 'PCIE' in context or 'PCI-E' in context:
                            variant_name = "H100 PCIe"
                        elif 'NVL' in context:
                            variant_name = "H100 NVL"
                        
                        if variant_name not in prices:
                            prices[variant_name] = f"${price:.2f}/hr"
                            print(f"        Text ✓ {variant_name} = ${price:.2f}/hr")
                except (ValueError, IndexError):
                    continue
        
        return prices
    
    def _extract_from_page_structure(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract H100 pricing from structured HTML elements"""
        prices = {}
        
        # Look for pricing tables, cards, or sections
        elements = soup.find_all(['div', 'section', 'article', 'tr', 'li', 'td', 'span', 'p'])
        
        for elem in elements:
            elem_text = elem.get_text(separator=' ', strip=True)
            
            # Check if this element mentions H100
            if 'H100' in elem_text or 'h100' in elem_text.lower():
                # Look for price patterns
                price_matches = re.findall(r'\$([0-9.,]+)\s*(?:/hr|/hour|per hour)?', elem_text)
                
                for price_str in price_matches:
                    try:
                        price = float(price_str.replace(',', ''))
                        
                        # Filter for reasonable H100 prices
                        if 0.5 <= price <= 50.0:
                            # Identify variant
                            variant_name = "H100"
                            elem_upper = elem_text.upper()
                            
                            if 'SXM' in elem_upper:
                                variant_name = "H100 SXM"
                            elif 'PCIE' in elem_upper or 'PCI-E' in elem_upper:
                                variant_name = "H100 PCIe"
                            elif 'NVL' in elem_upper:
                                variant_name = "H100 NVL"
                            
                            # Verify it's per hour pricing
                            if any(term in elem_text.lower() for term in ['/hr', '/hour', 'per hour', 'hourly']):
                                if variant_name not in prices:
                                    prices[variant_name] = f"${price:.2f}/hr"
                                    print(f"        Element ✓ {variant_name} = ${price:.2f}/hr")
                    except ValueError:
                        continue
        
        return prices
    
    def _try_api_endpoint(self) -> Dict[str, str]:
        """Try to fetch pricing from API endpoints"""
        h100_prices = {}
        
        api_urls = [
            f"{self.base_url}/api/pricing",
            f"{self.base_url}/api/v1/pricing",
            f"{self.base_url}/api/gpu-pricing",
        ]
        
        for api_url in api_urls:
            try:
                print(f"    Trying API: {api_url}")
                response = requests.get(api_url, headers=self.headers, timeout=15)
                
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
                        
            except Exception as e:
                print(f"      Error: {str(e)[:30]}...")
                continue
        
        return h100_prices
    
    def _extract_from_json(self, data, path="") -> Dict[str, str]:
        """Recursively search JSON for H100 pricing"""
        prices = {}
        
        if isinstance(data, dict):
            for key, value in data.items():
                # Check if key or value contains H100
                if isinstance(key, str) and 'h100' in key.lower():
                    if isinstance(value, (int, float)) and 0.5 < value < 50:
                        prices['H100'] = f"${value:.2f}/hr"
                        print(f"        JSON ✓ H100 = ${value:.2f}/hr")
                        return prices
                
                # Recurse into nested structures
                if isinstance(value, (dict, list)):
                    nested_prices = self._extract_from_json(value, f"{path}.{key}")
                    if nested_prices:
                        prices.update(nested_prices)
                        return prices
                        
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    nested_prices = self._extract_from_json(item, f"{path}[{i}]")
                    if nested_prices:
                        prices.update(nested_prices)
                        return prices
        
        return prices
    
    def _try_selenium_scraper(self) -> Dict[str, str]:
        """Use Selenium to scrape JavaScript-loaded pricing from GPU server hosting page"""
        h100_prices = {}
        
        try:
            print("    Setting up Selenium WebDriver...")
            
            # Configure Chrome options
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            driver = webdriver.Chrome(options=chrome_options)
            
            try:
                # Primary URL: GPU server hosting page
                url = "https://www.atlantic.net/gpu-server-hosting/"
                print(f"    Loading: {url}")
                driver.get(url)
                
                # Wait for dynamic content to load
                print("    Waiting for content to load...")
                time.sleep(5)  # Give more time for JavaScript to execute
                
                # Try to wait for specific elements
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                except TimeoutException:
                    print("      ⚠️  Timeout waiting for page elements")
                
                # Get the page source after JavaScript has loaded
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                text_content = soup.get_text()
                
                print(f"      ✓ Page loaded successfully")
                
                # Check for H100 references
                if 'H100' in text_content or 'h100' in text_content.lower():
                    print(f"      ✓ Found H100 references")
                    
                    # Debug: Show H100 context
                    h100_matches = re.finditer(r'.{0,100}H100.{0,200}', text_content, re.IGNORECASE | re.DOTALL)
                    print(f"      🔍 H100 contexts found:")
                    for i, match in enumerate(list(h100_matches)[:3]):
                        context = match.group(0).replace('\n', ' ').strip()
                        prices_in_context = re.findall(r'\$([0-9.,]+)', context)
                        if prices_in_context:
                            print(f"         [{i+1}] {context[:120]}... → Prices: {prices_in_context}")
                    
                    # Look for pricing tables or cards
                    pricing_elements = soup.find_all(['table', 'div', 'section'], 
                                                    class_=re.compile(r'(price|pricing|plan|gpu|card)', re.I))
                    print(f"      📋 Found {len(pricing_elements)} pricing elements")
                    
                    for elem in pricing_elements:
                        elem_text = elem.get_text(separator=' ', strip=True)
                        if 'H100' in elem_text or 'h100' in elem_text.lower():
                            # Extract prices from this element
                            price_matches = re.findall(r'\$([0-9.,]+)\s*(?:/hr|/hour|per hour|hourly)?', elem_text)
                            
                            for price_str in price_matches:
                                try:
                                    price = float(price_str.replace(',', ''))
                                    
                                    # Reasonable H100 price range
                                    if 0.5 <= price <= 50.0:
                                        # Determine variant
                                        variant_name = "H100"
                                        elem_upper = elem_text.upper()
                                        
                                        if 'SXM' in elem_upper or 'SXM5' in elem_upper:
                                            variant_name = "H100 SXM"
                                        elif 'PCIE' in elem_upper or 'PCI-E' in elem_upper:
                                            variant_name = "H100 PCIe"
                                        elif 'NVL' in elem_upper:
                                            variant_name = "H100 NVL"
                                        
                                        # Check if hourly pricing
                                        if any(term in elem_text.lower() for term in ['/hr', '/hour', 'per hour', 'hourly']):
                                            if variant_name not in h100_prices:
                                                h100_prices[variant_name] = f"${price:.2f}/hr"
                                                print(f"        Selenium Element ✓ {variant_name} = ${price:.2f}/hr")
                                except ValueError:
                                    continue
                    
                    # If no prices found in structured elements, try direct text extraction
                    if not h100_prices:
                        print("      Trying direct text pattern matching...")
                        
                        # More specific patterns for Atlantic.net
                        patterns = [
                            (r'H100\s+SXM[^\$]{0,200}\$([0-9.,]+)\s*(?:/hr|/hour|per hour)', 'H100 SXM'),
                            (r'H100\s+PCIe[^\$]{0,200}\$([0-9.,]+)\s*(?:/hr|/hour|per hour)', 'H100 PCIe'),
                            (r'H100\s+NVL[^\$]{0,200}\$([0-9.,]+)\s*(?:/hr|/hour|per hour)', 'H100 NVL'),
                            (r'NVIDIA\s+H100[^\$]{0,200}\$([0-9.,]+)\s*(?:/hr|/hour|per hour)', 'H100'),
                            (r'H100[^\$]{0,150}\$([0-9.,]+)\s*/hr', 'H100'),
                        ]
                        
                        for pattern, variant in patterns:
                            matches = re.findall(pattern, text_content, re.IGNORECASE | re.DOTALL)
                            for match in matches:
                                try:
                                    price = float(match.replace(',', ''))
                                    if 0.5 <= price <= 50.0 and variant not in h100_prices:
                                        h100_prices[variant] = f"${price:.2f}/hr"
                                        print(f"        Selenium Pattern ✓ {variant} = ${price:.2f}/hr")
                                except ValueError:
                                    continue
                else:
                    print(f"      ⚠️  No H100 references found on page")
                
            finally:
                driver.quit()
                print("    WebDriver closed")
                
        except WebDriverException as e:
            print(f"      ⚠️  Selenium error: {str(e)[:80]}")
        except Exception as e:
            print(f"      ⚠️  Error: {str(e)[:80]}")
        
        return h100_prices


def main():
    """Test the Atlantic.net scraper"""
    print("🚀 Atlantic.net H100 GPU Pricing Scraper")
    print("=" * 80)
    print()
    
    scraper = AtlanticNetScraper()
    h100_prices = scraper.get_h100_prices()
    
    print("\n" + "=" * 80)
    print("🎯 RESULTS - Atlantic.net H100 Pricing")
    print("=" * 80)
    
    if h100_prices and 'Error' not in h100_prices:
        print(f"\n✅ Successfully extracted {len(h100_prices)} H100 price variants:\n")
        
        for variant, price in sorted(h100_prices.items()):
            print(f"  • {variant:50s} {price}")
        
        # Save to JSON
        output_file = "atlanticnet_h100_prices.json"
        output_data = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'provider': 'Atlantic.net',
            'providers': {
                'Atlantic.net': {
                    'name': 'Atlantic.net',
                    'url': 'https://www.atlantic.net',
                    'variants': {}
                }
            }
        }
        
        # Add variants
        for variant, price in h100_prices.items():
            price_match = re.search(r'\$([0-9.]+)', price)
            if price_match:
                price_num = float(price_match.group(1))
                output_data['providers']['Atlantic.net']['variants'][variant] = {
                    'gpu_model': 'H100',
                    'gpu_memory': '80GB',
                    'price_per_hour': price_num,
                    'currency': 'USD',
                    'availability': 'on-demand'
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

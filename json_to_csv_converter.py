#!/usr/bin/env python3
"""
Convert H100 pricing JSON files to CSV format
"""

import json
import csv
import re
from datetime import datetime

def extract_price_value(price_str):
    """Extract numeric price value from price string"""
    # Remove currency symbols and extract number
    cleaned = re.sub(r'[^\d.,]', '', price_str)
    if cleaned:
        try:
            return float(cleaned.replace(',', ''))
        except ValueError:
            return None
    return None

def get_currency_from_price(price_str):
    """Extract currency symbol from price string"""
    if '₹' in price_str:
        return 'INR'
    elif '€' in price_str:
        return 'EUR'
    elif '$' in price_str:
        return 'USD'
    else:
        return 'Unknown'

def convert_json_to_csv(json_file_path, csv_file_path):
    """Convert JSON pricing data to CSV format"""
    
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract timestamp and providers data
    timestamp = data.get('timestamp', 'Unknown')
    providers = data.get('providers', {})
    
    # Prepare CSV data
    csv_rows = []
    
    # CSV headers
    headers = [
        'Provider',
        'GPU_Variant',
        'Price_Original',
        'Price_Numeric',
        'Currency',
        'GPU_Count',
        'GPU_Type',
        'Pricing_Model',
        'Timestamp'
    ]
    
    for provider_name, gpu_variants in providers.items():
        for variant_name, price in gpu_variants.items():
            # Extract additional info from variant name
            gpu_count = 1
            gpu_type = 'H100'
            pricing_model = 'On-Demand'
            
            # Parse GPU count
            if 'x GPU' in variant_name or 'x H100' in variant_name:
                count_match = re.search(r'(\d+)x', variant_name)
                if count_match:
                    gpu_count = int(count_match.group(1))
            elif '8x GPUs' in variant_name:
                gpu_count = 8
            elif '4x GPUs' in variant_name:
                gpu_count = 4
            elif '2x GPUs' in variant_name:
                gpu_count = 2
            elif '1x GPU' in variant_name:
                gpu_count = 1
            
            # Parse GPU type
            if 'H200' in variant_name:
                gpu_type = 'H200'
            elif 'H100' in variant_name:
                gpu_type = 'H100'
            elif 'A100' in variant_name:
                gpu_type = 'A100'
            elif 'L40S' in variant_name:
                gpu_type = 'L40S'
            elif 'L4' in variant_name:
                gpu_type = 'L4'
            elif 'P100' in variant_name:
                gpu_type = 'P100'
            
            # Parse pricing model
            if 'Reserved' in variant_name or 'reserved' in variant_name:
                pricing_model = 'Reserved'
            elif 'Spot' in variant_name:
                pricing_model = 'Spot'
            elif 'Discounted' in variant_name:
                pricing_model = 'Discounted'
            elif 'Monthly' in variant_name:
                pricing_model = 'Monthly'
            
            # Extract price value and currency
            price_numeric = extract_price_value(price)
            currency = get_currency_from_price(price)
            
            csv_rows.append([
                provider_name,
                variant_name,
                price,
                price_numeric,
                currency,
                gpu_count,
                gpu_type,
                pricing_model,
                timestamp
            ])
    
    # Write to CSV
    with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        writer.writerows(csv_rows)
    
    return len(csv_rows)

def main():
    """Main function to convert both JSON files"""
    
    # Convert first JSON file (newer one with 36 providers)
    json_file1 = '/home/jonraza15/root/scraper/multi_cloud_h100_prices-Jon.json'
    csv_file1 = '/home/jonraza15/root/scraper/h100_prices_36_providers.csv'
    
    # Convert second JSON file (older one with 14 providers)
    json_file2 = '/home/jonraza15/root/scraper/multi_cloud_h100_prices.json'
    csv_file2 = '/home/jonraza15/root/scraper/h100_prices_14_providers.csv'
    
    try:
        # Convert first file
        rows1 = convert_json_to_csv(json_file1, csv_file1)
        print(f"✅ Converted {json_file1} to {csv_file1}")
        print(f"   Total rows: {rows1}")
        
        # Convert second file
        rows2 = convert_json_to_csv(json_file2, csv_file2)
        print(f"✅ Converted {json_file2} to {csv_file2}")
        print(f"   Total rows: {rows2}")
        
        # Create combined CSV file
        combined_csv = '/home/jonraza15/root/scraper/h100_prices_combined.csv'
        
        with open(combined_csv, 'w', newline='', encoding='utf-8') as combined_file:
            writer = csv.writer(combined_file)
            
            # Write headers
            headers = [
                'Provider',
                'GPU_Variant',
                'Price_Original',
                'Price_Numeric',
                'Currency',
                'GPU_Count',
                'GPU_Type',
                'Pricing_Model',
                'Timestamp',
                'Source_File'
            ]
            writer.writerow(headers)
            
            # Read and combine both CSV files
            for csv_file, source_label in [(csv_file1, 'File_1_36_providers'), (csv_file2, 'File_2_14_providers')]:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    next(reader)  # Skip header
                    for row in reader:
                        row.append(source_label)  # Add source file identifier
                        writer.writerow(row)
        
        print(f"✅ Created combined file: {combined_csv}")
        print(f"   Total combined rows: {rows1 + rows2}")
        
    except Exception as e:
        print(f"❌ Error during conversion: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()

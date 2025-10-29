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

def convert_azure_json_to_csv(json_file_path, csv_file_path):
    """Convert Azure JSON pricing data to CSV format"""
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    timestamp = data.get('timestamp', 'Unknown')
    provider = data.get('provider', 'Microsoft Azure')
    prices = data.get('prices', {})
    
    csv_rows = []
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
    
    for variant_name, price in prices.items():
        if variant_name == 'Error':
            continue
            
        gpu_count = 1
        if '8x GPUs' in variant_name:
            gpu_count = 8
        elif '4x GPUs' in variant_name:
            gpu_count = 4
        elif '2x GPUs' in variant_name:
            gpu_count = 2
        elif '1x GPU' in variant_name:
            gpu_count = 1
        
        price_numeric = extract_price_value(price)
        currency = get_currency_from_price(price)
        
        csv_rows.append([
            provider,
            variant_name,
            price,
            price_numeric,
            currency,
            gpu_count,
            'H100',
            'On-Demand',
            timestamp
        ])
    
    with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        writer.writerows(csv_rows)
    
    return len(csv_rows)

def convert_runpod_json_to_csv(json_file_path, csv_file_path):
    """Convert RunPod JSON pricing data to CSV format"""
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    timestamp = data.get('timestamp', 'Unknown')
    providers_data = data.get('providers', {})
    
    csv_rows = []
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
    
    for provider_name, provider_info in providers_data.items():
        variants = provider_info.get('variants', {})
        
        for variant_name, variant_data in variants.items():
            price_per_hour = variant_data.get('price_per_hour', 0)
            currency = variant_data.get('currency', 'USD')
            availability = variant_data.get('availability', 'on-demand')
            gpu_model = variant_data.get('gpu_model', 'H100')
            
            pricing_model = 'Spot' if 'spot' in availability.lower() else 'On-Demand'
            
            price_str = f"${price_per_hour}/hr"
            
            csv_rows.append([
                provider_name,
                variant_name,
                price_str,
                price_per_hour,
                currency,
                1,
                gpu_model,
                pricing_model,
                timestamp
            ])
    
    with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        writer.writerows(csv_rows)
    
    return len(csv_rows)

def convert_aws_json_to_csv(json_file_path, csv_file_path):
    """Convert AWS JSON pricing data to CSV format"""
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    timestamp = data.get('timestamp', 'Unknown')
    provider = data.get('provider', 'Amazon Web Services')
    prices = data.get('prices', {})
    
    csv_rows = []
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
    
    for variant_name, price in prices.items():
        if variant_name == 'Error':
            continue
            
        gpu_count = 8  # Default for p5 instances
        if 'p5.48xlarge' in variant_name:
            gpu_count = 8
        elif 'p5.24xlarge' in variant_name:
            gpu_count = 4
        elif 'p5.12xlarge' in variant_name:
            gpu_count = 2
        elif 'p5.6xlarge' in variant_name:
            gpu_count = 1
        
        price_numeric = extract_price_value(price)
        currency = get_currency_from_price(price)
        
        csv_rows.append([
            provider,
            variant_name,
            price,
            price_numeric,
            currency,
            gpu_count,
            'H100',
            'On-Demand',
            timestamp
        ])
    
    with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        writer.writerows(csv_rows)
    
    return len(csv_rows)

def main():
    """Main function to convert all JSON files"""
    
    # Define all JSON files to convert
    json_files = [
        ('multi_cloud_h100_prices-Jon.json', 'h100_prices_36_providers.csv', 'File_1_36_providers', convert_json_to_csv),
        ('multi_cloud_h100_prices.json', 'h100_prices_14_providers.csv', 'File_2_14_providers', convert_json_to_csv),
        ('azure_h100_prices_fixed.json', 'h100_prices_azure.csv', 'File_3_Azure', convert_azure_json_to_csv),
        ('runpod_h100_prices.json', 'h100_prices_runpod.csv', 'File_4_RunPod', convert_runpod_json_to_csv),
        ('aws_p5_h100_prices.json', 'h100_prices_aws.csv', 'File_5_AWS', convert_aws_json_to_csv),
    ]
    
    converted_files = []
    total_rows = 0
    
    try:
        # Convert each file
        for json_file, csv_file, source_label, converter_func in json_files:
            try:
                rows = converter_func(json_file, csv_file)
                print(f"✅ Converted {json_file} to {csv_file}")
                print(f"   Total rows: {rows}")
                converted_files.append((csv_file, source_label))
                total_rows += rows
            except FileNotFoundError:
                print(f"⚠️  Skipping {json_file} (file not found)")
            except Exception as e:
                print(f"❌ Error converting {json_file}: {e}")
        
        # Create combined CSV file
        combined_csv = 'h100_prices_combined.csv'
        
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
            
            # Read and combine all CSV files
            for csv_file, source_label in converted_files:
                try:
                    with open(csv_file, 'r', encoding='utf-8') as f:
                        reader = csv.reader(f)
                        next(reader)  # Skip header
                        for row in reader:
                            row.append(source_label)  # Add source file identifier
                            writer.writerow(row)
                except FileNotFoundError:
                    print(f"⚠️  Skipping {csv_file} in combination (file not found)")
        
        print(f"\n✅ Created combined file: {combined_csv}")
        print(f"   Total combined rows: {total_rows}")
        
    except Exception as e:
        print(f"❌ Error during conversion: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()

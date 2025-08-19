#!/usr/bin/env python3
"""
Convert H100 pricing data currencies to USD
"""

import pandas as pd
import re
import requests
from datetime import datetime

def get_live_exchange_rates():
    """
    Fetch live exchange rates from a free API
    Returns EUR to USD and INR to USD rates
    """
    try:
        # Get EUR to USD
        eur_response = requests.get("https://api.frankfurter.app/latest?from=EUR&to=USD", timeout=10)
        eur_data = eur_response.json()
        eur_to_usd = eur_data["rates"]["USD"]
        
        # Get INR to USD
        inr_response = requests.get("https://api.frankfurter.app/latest?from=INR&to=USD", timeout=10)
        inr_data = inr_response.json()
        inr_to_usd = inr_data["rates"]["USD"]
        
        print(f"✅ Live exchange rates fetched:")
        print(f"   EUR → USD: {eur_to_usd}")
        print(f"   INR → USD: {inr_to_usd}")
        
        return eur_to_usd, inr_to_usd
    
    except Exception as e:
        print(f"⚠️  Failed to fetch live rates, using fallback rates: {e}")
        # Fallback rates (approximate)
        return 1.08, 0.012  # EUR->USD, INR->USD

def extract_price_and_currency(price_str):
    """
    Extract numeric price and currency from price string
    Handles complex formats like "€22.04 (€2.76/GPU)"
    """
    if pd.isna(price_str):
        return None, None
    
    price_str = str(price_str).strip()
    
    # Handle special case: "€22.04 (€2.76/GPU)" - extract the per-GPU price
    per_gpu_match = re.search(r'\(([€$₹])([0-9,]+\.?[0-9]*)/GPU\)', price_str)
    if per_gpu_match:
        currency_symbol = per_gpu_match.group(1)
        price_num = float(per_gpu_match.group(2).replace(',', ''))
        currency = 'EUR' if currency_symbol == '€' else 'USD' if currency_symbol == '$' else 'INR'
        return price_num, currency
    
    # Pattern for price with currency symbols
    currency_patterns = [
        (r'[$]([0-9,]+\.?[0-9]*)', 'USD'),
        (r'[€]([0-9,]+\.?[0-9]*)', 'EUR'),
        (r'[₹]([0-9,]+\.?[0-9]*)', 'INR'),
        (r'([0-9,]+\.?[0-9]*)\s*USD', 'USD'),
        (r'([0-9,]+\.?[0-9]*)\s*EUR', 'EUR'),
        (r'([0-9,]+\.?[0-9]*)\s*INR', 'INR'),
        (r'([0-9,]+\.?[0-9]*)', 'USD')  # Default to USD if no currency found
    ]
    
    for pattern, currency in currency_patterns:
        match = re.search(pattern, price_str, re.IGNORECASE)
        if match:
            price_num = float(match.group(1).replace(',', ''))
            return price_num, currency
    
    return None, None

def convert_to_usd(price_numeric, currency, eur_to_usd, inr_to_usd):
    """Convert price to USD based on currency"""
    if pd.isna(price_numeric) or currency == 'USD':
        return price_numeric
    elif currency == 'EUR':
        return round(price_numeric * eur_to_usd, 4)
    elif currency == 'INR':
        return round(price_numeric * inr_to_usd, 4)
    else:
        return price_numeric  # Return as-is if unknown currency

def convert_currencies_to_usd(csv_file_path, output_file_path):
    """
    Convert all currencies in H100 pricing data to USD
    """
    print(f"🔄 Loading data from {csv_file_path}")
    
    # Load the data
    df = pd.read_csv(csv_file_path)
    print(f"   Loaded {len(df)} records")
    
    # Get live exchange rates
    eur_to_usd, inr_to_usd = get_live_exchange_rates()
    
    # Create a copy for processing
    df_converted = df.copy()
    
    print("\n💱 Converting currencies to USD...")
    
    # Fix any missing price/currency data first
    fixed_count = 0
    for idx, row in df_converted.iterrows():
        if pd.isna(row['Price_Numeric']) or pd.isna(row['Currency']):
            price_num, currency = extract_price_and_currency(row['Price_Original'])
            if price_num is not None:
                df_converted.at[idx, 'Price_Numeric'] = price_num
                fixed_count += 1
            if currency is not None:
                df_converted.at[idx, 'Currency'] = currency
    
    if fixed_count > 0:
        print(f"   Fixed {fixed_count} missing price/currency values")
    
    # Add USD converted price column
    df_converted['Price_USD'] = df_converted.apply(
        lambda row: convert_to_usd(row['Price_Numeric'], row['Currency'], eur_to_usd, inr_to_usd), 
        axis=1
    )
    
    # Count conversions by currency
    usd_count = len(df_converted[df_converted['Currency'] == 'USD'])
    eur_count = len(df_converted[df_converted['Currency'] == 'EUR'])
    inr_count = len(df_converted[df_converted['Currency'] == 'INR'])
    
    print(f"   ✅ Converted {eur_count} EUR prices to USD")
    print(f"   ✅ Converted {inr_count} INR prices to USD")
    print(f"   ✅ {usd_count} prices were already in USD")
    
    # Add conversion metadata
    df_converted['EUR_to_USD_Rate'] = eur_to_usd
    df_converted['INR_to_USD_Rate'] = inr_to_usd
    df_converted['Conversion_Date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Save to CSV
    df_converted.to_csv(output_file_path, index=False)
    print(f"\n💾 Currency converted dataset saved to: {output_file_path}")
    
    # Show summary
    print(f"\n📊 Summary:")
    print(f"   Total records: {len(df_converted)}")
    print(f"   Price range (USD): ${df_converted['Price_USD'].min():.4f} - ${df_converted['Price_USD'].max():.2f}")
    print(f"   Median price (USD): ${df_converted['Price_USD'].median():.2f}")
    
    return df_converted

def main():
    """Main function"""
    print("� H100 GPU Pricing Currency Converter")
    print("=" * 45)
    
    # File paths
    input_file = '/home/jonraza15/root/scraper/h100_prices_combined.csv'
    output_file = '/home/jonraza15/root/scraper/h100_prices_usd.csv'
    
    try:
        # Convert currencies
        df_converted = convert_currencies_to_usd(input_file, output_file)
        
        print("\n🎉 Currency conversion completed successfully!")
        print(f"📁 Output file: {output_file}")
        
    except FileNotFoundError:
        print(f"❌ Error: Input file not found: {input_file}")
        print("   Please ensure the combined CSV file exists.")
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()

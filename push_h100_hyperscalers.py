#!/usr/bin/env python3
"""
Push H100 Hyperscaler Prices to Supabase

This script reads the H100 hyperscaler prices from provider_averages.csv
and pushes them to the Supabase h100_hyperscaler_prices table.

Usage:
    python push_h100_hyperscalers.py

Environment Variables Required (set in .env file):
    SUPABASE_URL - Your Supabase project URL
    SUPABASE_SERVICE_KEY - Your Supabase service role key (for write access)
"""

import os
import sys
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv not installed, using environment variables directly")


# Hyperscaler configuration (same as gpu_index_calculator.py)
HYPERSCALERS = {
    'Amazon Web Services': {
        'weight': 18.28,
        'discount': 44,  # 44% discount
    },
    'Microsoft Azure': {
        'weight': 23.54,
        'discount': 65,  # 65% discount
    },
    'Google Cloud': {
        'weight': 10.28,
        'discount': 65,  # 65% discount
    },
    'CoreWeave': {
        'weight': 3.74,
        'discount': 50,  # 50% discount
    },
}


def load_provider_prices(filepath: str = "provider_averages.csv") -> Optional[pd.DataFrame]:
    """Load provider prices from CSV file"""
    try:
        df = pd.read_csv(filepath)
        print(f"✅ Loaded {len(df)} providers from {filepath}")
        return df
    except FileNotFoundError:
        print(f"❌ Error: {filepath} not found!")
        print(f"   Please run the scrapers first to generate provider data.")
        return None
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return None


def extract_hyperscaler_prices(df: pd.DataFrame) -> List[Dict]:
    """Extract hyperscaler prices from provider data"""
    hyperscaler_records = []
    timestamp = datetime.now().isoformat()
    
    print(f"\n📊 Extracting H100 hyperscaler prices...")
    
    for provider_name, config in HYPERSCALERS.items():
        # Find provider in CSV data
        provider_data = df[df['Provider'] == provider_name]
        
        if not provider_data.empty:
            original_price = float(provider_data['AvgNormalizedPrice'].iloc[0])
            discount_rate = config['discount'] / 100
            weight = config['weight']
            
            # Calculate effective price after discount
            effective_price = original_price * (1 - discount_rate)
            
            # Calculate weighted contribution
            weighted_contribution = effective_price * (weight / 100)
            
            record = {
                'timestamp': timestamp,
                'provider_name': provider_name,
                'original_price': round(original_price, 4),
                'effective_price': round(effective_price, 4),
                'discount_rate': round(discount_rate * 100, 2),  # Store as percentage
                'weight': round(weight, 2),
                'weighted_contribution': round(weighted_contribution, 6),
            }
            hyperscaler_records.append(record)
            print(f"   ✓ {provider_name}: ${original_price:.2f} → ${effective_price:.2f} (after {config['discount']}% discount)")
        else:
            print(f"   ⚠️ {provider_name}: Not found in CSV data")
    
    return hyperscaler_records


def push_to_supabase(records: List[Dict]) -> bool:
    """Push hyperscaler records to Supabase"""
    
    # Get Supabase credentials from environment
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Error: Supabase credentials not found!")
        print("   Please set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables.")
        print("\n   Example:")
        print("   export SUPABASE_URL='https://your-project.supabase.co'")
        print("   export SUPABASE_SERVICE_KEY='your-service-role-key'")
        return False
    
    try:
        from supabase import create_client, Client
    except ImportError:
        print("❌ Error: supabase-py library not installed!")
        print("   Install it with: pip install supabase")
        return False
    
    try:
        # Initialize Supabase client
        supabase: Client = create_client(supabase_url, supabase_key)
        
        print(f"\n📤 Pushing {len(records)} hyperscaler prices to Supabase...")
        
        # Insert records
        response = supabase.table('h100_hyperscaler_prices').insert(records).execute()
        
        if response.data:
            print(f"\n✅ Successfully pushed {len(response.data)} hyperscaler prices!")
            
            # Print summary
            print(f"\n📋 Summary:")
            for record in response.data:
                print(f"   • {record['provider_name']}: ${record['effective_price']:.2f}/hr")
            
            return True
        else:
            print(f"\n❌ Error: No data returned from Supabase")
            return False
            
    except Exception as e:
        print(f"\n❌ Error pushing to Supabase: {e}")
        import traceback
        traceback.print_exc()
        return False


def display_latest_prices() -> None:
    """Display the latest prices from Supabase (optional verification)"""
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not supabase_url or not supabase_key:
        return
    
    try:
        from supabase import create_client, Client
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Get latest prices for each provider
        response = supabase.table('h100_hyperscaler_prices')\
            .select('*')\
            .order('timestamp', desc=True)\
            .limit(4)\
            .execute()
        
        if response.data:
            print(f"\n📊 Latest Entries in Supabase:")
            for record in response.data:
                print(f"   {record['provider_name']}: ${record['effective_price']}/hr @ {record['timestamp'][:19]}")
    except Exception as e:
        print(f"   (Could not fetch latest: {e})")


def main():
    print("🚀 H100 Hyperscaler Prices → Supabase")
    print("=" * 60)
    
    # Load provider data
    df = load_provider_prices()
    if df is None:
        sys.exit(1)
    
    # Extract hyperscaler prices
    records = extract_hyperscaler_prices(df)
    
    if not records:
        print("\n❌ No hyperscaler prices found!")
        sys.exit(1)
    
    # Push to Supabase
    success = push_to_supabase(records)
    
    if success:
        display_latest_prices()
        print("\n✅ H100 hyperscaler prices successfully uploaded to Supabase!")
    else:
        print("\n❌ Failed to push to Supabase")
        sys.exit(1)


if __name__ == "__main__":
    main()

import pandas as pd
import numpy as np

# Load provider averages data
df = pd.read_csv("provider_averages.csv")

def filter_outliers(df, price_column='AvgNormalizedPrice', method='iqr', multiplier=3.0):
    """
    Filter out extreme price outliers dynamically
    
    Args:
        df: DataFrame with provider data
        price_column: Column name containing prices
        method: 'iqr' for interquartile range or 'std' for standard deviation
        multiplier: How many IQRs or standard deviations to use as threshold
    
    Returns:
        DataFrame with outliers removed and list of excluded providers
    """
    prices = df[price_column].dropna()
    
    if method == 'iqr':
        Q1 = prices.quantile(0.25)
        Q3 = prices.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - multiplier * IQR
        upper_bound = Q3 + multiplier * IQR
    elif method == 'std':
        mean_price = prices.mean()
        std_price = prices.std()
        lower_bound = mean_price - multiplier * std_price
        upper_bound = mean_price + multiplier * std_price
    else:
        raise ValueError("Method must be 'iqr' or 'std'")
    
    # Identify outliers
    outlier_mask = (df[price_column] < lower_bound) | (df[price_column] > upper_bound)
    outliers = df[outlier_mask]['Provider'].tolist()
    
    # Filter out outliers
    filtered_df = df[~outlier_mask].copy()
    
    return filtered_df, outliers, lower_bound, upper_bound

# Provider weights (out of 40% total for non-hyperscalers)
provider_weights = {
    'Voltage Park': 7.09,
    'VoltagePark': 7.09,  # Alternative name
    'Nebius': 5.01,
    'ShaktiCloud': 3.87,
    'Shakti Cloud': 3.87,  # Alternative name
    'TaigaCloud': 3.75,
    'Lambda Labs': 4.00,
    'Crusoe': 1.60,
    'HyperStack': 1.42,
    'FluidStack': 1.40,
    'Ori': 1.31,
    'ORI': 1.31,  # Alternative name
    'Scaleway': 0.50,
    'OVHcloud': 0.52,
    'OVH Cloud': 0.52,  # Alternative name
    'GMICloud': 0.54,
    'GMI Cloud': 0.54,  # Alternative name
    'Leaseweb': 0.40,
    'Gcore': 0.37,
    'HydraHost': 0.37,
    'Neysa.ai': 0.28,
    'Fal.AI': 0.30,
    'Baseten': 0.26,
    'EdgeVana': 0.21,
    'Replicate': 0.19,
    'AceCloud': 0.19,
    'Ace Cloud': 0.19,  # Alternative name
    'Massed Compute': 0.19,
    'Civo': 0.12,
    'GPU-Mart': 0.11,
    'Atlantic.Net': 0.09,
    'Vast.ai': 0.07,
    'RunPod': 0.07,
    'Hostkey': 0.03,
    'CUDO Compute': 0.04,
    'DataCrunch': 0.04,
    'LeaderGPU': 0.06,
    'AtlasCloud': 0.06,
    'Qubrid': 0.02,
    'Koyeb': 0.02,
    'JarvisLabs': 0.0035,
}

# Hyperscaler data (60% total weight)
hyperscalers = {
    'Amazon Web Services': {
        'weight': 18.28,
        'buyers_getting_discount': 100,
        'discount': 44,
        'website_price': None,  # Will use from CSV
        'research_price': None  # Will use from CSV
    },
    'Microsoft Azure': {
        'weight': 23.54,
        'buyers_getting_discount': 65,
        'discount': 65,
        'website_price': 18.8,
        'research_price': 6.2
    },
    'Google Cloud': {
        'weight': 10.28,
        'buyers_getting_discount': 65,
        'discount': 65,
        'website_price': 10.0,
        'research_price': 4.0
    },
    'CoreWeave': {
        'weight': 3.74,
        'buyers_getting_discount': 80,
        'discount': 50,
        'website_price': 6.155,
        'research_price': 3.0
    },
}

# Filter out extreme outliers before processing, but preserve hyperscalers
print("Filtering extreme price outliers...")

# Get list of hyperscaler names for protection
hyperscaler_names = list(hyperscalers.keys())

# Filter outliers from non-hyperscalers only
non_hyperscaler_df = df[~df['Provider'].isin(hyperscaler_names)]
hyperscaler_df = df[df['Provider'].isin(hyperscaler_names)]

if not non_hyperscaler_df.empty:
    df_filtered, excluded_providers, lower_bound, upper_bound = filter_outliers(
        non_hyperscaler_df, 
        price_column='AvgNormalizedPrice', 
        method='iqr',  # Use IQR method
        multiplier=2.5  # Slightly more aggressive filtering
    )
    
    # Combine filtered non-hyperscalers with all hyperscalers
    df = pd.concat([hyperscaler_df, df_filtered], ignore_index=True)
    
    print(f"Price range after outlier filtering: ${lower_bound:.4f} - ${upper_bound:.4f}")
    if excluded_providers:
        print(f"Excluded outlier providers: {', '.join(excluded_providers)}")
    else:
        print("No non-hyperscaler outliers detected")
    print(f"Protected hyperscalers: {', '.join(hyperscaler_names)}")
else:
    excluded_providers = []
    print("No non-hyperscaler data to filter")

print()

def calculate_weighted_index():
    total_weighted_price = 0
    total_weight = 0
    
    # Separate calculations for different index types
    hyperscaler_weighted_price = 0
    hyperscaler_weight = 0
    non_hyperscaler_weighted_price = 0
    non_hyperscaler_weight = 0
    
    print("H100 GPU Index Price Calculation")
    print("=" * 60)
    
    # Process hyperscalers
    print("\nHYPERSCALERS:")
    print("-" * 40)
    
    for provider, data in hyperscalers.items():
        # Find provider in CSV data
        provider_data = df[df['Provider'] == provider]
        
        if not provider_data.empty:
            raw_price = provider_data['AvgNormalizedPrice'].iloc[0]
            weight = data['weight']
            buyers_discount_pct = data['buyers_getting_discount'] / 100
            discount_pct = data['discount'] / 100

            # Fallback hierarchy: CSV price -> website_price -> research_price
            base_price = raw_price
            used_fallback = None
            if pd.isna(base_price):
                if data.get('website_price') is not None:
                    base_price = data['website_price']
                    used_fallback = 'website_price'
                elif data.get('research_price') is not None:
                    base_price = data['research_price']
                    used_fallback = 'research_price'

            # If still NaN or None, skip to avoid poisoning totals
            if base_price is None or pd.isna(base_price):
                print(f"{provider:20} | Weight: {weight:6.2f}% | Price: NaN | SKIPPED (no usable price)")
                continue

            # Calculate effective discounted weighted contribution
            discounted_portion = weight * buyers_discount_pct * (1 - discount_pct) * base_price
            non_discounted_portion = (weight - (weight * buyers_discount_pct)) * base_price
            effective_weighted_price = discounted_portion + non_discounted_portion

            # Guard against accidental NaN after math
            if pd.isna(effective_weighted_price):
                print(f"{provider:20} | Weight: {weight:6.2f}% | Price produced NaN after calc | SKIPPED")
                continue

            total_weighted_price += effective_weighted_price
            total_weight += weight

            hyperscaler_weighted_price += effective_weighted_price
            hyperscaler_weight += weight

            if used_fallback:
                print(f"{provider:20} | Weight: {weight:6.2f}% | Price: ${base_price:6.4f} (fallback:{used_fallback}) | "
                      f"Discount: {data['discount']:2d}% | Weighted: ${effective_weighted_price:8.4f}")
            else:
                print(f"{provider:20} | Weight: {weight:6.2f}% | Price: ${base_price:6.4f} | "
                      f"Discount: {data['discount']:2d}% | Weighted: ${effective_weighted_price:8.4f}")
        else:
            print(f"{provider:20} | NOT FOUND IN DATA")
    
    # Process other providers
    print(f"\nOTHER PROVIDERS:")
    print("-" * 40)
    
    for _, row in df.iterrows():
        provider = row['Provider']
        
        # Skip if already processed as hyperscaler
        if provider in hyperscalers:
            continue
            
        # Get weight for this provider
        weight = provider_weights.get(provider, 0)
        
        if weight > 0:
            price = row['AvgNormalizedPrice']
            # Skip providers with NaN prices
            if pd.isna(price):
                print(f"{provider:20} | Weight: {weight:6.2f}% | Price: NaN | SKIPPED (no pricing data)")
                continue
                
            weighted_price = weight * price
            
            total_weighted_price += weighted_price
            total_weight += weight
            
            # Add to non-hyperscaler calculations
            non_hyperscaler_weighted_price += weighted_price
            non_hyperscaler_weight += weight
            
            print(f"{provider:20} | Weight: {weight:6.2f}% | Price: ${price:6.4f} | "
                  f"Weighted: ${weighted_price:8.4f}")
        else:
            print(f"{provider:20} | NO WEIGHT ASSIGNED")
    
    # Check for providers that have weights but were filtered out as outliers
    if excluded_providers:
        print(f"\nEXCLUDED OUTLIERS:")
        print("-" * 40)
        for provider in excluded_providers:
            weight = provider_weights.get(provider, 0)
            if weight > 0:
                # Find original price in unfiltered data
                original_data = pd.read_csv("provider_averages.csv")
                original_price = original_data[original_data['Provider'] == provider]['AvgNormalizedPrice'].iloc[0]
                print(f"{provider:20} | Weight: {weight:6.2f}% | Price: ${original_price:6.4f} | "
                      f"EXCLUDED (outlier)")
            else:
                original_data = pd.read_csv("provider_averages.csv")
                if provider in original_data['Provider'].values:
                    original_price = original_data[original_data['Provider'] == provider]['AvgNormalizedPrice'].iloc[0]
                    print(f"{provider:20} | NO WEIGHT ASSIGNED | Price: ${original_price:6.4f} | "
                          f"EXCLUDED (outlier)")
    
    # Calculate final index prices
    if total_weight > 0:
        final_index_price = total_weighted_price / total_weight
    else:
        final_index_price = 0
        
    if hyperscaler_weight > 0:
        hyperscaler_only_price = hyperscaler_weighted_price / hyperscaler_weight
    else:
        hyperscaler_only_price = 0
        
    if non_hyperscaler_weight > 0:
        non_hyperscaler_only_price = non_hyperscaler_weighted_price / non_hyperscaler_weight
    else:
        non_hyperscaler_only_price = 0
    
    print("\n" + "=" * 60)
    print(f"SUMMARY:")
    print(f"Total Weight Used: {total_weight:.2f}%")
    print(f"Total Weighted Price: ${total_weighted_price:.4f}")
    print("\n" + "=" * 60)
    print("INDEX PRICE CALCULATIONS:")
    print("=" * 60)
    print(f"1. FULL INDEX (Hyperscalers + Non-Hyperscalers):")
    print(f"   Weight: {total_weight:.2f}% | Price: ${final_index_price:.4f}/hour")
    print(f"\n2. HYPERSCALERS ONLY:")
    print(f"   Weight: {hyperscaler_weight:.2f}% | Price: ${hyperscaler_only_price:.4f}/hour")
    print(f"\n3. NON-HYPERSCALERS ONLY:")
    print(f"   Weight: {non_hyperscaler_weight:.2f}% | Price: ${non_hyperscaler_only_price:.4f}/hour")
    print("=" * 60)
    
    # Save results to file with all three prices
    results = {
        'Total_Weight_Percent': total_weight,
        'Total_Weighted_Price': total_weighted_price,
        'Full_Index_Price': final_index_price,
        'Hyperscalers_Only_Price': hyperscaler_only_price,
        'Non_Hyperscalers_Only_Price': non_hyperscaler_only_price,
        'Hyperscaler_Weight': hyperscaler_weight,
        'Non_Hyperscaler_Weight': non_hyperscaler_weight,
        'Calculation_Date': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    results_df = pd.DataFrame([results])
    results_df.to_csv("h100_gpu_index.csv", index=False)
    
    print(f"\nResults saved to: h100_gpu_index.csv")
    
    return final_index_price, hyperscaler_only_price, non_hyperscaler_only_price

if __name__ == "__main__":
    full_price, hyperscaler_price, non_hyperscaler_price = calculate_weighted_index()

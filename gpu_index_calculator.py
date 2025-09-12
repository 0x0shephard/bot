import pandas as pd
import numpy as np
import os
import subprocess
from typing import Tuple, Optional, List

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

HISTORY_FILE = "gpu_index_history.csv"
HISTORY_COLUMNS = [
    'timestamp',
    'full_index_price',
    'hyperscalers_only_price',
    'non_hyperscalers_only_price',
    'source'  # calculated | rerun | fallback_avg
]

def load_price_history(n: Optional[int] = None) -> pd.DataFrame:
    """Load the price history file if it exists.

    Args:
        n: If provided, return only the last n rows.
    """
    if not os.path.exists(HISTORY_FILE):
        return pd.DataFrame(columns=HISTORY_COLUMNS)
    df_hist = pd.read_csv(HISTORY_FILE)
    # Ensure columns (in case of older format)
    for col in HISTORY_COLUMNS:
        if col not in df_hist.columns:
            df_hist[col] = np.nan
    if n is not None:
        return df_hist.tail(n).reset_index(drop=True)
    return df_hist

def append_price_history(full_price: float, hyperscaler_price: float, non_hyperscaler_price: float, source: str):
    """Append a new record to the history file."""
    record = {
        'timestamp': pd.Timestamp.now().isoformat(),
        'full_index_price': full_price,
        'hyperscalers_only_price': hyperscaler_price,
        'non_hyperscalers_only_price': non_hyperscaler_price,
        'source': source
    }
    mode = 'a' if os.path.exists(HISTORY_FILE) else 'w'
    header = not os.path.exists(HISTORY_FILE)
    pd.DataFrame([record]).to_csv(HISTORY_FILE, mode=mode, header=header, index=False)

def get_last_price() -> Optional[float]:
    hist = load_price_history()
    if hist.empty:
        return None
    val = hist['full_index_price'].dropna()
    if val.empty:
        return None
    return float(val.iloc[-1])

def average_last_n_prices(n: int = 10) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    hist = load_price_history(n)
    if hist.empty:
        return None, None, None
    return (
        float(hist['full_index_price'].dropna().mean()) if not hist['full_index_price'].dropna().empty else None,
        float(hist['hyperscalers_only_price'].dropna().mean()) if not hist['hyperscalers_only_price'].dropna().empty else None,
        float(hist['non_hyperscalers_only_price'].dropna().mean()) if not hist['non_hyperscalers_only_price'].dropna().empty else None,
    )

def significant_change(new: float, old: float, threshold: float = 0.5) -> bool:
    if old is None:
        return False
    if old == 0:
        return False
    change = abs(new - old) / old
    return change >= threshold

def run_cmd(cmd: list) -> Tuple[int, str, str]:
    """Run a shell command and return (code, stdout, stderr)."""
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, err = proc.communicate()
        return proc.returncode, out.strip(), err.strip()
    except Exception as e:
        return 1, '', str(e)

def ensure_git_identity():
    """Ensure git user identity is configured (actions bot fallback)."""
    code, out, _ = run_cmd(["git", "config", "user.email"])
    if code != 0 or not out:
        run_cmd(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"]) 
    code, out, _ = run_cmd(["git", "config", "user.name"])
    if code != 0 or not out:
        run_cmd(["git", "config", "user.name", "github-actions[bot]"]) 

TRIGGER_MARKER = ".price_change_triggered"

def already_triggered_this_run() -> bool:
    return os.path.exists(TRIGGER_MARKER)

def mark_triggered():
    with open(TRIGGER_MARKER, 'w') as f:
        f.write(pd.Timestamp.now().isoformat())

def attempt_trigger_commit(last_price: float, new_price: float):
    """
    Commit & push a marker + updated history to trigger workflow re-run when
    a significant move (>=50%) is confirmed via rerun. Safeguards:
      - Only inside GitHub Actions (env GITHUB_ACTIONS == 'true')
      - Only once per run (marker file)
    """
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        return False
    if not significant_change(new_price, last_price):
        return False
    if already_triggered_this_run():
        return False

    ensure_git_identity()
    # Create a human-readable log
    msg_lines = [
        f"Timestamp: {pd.Timestamp.now().isoformat()}",
        f"Previous full index price: {last_price}",
        f"New full index price: {new_price}",
        f"Relative change: {abs(new_price - last_price)/last_price:.2%}",
        "Reason: >=50% movement detected; committing to trigger follow-up run."
    ]
    with open('significant_change.log', 'w') as f:
        f.write('\n'.join(msg_lines) + '\n')

    mark_triggered()

    # Stage files (history + marker + log)
    run_cmd(["git", "add", HISTORY_FILE, "significant_change.log", TRIGGER_MARKER])
    commit_message = f"trigger: significant GPU index move {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
    code, _, err = run_cmd(["git", "commit", "-m", commit_message])
    if code != 0:
        # Probably nothing changed beyond history that was already committed earlier
        return False
    # Push
    run_cmd(["git", "push", "origin", "main"])  # Relying on GITHUB_TOKEN credentials injected by Actions
    print("Pushed trigger commit to remote (significant change detected).")
    return True

if __name__ == "__main__":
    # First calculation
    full_price, hyperscaler_price, non_hyperscaler_price = calculate_weighted_index()
    last_price = get_last_price()
    reran = False
    final_source = 'calculated'

    # If the first pass produced zero/NaN, attempt an immediate rerun before other logic
    if (full_price is None) or pd.isna(full_price) or full_price == 0:
        print("First pass produced zero/NaN full index price. Re-running calculation for recovery...")
        full_price2, hyperscaler_price2, non_hyperscaler_price2 = calculate_weighted_index()
        if full_price2 and not pd.isna(full_price2) and full_price2 != 0:
            full_price = full_price2
            hyperscaler_price = hyperscaler_price2
            non_hyperscaler_price = non_hyperscaler_price2
            final_source = 'rerun'  # Mark as rerun since second attempt succeeded
            reran = True
        else:
            print("Immediate rerun still invalid (zero/NaN). Proceeding to fallback/threshold checks.")

    if last_price is not None and significant_change(full_price, last_price):
        print(f"Detected >=50% change from last stored price ({last_price:.4f} -> {full_price:.4f}). Re-running calculation to confirm...")
        # Rerun once to confirm
        full_price2, hyperscaler_price2, non_hyperscaler_price2 = calculate_weighted_index()
        reran = True
        if full_price2 and not pd.isna(full_price2):
            full_price = full_price2
            hyperscaler_price = hyperscaler_price2
            non_hyperscaler_price = non_hyperscaler_price2
            final_source = 'rerun'
        else:
            print("Rerun produced empty/zero price. Considering fallback average.")

    # Fallback if price is 0/NaN or empty after rerun attempt
    if (full_price is None or pd.isna(full_price) or full_price == 0):
        avg_full, avg_hyp, avg_non = average_last_n_prices(10)
        if avg_full is not None:
            print(f"Using fallback average of last prices (n<=10): full={avg_full:.4f}")
            full_price = avg_full if avg_full is not None else full_price
            hyperscaler_price = avg_hyp if avg_hyp is not None else hyperscaler_price
            non_hyperscaler_price = avg_non if avg_non is not None else non_hyperscaler_price
            final_source = 'fallback_avg'
        else:
            print("No history available for fallback average; keeping current value.")

    append_price_history(full_price, hyperscaler_price, non_hyperscaler_price, final_source)
    print(f"Appended price record (source={final_source}) to {HISTORY_FILE}")

    # Attempt trigger commit only if rerun confirmed large change (avoid noise on fallback avg)
    if last_price is not None and final_source == 'rerun':
        triggered = attempt_trigger_commit(last_price, full_price)
        if triggered:
            print("Workflow re-trigger commit created.")
        else:
            print("Trigger conditions not met or commit skipped.")

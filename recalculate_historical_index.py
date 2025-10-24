#!/usr/bin/env python3
"""
Recalculate Historical GPU Index with Corrected AWS Pricing

This script reconstructs the exact historical GPU index by:
1. Extracting gpu_prices_normalized.csv from each git commit
2. Correcting AWS GPU counts (48→8, 24→4, 12→2, 6→1)
3. Recalculating the index for each historical point
"""

import pandas as pd
import subprocess
import json
from datetime import datetime
import sys

def get_git_commit_for_timestamp(timestamp_str, all_commits):
    """Find the git commit hash closest to the given timestamp"""
    try:
        # Convert timestamp to datetime and make it timezone-aware (UTC)
        target_dt = pd.to_datetime(timestamp_str)
        if target_dt.tzinfo is None:
            target_dt = target_dt.tz_localize('UTC')

        # Find closest commit by time difference
        min_diff = None
        closest_commit = None

        for commit_hash, commit_dt in all_commits:
            diff = abs((target_dt - commit_dt).total_seconds())

            # Only consider commits within 1 hour of target
            if diff <= 3600:  # 1 hour
                if min_diff is None or diff < min_diff:
                    min_diff = diff
                    closest_commit = commit_hash

        return closest_commit

    except Exception as e:
        print(f"Error finding commit for {timestamp_str}: {e}")
        return None

def get_all_commits():
    """Get all commits that modified gpu_prices_normalized.csv"""
    try:
        cmd = [
            'git', 'log', '--all',
            '--pretty=format:%H|%ci',
            '--', 'gpu_prices_normalized.csv'
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd='.')

        commits = []
        for line in result.stdout.strip().split('\n'):
            if '|' in line:
                parts = line.split('|')
                commit_hash = parts[0]
                commit_time = pd.to_datetime(parts[1])
                commits.append((commit_hash, commit_time))

        return commits

    except Exception as e:
        print(f"Error getting commits: {e}")
        return []

def extract_csv_from_commit(commit_hash, filename='gpu_prices_normalized.csv'):
    """Extract a CSV file from a specific git commit"""
    try:
        cmd = ['git', 'show', f'{commit_hash}:{filename}']
        result = subprocess.run(cmd, capture_output=True, text=True, cwd='.')

        if result.returncode == 0:
            # Parse CSV content
            from io import StringIO
            df = pd.read_csv(StringIO(result.stdout))
            return df
        else:
            return None

    except Exception as e:
        print(f"Error extracting {filename} from {commit_hash}: {e}")
        return None

def correct_aws_gpu_counts(df):
    """Fix AWS GPU counts and recalculate prices"""
    # Find AWS rows
    aws_mask = df['Provider'] == 'Amazon Web Services'

    if not aws_mask.any():
        return df, None, None

    # Store old AWS price before correction
    old_aws_data = df[aws_mask].copy()
    old_avg_normalized = old_aws_data['NormalizedPrice'].mean()

    # Make a copy to modify
    df_corrected = df.copy()

    # GPU count corrections mapping
    gpu_count_fix = {
        48: 8,
        24: 4,
        12: 2,
        6: 1
    }

    # Apply corrections to AWS rows
    for idx in df_corrected[aws_mask].index:
        old_count = df_corrected.loc[idx, 'GPU_Count']

        if old_count in gpu_count_fix:
            new_count = gpu_count_fix[old_count]
            df_corrected.loc[idx, 'GPU_Count'] = new_count

            # Recalculate PricePerGPU
            price_numeric = df_corrected.loc[idx, 'Price_Numeric']
            df_corrected.loc[idx, 'PricePerGPU'] = price_numeric / new_count

            # Recalculate NormalizedPrice
            performance_ratio = df_corrected.loc[idx, 'PerformanceRatio']
            df_corrected.loc[idx, 'NormalizedPrice'] = (price_numeric / new_count) * performance_ratio

    # Get new AWS average
    new_aws_data = df_corrected[aws_mask]
    new_avg_normalized = new_aws_data['NormalizedPrice'].mean()

    return df_corrected, old_avg_normalized, new_avg_normalized

def calculate_corrected_index(old_index, old_aws_price, new_aws_price,
                              aws_weight=0.1828, total_weight=0.8895, aws_discount=0.44):
    """
    Calculate corrected index using delta method

    Args:
        old_index: Original index value with bug
        old_aws_price: AWS normalized price with bug (avg ~1.147)
        new_aws_price: AWS normalized price corrected (avg ~6.88)
        aws_weight: AWS weight in index (18.28%)
        total_weight: Total weight of all providers (88.95%)
        aws_discount: Discount applied to AWS as hyperscaler (44%)

    Returns:
        Corrected index value
    """
    # Calculate weighted contribution change
    # AWS contribution = weight × price × (1 - discount)
    old_contribution = aws_weight * old_aws_price * (1 - aws_discount)
    new_contribution = aws_weight * new_aws_price * (1 - aws_discount)

    delta_contribution = new_contribution - old_contribution

    # Adjust index
    corrected_index = old_index + (delta_contribution / total_weight)

    return corrected_index

def main():
    print("=" * 70)
    print("Historical GPU Index Recalculation Script")
    print("Correcting AWS GPU Count Bug Across All Historical Data")
    print("=" * 70)

    # Load history
    print("\nLoading gpu_index_history.csv...")
    history_df = pd.read_csv('gpu_index_history.csv')

    print(f"Found {len(history_df)} historical index records")
    print(f"Date range: {history_df['timestamp'].min()} to {history_df['timestamp'].max()}")

    # Get all git commits upfront
    print("\nFetching all git commits...")
    all_commits = get_all_commits()
    print(f"Found {len(all_commits)} git commits for gpu_prices_normalized.csv")

    # Prepare results storage
    results = []

    # Process each historical point
    total = len(history_df)
    success_count = 0
    skip_count = 0

    for idx, row in history_df.iterrows():
        timestamp = row['timestamp']
        old_index = row['full_index_price']

        print(f"\n[{idx+1}/{total}] Processing {timestamp}...")

        # Find corresponding git commit
        commit_hash = get_git_commit_for_timestamp(timestamp, all_commits)

        if not commit_hash:
            print(f"  WARNING: No git commit found, skipping...")
            results.append({
                'timestamp': timestamp,
                'old_index': old_index,
                'corrected_index': None,
                'delta': None,
                'commit_hash': None,
                'status': 'no_commit'
            })
            skip_count += 1
            continue

        print(f"  Found commit: {commit_hash[:8]}")

        # Extract CSV from commit
        df = extract_csv_from_commit(commit_hash)

        if df is None:
            print(f"  WARNING: Could not extract CSV, skipping...")
            results.append({
                'timestamp': timestamp,
                'old_index': old_index,
                'corrected_index': None,
                'delta': None,
                'commit_hash': commit_hash,
                'status': 'no_csv'
            })
            skip_count += 1
            continue

        # Correct AWS data
        df_corrected, old_aws_price, new_aws_price = correct_aws_gpu_counts(df)

        if old_aws_price is None:
            print(f"  WARNING: No AWS data in snapshot, skipping...")
            results.append({
                'timestamp': timestamp,
                'old_index': old_index,
                'corrected_index': None,
                'delta': None,
                'commit_hash': commit_hash,
                'status': 'no_aws_data'
            })
            skip_count += 1
            continue

        # Calculate corrected index
        corrected_index = calculate_corrected_index(old_index, old_aws_price, new_aws_price)
        delta = corrected_index - old_index

        print(f"  SUCCESS: Old Index: ${old_index:.4f}/hr")
        print(f"  SUCCESS: Corrected Index: ${corrected_index:.4f}/hr")
        print(f"  SUCCESS: Delta: +${delta:.4f} ({(delta/old_index)*100:.1f}%)")

        results.append({
            'timestamp': timestamp,
            'old_index': old_index,
            'corrected_index': corrected_index,
            'delta': delta,
            'aws_old_price': old_aws_price,
            'aws_new_price': new_aws_price,
            'commit_hash': commit_hash,
            'status': 'success'
        })
        success_count += 1

    # Save results
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total records: {total}")
    print(f"Successfully corrected: {success_count}")
    print(f"Skipped: {skip_count}")

    results_df = pd.DataFrame(results)
    output_file = 'corrected_gpu_index_history.csv'
    results_df.to_csv(output_file, index=False)

    print(f"\nSUCCESS: Results saved to: {output_file}")

    # Calculate statistics on successful corrections
    successful = results_df[results_df['status'] == 'success']
    if len(successful) > 0:
        print("\nCorrection Statistics:")
        print(f"  Average delta: +${successful['delta'].mean():.4f}/hr")
        print(f"  Min delta: +${successful['delta'].min():.4f}/hr")
        print(f"  Max delta: +${successful['delta'].max():.4f}/hr")
        print(f"  Std dev: ${successful['delta'].std():.4f}/hr")

        avg_pct = (successful['delta'] / successful['old_index'] * 100).mean()
        print(f"  Average % increase: {avg_pct:.2f}%")

    return results_df

if __name__ == "__main__":
    try:
        results = main()
        print("\nSUCCESS: Script completed successfully!")
    except Exception as e:
        print(f"\nERROR: Script failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

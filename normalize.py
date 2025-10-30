import pandas as pd


baseline = {
    "CUDA Cores": 16896,
    "Tensor Cores": 528,
    "FP16 TFLOPS": 1979,
    "FP64 TFLOPS": 34,
    "Memory Bandwidth (GB/s)": 3350,
    "VRAM (GB)": 80,
    "Boost Clock (MHz)": 1830,
    "L2 Cache (MB)": 50
}

weights = {
    "CUDA Cores": 0.144435,
    "Tensor Cores": 0.144435,
    "FP16 TFLOPS": 0.155983,
    "FP64 TFLOPS": 0.155958,
    "Memory Bandwidth (GB/s)": 0.138890,
    "VRAM (GB)": 0.140570,
    "L2 Cache (MB)": 0.119730
}


variant_specs = {
    "SXM": baseline,
    "PCIe": {
        "CUDA Cores": 14592,
        "Tensor Cores": 456,
        "FP16 TFLOPS": 1513,
        "FP64 TFLOPS": 26,
        "Memory Bandwidth (GB/s)": 2000,
        "VRAM (GB)": 80,
        "Boost Clock (MHz)": 1590,
        "L2 Cache (MB)": 50
    },
    "NVL": {
        "CUDA Cores": 16896,
        "Tensor Cores": 528,
        "FP16 TFLOPS": 1979,
        "FP64 TFLOPS": 34,
        "Memory Bandwidth (GB/s)": 3900,
        "VRAM (GB)": 94,
        "Boost Clock (MHz)": 1830,
        "L2 Cache (MB)": 50
    },
    "MIG": {
        "CUDA Cores": 8448,
        "Tensor Cores": 264,
        "FP16 TFLOPS": 990,
        "FP64 TFLOPS": 17,
        "Memory Bandwidth (GB/s)": 1675,
        "VRAM (GB)": 40,
        "Boost Clock (MHz)": 1830,
        "L2 Cache (MB)": 25
    }
}


def get_perf_ratio(variant):
    if variant not in variant_specs:
        return None
    specs = variant_specs[variant]
    score = sum(weights[m] * (specs[m] / baseline[m]) for m in weights)
    return score


df = pd.read_csv("h100_prices_usd.csv")
df["Price (USD)"] = (
    df["Price_USD"]
    .astype(str)  
    .str.replace("$", "", regex=False)  
    .str.replace("/hr", "", regex=False)  
    .str.replace(",", "", regex=False)  
    .astype(float)
)

def detect_variant(name):
    name_lower = name.lower()
    if "sxm" in name_lower:
        return "SXM"
    elif "pcie" in name_lower or "pci" in name_lower:
        return "PCIe"
    elif "nvl" in name_lower:
        return "NVL"
    elif "mig" in name_lower:
        return "MIG"
    elif "nvlink" in name_lower:
        return "NVL"  # NVLink is similar to NVL
    elif "hgx" in name_lower:
        return "SXM"  # HGX typically uses SXM form factor
    elif "h200" in name_lower:
        return "SXM"  # H200 typically uses SXM form factor
    elif "standard" in name_lower or "h100" in name_lower:
        return "SXM"  # Default H100 standard to SXM (most common)
    else:
        return "SXM"  # Default fallback to SXM since it's the most common H100 variant

def extract_gpu_count(name):
    """Extract GPU count from GPU variant name"""
    import re
    name_lower = name.lower()
    
    # Look for patterns like "8x gpus", "4x gpu", "2x", etc.
    patterns = [
        r'(\d+)x?\s*gpus?',
        r'(\d+)\s*x\s*gpus?',
        r'\((\d+)x\s*gpus?\)',
        r'(\d+)×\s*h100',  # Unicode multiplication sign
        r'(\d+)x\s*h100',
        r'\((\d+)x\s*gpus?\)',  # Enhanced pattern for (8x GPUs)
        r'a3.*?(\d+)x?\s*gpus?',  # Google Cloud A3 pattern
        r'nd\d+.*?(\d+)x?\s*gpus?'  # Azure ND pattern
    ]
    
    for pattern in patterns:
        match = re.search(pattern, name_lower)
        if match:
            return int(match.group(1))
    
    # Special handling for known cluster configurations
    if 'a3 machine type' in name_lower and '8x' in name_lower:
        return 8
    if 'a3 integration' in name_lower and '8x' in name_lower:
        return 8
    if 'nd96isr' in name_lower:
        return 8  # ND96isr is known to be 8x GPU configuration
    
    # Default to 1 GPU if no pattern found
    return 1

df["VariantType"] = df["GPU_Variant"].apply(detect_variant)
df["GPUCountFromName"] = df["GPU_Variant"].apply(extract_gpu_count)

# Use GPU count from name if it's different from GPU_Count column, otherwise use GPU_Count
df["EffectiveGPUCount"] = df.apply(
    lambda row: max(row["GPUCountFromName"], row["GPU_Count"]), axis=1
)

# Special handling for known cluster configurations that might not be detected properly
def fix_cluster_pricing(row):
    """Fix cluster pricing for known providers with multi-GPU configurations"""
    name = row["GPU_Variant"].lower()
    provider = row["Provider"]
    
    # Google Cloud A3 machine types are 8x GPU clusters
    if provider == "Google Cloud" and ("a3 machine type" in name or "a3 integration" in name):
        if "per gpu" not in name:  # If it's not already per-GPU pricing
            return 8
    
    # Microsoft Azure ND96isr is 8x GPU cluster
    if provider == "Microsoft Azure" and "nd96isr" in name:
        if "per gpu" not in name:  # If it's not already per-GPU pricing
            return 1
    
    return row["EffectiveGPUCount"]

df["EffectiveGPUCount"] = df.apply(fix_cluster_pricing, axis=1)

# Calculate per-GPU price by dividing by effective GPU count
df["PricePerGPU"] = df["Price (USD)"] / df["EffectiveGPUCount"]

perf_ratios = {v: get_perf_ratio(v) for v in variant_specs}

df["PerformanceRatio"] = df["VariantType"].map(perf_ratios)

# Normalize the per-GPU price by dividing by performance ratio
# This gives us a performance-adjusted price where higher performance variants 
# will have lower normalized prices and lower performance variants will have higher normalized prices
df["NormalizedPrice"] = df.apply(
    lambda row: row["PricePerGPU"] / row["PerformanceRatio"] 
    if row["PerformanceRatio"]
    else row["PricePerGPU"],
    axis=1
)

df.to_csv("gpu_prices_normalized.csv", index=False)
print(df[["Provider", "GPU_Variant", "Price (USD)", "EffectiveGPUCount", "PricePerGPU", "VariantType", "PerformanceRatio", "NormalizedPrice"]])

# Create provider averages CSV
print("\n" + "="*80)
print("Creating provider averages...")

# Group by provider and calculate averages
provider_averages = df.groupby('Provider').agg({
    'NormalizedPrice': ['mean', 'count', 'std'],
    'PricePerGPU': 'mean',
    'Price (USD)': 'mean'
}).round(4)

# Flatten column names
provider_averages.columns = [
    'AvgNormalizedPrice', 'VariantCount', 'StdDevNormalizedPrice',
    'AvgPricePerGPU', 'AvgOriginalPrice'
]

# Reset index to make Provider a column
provider_averages = provider_averages.reset_index()

# Sort by average normalized price
provider_averages = provider_averages.sort_values('AvgNormalizedPrice')

# Save to CSV
provider_averages.to_csv("provider_averages.csv", index=False)

print("Provider averages (sorted by lowest normalized price):")
print(provider_averages.to_string(index=False))

print(f"\nSaved detailed data to: gpu_prices_normalized.csv")
print(f"Saved provider averages to: provider_averages.csv")

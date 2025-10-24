# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a GPU pricing scraper and index calculator system that collects H100 GPU pricing data from multiple cloud providers and calculates a weighted GPU price index. The system runs on a scheduled GitHub Actions workflow, scraping prices twice daily and updating the repository with the latest pricing data and index calculations.

## Key Commands

### Running the Complete Pipeline

The pipeline consists of 5 sequential steps that must be run in order:

```bash
# Step 1: Run all scrapers to collect pricing data
python scraper20.py          # Scrapes 36+ cloud providers (HyperStack, CoreWeave, etc.)
python scraper-1.py          # Additional provider scrapers
python aws_scraper.py        # Dedicated AWS P5 instance scraper

# Step 2: Convert JSON pricing data to CSV
python json_to_csv_converter.py

# Step 3: Convert all currencies to USD using live exchange rates
python clean_and_convert_currencies.py

# Step 4: Normalize prices by GPU variant performance
python normalize.py

# Step 5: Calculate weighted GPU price index
python gpu_index_calculator.py
```

### Running Individual Components

```bash
# Run a single scraper
python scraper20.py

# Test currency conversion with live rates
python clean_and_convert_currencies.py

# Recalculate index from existing normalized data
python gpu_index_calculator.py
```

### Dependencies Installation

```bash
pip install pandas numpy requests beautifulsoup4 selenium webdriver-manager lxml openpyxl
```

## Architecture

### Data Flow

1. **Scraping** → Multiple scrapers collect pricing from cloud providers
2. **Aggregation** → JSON files are converted and combined into CSV
3. **Currency Conversion** → All prices normalized to USD using live exchange rates
4. **Performance Normalization** → Prices adjusted based on GPU variant specs (SXM, PCIe, NVL, MIG)
5. **Index Calculation** → Weighted average computed using provider market share weights

### Key Files

#### Scrapers
- **scraper20.py** (2,100+ lines): Main multi-provider scraper using abstract base class pattern. Implements `CloudProviderScraper` base class with specific scrapers for 36+ providers
- **scraper-1.py**: Additional provider implementations
- **aws_scraper.py**: AWS P5 instance specific scraper with multiple fallback methods

#### Data Processing Pipeline
- **json_to_csv_converter.py**: Converts multiple JSON pricing files to unified CSV format, handles GPU count extraction, pricing model detection
- **clean_and_convert_currencies.py**: Fetches live exchange rates (EUR, INR → USD) via frankfurter.app API
- **normalize.py**: Applies GPU variant performance ratios to normalize prices across SXM/PCIe/NVL/MIG variants
- **gpu_index_calculator.py** (499 lines): Core index calculation with:
  - Outlier filtering using IQR method
  - Provider weight management (hyperscalers vs non-hyperscalers)
  - Historical price tracking
  - Discount application for enterprise buyers
  - Automatic rerun triggers on significant price changes (≥50%)

#### Configuration & Automation
- **autorun.py**: Triggers external Supabase function after pipeline completion
- **.github/workflows/gpu-price-scraper.yml**: Main GitHub Actions workflow, runs at 11:00 and 23:00 UTC
- **.github/workflows/autorun.yml**: Separate workflow for autorun service calls

#### Output Files
- **multi_cloud_h100_prices.json**: Raw scraped pricing data
- **h100_prices_combined.csv**: Aggregated CSV from all JSON sources
- **h100_prices_usd.csv**: Currency-normalized pricing
- **gpu_prices_normalized.csv**: Performance-normalized pricing with detailed variant info
- **provider_averages.csv**: Provider-level aggregated statistics
- **h100_gpu_index.csv**: Final index prices (full, hyperscalers-only, non-hyperscalers-only)
- **gpu_index_history.csv**: Time-series of index prices with source tracking
- **results_summary.md**: Pipeline status summary (auto-generated)

### GPU Variant Performance Model

The system uses hardware specifications to calculate performance ratios for different H100 variants:

- **Baseline (SXM)**: Full H100 specs (16896 CUDA cores, 528 Tensor cores, 80GB VRAM, 3350 GB/s bandwidth)
- **PCIe**: Reduced specs (14592 CUDA cores, 2000 GB/s bandwidth)
- **NVL**: Enhanced specs (94GB VRAM, 3900 GB/s bandwidth)
- **MIG**: Partitioned instance (half cores, 40GB VRAM)

Performance weights:
- CUDA Cores: 14.44%
- Tensor Cores: 14.44%
- FP16 TFLOPS: 15.60%
- FP64 TFLOPS: 15.60%
- Memory Bandwidth: 13.89%
- VRAM: 14.06%
- L2 Cache: 11.97%

### Index Calculation Logic

1. **Provider Categorization**:
   - **Hyperscalers** (60% total weight): AWS, Azure, Google Cloud, CoreWeave
   - **Non-hyperscalers** (40% total weight): 30+ specialized GPU cloud providers

2. **Discount Application**: Hyperscalers have buyer discount percentages (44-65%) applied to reflect actual market prices vs list prices

3. **Outlier Filtering**: IQR method (2.5x multiplier) removes extreme outliers from non-hyperscaler prices while protecting hyperscaler data

4. **Weighted Average**: Each provider has specific weight representing market share. Final index = Σ(weight × price) / Σ(weight)

5. **Historical Tracking**: Maintains price history with automatic carry-forward logic when:
   - New calculation produces zero/NaN
   - Price change exceeds 50% threshold (likely data quality issue)

6. **Automatic Rerun**: On ≥50% price changes, commits trigger marker to repository, causing workflow to re-run for validation

## Scraper Implementation Pattern

When adding a new cloud provider scraper:

1. Extend `CloudProviderScraper` abstract base class
2. Implement `extract_h100_prices(soup)` method
3. Add provider to weights dictionary in `gpu_index_calculator.py`
4. Use regex patterns to extract prices from page text
5. Handle multiple GPU configurations (1x, 2x, 4x, 8x clusters)
6. Detect pricing models (On-Demand, Reserved, Spot, Monthly)

Example structure:
```python
class NewProviderScraper(CloudProviderScraper):
    def __init__(self):
        super().__init__("ProviderName", "https://provider.com/pricing")

    def extract_h100_prices(self, soup: BeautifulSoup) -> Dict[str, str]:
        # Implement extraction logic
        return {"H100 SXM": "$X.XX"}
```

## GitHub Actions Workflow

The pipeline runs automatically:
- **Schedule**: 11:00 and 23:00 UTC daily
- **On Push**: Runs on commits to main branch
- **Manual**: Can be triggered via workflow_dispatch

Pipeline steps in Actions:
1. Checkout repository
2. Setup Python 3.10
3. Install dependencies + Chrome/ChromeDriver
4. Run scrapers (continues on individual scraper failures)
5. Convert JSON → CSV
6. Clean & convert currencies
7. Normalize prices
8. Calculate GPU index
9. Generate results summary
10. Commit & push updated CSVs/JSON
11. Trigger autorun service
12. Upload artifacts (30-day retention)

## Data Validation & Error Handling

- **Scraper Failures**: Pipeline continues if individual scrapers fail (uses `|| echo "failed, continuing..."`)
- **Missing Prices**: Providers with NaN prices are skipped in index calculation
- **Currency API Failures**: Falls back to hardcoded rates (EUR: 1.08, INR: 0.012)
- **Price Anomalies**: Automatic carry-forward of previous price on ≥50% changes
- **Git Operations**: Auto-configures git identity as github-actions bot
- **Trigger Safeguards**: Once-per-run marker prevents infinite rerun loops

## Important Notes

- All prices are normalized to **per-GPU, per-hour** rates in USD
- Hyperscaler prices use discounted rates reflecting actual enterprise pricing
- The index includes three calculations: full (combined), hyperscalers-only, non-hyperscalers-only
- Provider weights must sum to 100% across all providers
- Outlier filtering only applies to non-hyperscalers to maintain market representation
- CSV files are the source of truth for the pipeline (committed to git)
- History file enables time-series analysis and anomaly detection

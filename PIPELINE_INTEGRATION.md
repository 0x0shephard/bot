# Pipeline Integration Guide

## Overview

This document explains how `push_to_contract.py` and `autorun.py` work together in the GPU price oracle pipeline.

## Pipeline Flow

```
[Pipeline Steps 1-6: Scraping → Merging → Conversion → Normalization → Index Calculation]
                                    ↓
                          h100_gpu_index.csv
                                    ↓
                      [STEP 7: push_to_contract.py]
                                    ↓
                  MultiAssetOracle Contract (Sepolia)
                                    ↓
                        [STEP 8: autorun.py]
                                    ↓
                      Supabase Database (via Edge Function)
                                    ↓
                            Frontend Display
```

---

## Script 1: push_to_contract.py

### Purpose
Reads GPU index prices from the pipeline-generated CSV and pushes them to the MultiAssetOracle smart contract on Ethereum Sepolia testnet.

### Key Features

#### 1. CSV Price Reading
- Reads `h100_gpu_index.csv` (output from `gpu_index_calculator.py`)
- Extracts three price metrics:
  - `Full_Index_Price`: Weighted average across all providers
  - `Hyperscalers_Only_Price`: AWS, Azure, GCP only
  - `Non_Hyperscalers_Only_Price`: Smaller providers only

#### 2. Blockchain Updates
- Connects to Ethereum Sepolia testnet via RPC
- Updates three assets in the MultiAssetOracle contract:
  - `H100_HOURLY`: Full weighted index
  - `H100_HYPERSCALERS_HOURLY`: Hyperscalers only
  - `H100_NON_HYPERSCALERS_HOURLY`: Non-hyperscalers only
- Uses batch updates for gas efficiency (one transaction for all three prices)
- Prices stored with 18 decimals precision

#### 3. Price Validation
- Checks prices are > 0
- Warns if prices > $100/hr (unusually high)
- Validates CSV format and required columns

#### 4. Transaction Handling
- Dynamic gas pricing (EIP-1559)
- Automatic nonce management
- Transaction receipt confirmation
- 180-second timeout for transaction confirmation

#### 5. Logging
- Updates logged to `contract_update_log.json`
- Stores last 100 updates with:
  - Timestamp, prices, transaction hash, block number
  - Contract address, network, updater address

### Command-Line Options

```bash
# Basic usage (reads from h100_gpu_index.csv)
python push_to_contract.py

# Use custom CSV file
python push_to_contract.py --csv path/to/custom.csv

# Manual price override (bypass CSV)
python push_to_contract.py --manual-prices 3.79 4.20 2.95

# Register assets (first-time setup)
python push_to_contract.py --register

# Skip on-chain verification (faster, for CI/CD)
python push_to_contract.py --no-verify

# Dry run (test without sending transactions)
python push_to_contract.py --dry-run
```

### Environment Variables Required

```bash
# Required
SEPOLIA_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/YOUR_API_KEY
ORACLE_UPDATER_PRIVATE_KEY=0x...  # or PRIVATE_KEY

# Optional
MULTI_ASSET_ORACLE_ADDRESS=0xB44d652354d12Ac56b83112c6ece1fa2ccEfc683
ORACLE_DECIMALS=18
```

### Workflow Integration

In `.github/workflows/gpu-price-scraper.yml`, this runs as **Step 7**:

```yaml
- name: Step 7 - Push to Sepolia Smart Contract
  env:
    SEPOLIA_RPC_URL: ${{ secrets.SEPOLIA_RPC_URL }}
    ORACLE_UPDATER_PRIVATE_KEY: ${{ secrets.ORACLE_UPDATER_PRIVATE_KEY }}
  run: |
    python push_to_contract.py --csv h100_gpu_index.csv --no-verify
```

**Note:** The `--no-verify` flag is used in CI/CD to skip on-chain verification for faster execution.

### Error Handling

- **Missing CSV**: Exits with error, suggests checking pipeline
- **Invalid CSV format**: Validates columns and data types
- **RPC connection failure**: Detailed error with troubleshooting steps
- **Transaction failure**: Full traceback with gas and nonce details
- **Price verification mismatch**: Warns but doesn't fail (unless --no-verify)

---

## Script 2: autorun.py

### Purpose
Fetches oracle prices FROM the blockchain and pushes them TO the Supabase database for frontend display. Runs AFTER `push_to_contract.py`.

### Key Features

#### 1. Blockchain Price Fetching
- Connects to Sepolia testnet (read-only, no private key needed)
- Calls `getPrice()` on MultiAssetOracle contract for each asset
- Converts prices from 18 decimals to float

#### 2. Database Sync
- Pushes oracle prices to Supabase via edge function
- Creates price snapshots with:
  - Market ID, market name, vAMM address
  - Oracle price (index price)
  - Block number, timestamp

#### 3. Retry Logic
- **Max retries**: 3 attempts per market
- **Retry delay**: 5 seconds between attempts
- **Timeout**: 10 seconds per HTTP request
- Continues with other markets if one fails

#### 4. Error Handling
- Graceful handling of:
  - RPC connection failures
  - Missing oracle prices (not yet set)
  - HTTP request timeouts
  - Supabase edge function errors
- Detailed error messages with troubleshooting steps

### Command-Line Options

```bash
# Basic usage (fetches from blockchain, pushes to database)
python autorun.py

# Use custom RPC URL
python autorun.py --rpc-url https://your-rpc-endpoint.com

# Use custom oracle address
python autorun.py --oracle 0x...

# Use custom database URL
python autorun.py --db-url https://your-supabase-function.com

# Dry run (fetch prices, skip database push)
python autorun.py --dry-run
```

### Environment Variables

```bash
# Optional (has defaults)
SEPOLIA_RPC_URL=https://rpc.sepolia.org  # Default public RPC
MULTI_ASSET_ORACLE_ADDRESS=0xB44d652354d12Ac56b83112c6ece1fa2ccEfc683
SUPABASE_PRICE_FUNCTION_URL=https://basxvmmtxwlxylpukqjj.supabase.co/functions/v1/fetch-price
```

**Note:** No private key required - this script only reads from blockchain.

### Workflow Integration

In `.github/workflows/gpu-price-scraper.yml`, this runs as **final step**:

```yaml
- name: Run autorun.py
  run: |
    echo "Running autorun.py..."
    python autorun.py
    echo "autorun.py completed"
```

Runs after:
- Step 7: `push_to_contract.py` (updates blockchain)
- Git commit/push (saves results to repo)

### Market Configuration

Three markets are tracked:

| Asset | Display Name | Market ID | vAMM Address |
|-------|--------------|-----------|--------------|
| H100_HOURLY | H100 GPU | 0x2bc0c... | 0xF7210ccC... |
| H100_HYPERSCALERS_HOURLY | H100 HyperScalers | 0xf4aa47... | 0xFE1df531... |
| H100_NON_HYPERSCALERS_HOURLY | H100 non-HyperScalers | 0x9d2d65... | 0x19574B8C... |

### Output Format

**Success:**
```
============================================================
ORACLE PRICE DATABASE PUSHER
============================================================
Connected to Ethereum
   Chain ID: 11155111
   Latest block: 12345678
   Oracle: 0xB44d652...
   Database URL: https://basxvmmtxwlxylpukqjj...
============================================================

============================================================
FETCHING ORACLE PRICES FROM BLOCKCHAIN
============================================================
   ✓ H100 GPU: $3.774810/hour (Index Price)
   ✓ H100 HyperScalers: $4.202163/hour (Index Price)
   ✓ H100 non-HyperScalers: $2.992301/hour (Index Price)
============================================================

============================================================
PUSHING ORACLE PRICES TO DATABASE
============================================================
   ✓ H100 GPU: Pushed successfully
   ✓ H100 HyperScalers: Pushed successfully
   ✓ H100 non-HyperScalers: Pushed successfully
============================================================
Results: 3 succeeded, 0 failed
============================================================

============================================================
✓ SUCCESS! ALL ORACLE PRICES PUSHED TO DATABASE
============================================================
   3 market(s) updated successfully
   Prices are now available for the frontend
============================================================
```

**Error (no prices on blockchain):**
```
============================================================
ERROR: No prices fetched from blockchain
============================================================
   This may indicate:
   1. Oracle prices not yet set (run push_to_contract.py first)
   2. RPC connection issues
   3. Contract address mismatch
============================================================
```

---

## Pipeline Execution Order

### Automated (GitHub Actions)

```bash
# Every 12 hours at 0:00 and 12:00 UTC
1. Run scrapers (6 scripts in parallel)
2. Merge JSON files → multi_cloud_h100_prices.json
3. Convert to CSV → h100_prices_combined.csv
4. Convert currencies → h100_prices_usd.csv
5. Normalize prices → gpu_prices_normalized.csv
6. Calculate index → h100_gpu_index.csv
7. Push to blockchain (push_to_contract.py --no-verify)
8. Commit results to git
9. Push to database (autorun.py)
10. Archive artifacts
```

### Manual Execution

```bash
# Step 1: Run the pipeline (if not already done)
python scraper20.py
python scraper-1.py
# ... other scrapers
python combined.py
python json_to_csv_converter.py
python clean_and_convert_currencies.py
python normalize.py
python gpu_index_calculator.py

# Step 2: Push to blockchain
python push_to_contract.py

# Step 3: Sync to database
python autorun.py
```

### Testing Without Blockchain

```bash
# Test CSV reading without transactions
python push_to_contract.py --dry-run

# Test blockchain fetching without database push
python autorun.py --dry-run
```

---

## Troubleshooting

### push_to_contract.py Issues

**Problem:** `ERROR: CSV file not found`
- **Solution:** Ensure pipeline completed successfully, run `gpu_index_calculator.py`

**Problem:** `ERROR: Private key not configured`
- **Solution:** Set `ORACLE_UPDATER_PRIVATE_KEY` or `PRIVATE_KEY` in `.env`

**Problem:** `ERROR: Failed to connect to Sepolia RPC`
- **Solution:** Check `SEPOLIA_RPC_URL`, try alternative RPC (Alchemy, Infura, QuickNode)

**Problem:** Transaction fails with "insufficient funds"
- **Solution:** Add Sepolia ETH to updater wallet (faucet: https://sepoliafaucet.com)

### autorun.py Issues

**Problem:** `ERROR: No prices fetched from blockchain`
- **Solution:** Run `push_to_contract.py` first to set prices on-chain

**Problem:** Database push fails (HTTP 500)
- **Solution:** Check Supabase edge function logs, verify `SUPABASE_PRICE_FUNCTION_URL`

**Problem:** Retry loop exhausted
- **Solution:** Check network connectivity, Supabase status, edge function configuration

---

## Security Notes

### push_to_contract.py
- **Private key required**: NEVER commit to git or share
- **Gas costs**: ~0.0005 ETH per update (free on Sepolia testnet)
- **Access control**: Ensure only authorized wallets can update oracle

### autorun.py
- **No private key needed**: Read-only blockchain access
- **Public RPC safe**: Can use public endpoints
- **Rate limiting**: Uses retry logic to handle rate limits

---

## Recent Improvements

### push_to_contract.py
1. Added `--no-verify` flag for faster CI/CD execution
2. Added `--dry-run` mode for testing without transactions
3. Added standalone CSV reader for dry-run mode
4. Improved error messages with troubleshooting steps
5. Better price validation and sanity checks

### autorun.py
1. Complete rewrite from simple GET request to full database pusher
2. Added retry logic (3 attempts, 5-second delay)
3. Added `--dry-run` mode for testing
4. Improved error handling with detailed diagnostics
5. Better logging and progress indicators
6. Graceful handling of missing prices

---

## Asset IDs Reference

All three scripts use the same asset IDs (keccak256 hashes):

```python
ASSET_IDS = {
    "H100_HOURLY": "0x82af7da7090d6235dbc9f8cfccfb82eee2e9cb33d50be18eabf66c158261796a",
    "H100_HYPERSCALERS_HOURLY": "0x4907d2c1e61b87a99a260f8529c3c4f9e2374edae1f5ab1464a8e79d0f2c26de",
    "H100_NON_HYPERSCALERS_HOURLY": "0xd6e43f59d2c94773a52e2c20f09762901247d1aaf2090d0b99e85c55c9833626",
}
```

These are generated using `keccak256("H100_HOURLY")`, etc.

---

## Next Steps

1. **Monitor first automated run**: Check GitHub Actions logs
2. **Verify on-chain prices**: https://sepolia.etherscan.io/address/0xB44d652354d12Ac56b83112c6ece1fa2ccEfc683
3. **Check database updates**: Verify Supabase `price_snapshots` table
4. **Test manually**: Run both scripts locally to ensure proper configuration
5. **Set up alerts**: Monitor for transaction failures or database sync issues

---

## Support

For issues or questions:
- Check GitHub Actions logs: https://github.com/YOUR_REPO/actions
- Review Etherscan transactions: https://sepolia.etherscan.io
- Check Supabase logs: Supabase Dashboard → Edge Functions
- Review `contract_update_log.json` for recent updates

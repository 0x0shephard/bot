#!/usr/bin/env python3
"""Push oracle index prices to Supabase database.

This script reads oracle/index prices from the MultiAssetOracle contract and pushes
them to the database via market-specific Supabase edge functions.

Each market has its own endpoint and database table for better data isolation.
vAMM prices are tracked by the frontend.

Can be run independently or after oracle updates.
"""

import os
import sys
import time
import requests
from typing import Optional, Dict, Tuple
from dataclasses import dataclass

from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

# Configuration
SEPOLIA_RPC_URL = os.getenv("SEPOLIA_RPC_URL", "https://eth-sepolia.g.alchemy.com/v2/PBl0lLA410KGD5_NieO6L")
MULTI_ASSET_ORACLE_ADDRESS = os.getenv(
    "MULTI_ASSET_ORACLE_ADDRESS",
    "0xB44d652354d12Ac56b83112c6ece1fa2ccEfc683",
)

# Hardcoded Supabase base URL (for testing)
SUPABASE_BASE_URL = "https://basxvmmtxwlxylpukqjj.supabase.co/functions/v1"

# Supabase anon key for edge function authentication
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Market-specific edge function endpoints (hardcoded for testing)
MARKET_ENDPOINTS = {
    "H100_HOURLY": f"{SUPABASE_BASE_URL}/fetch-price",  # Existing H100-PERP endpoint
    "H100_HYPERSCALERS_HOURLY": f"{SUPABASE_BASE_URL}/push-h100-hyperscalers-price",  # HyperScalers
    "H100_NON_HYPERSCALERS_HOURLY": f"{SUPABASE_BASE_URL}/push-h100-non-hyperscalers-price",  # non-HyperScalers
}

# Asset IDs (keccak256 hashes)
ASSET_IDS = {
    "H100_HOURLY": "0x82af7da7090d6235dbc9f8cfccfb82eee2e9cb33d50be18eabf66c158261796a",
    "H100_HYPERSCALERS_HOURLY": "0x4907d2c1e61b87a99a260f8529c3c4f9e2374edae1f5ab1464a8e79d0f2c26de",
    "H100_NON_HYPERSCALERS_HOURLY": "0xd6e43f59d2c94773a52e2c20f09762901247d1aaf2090d0b99e85c55c9833626",
}

# Market configuration with database table names
MARKETS = {
    "H100_HOURLY": {
        "market_id": "0x2bc0c3f3ef82289c7da8a9335c83ea4f2b5b8bd62b67c4f4e0dba00b304c2937",
        "market_name": "H100-PERP",
        "display_name": "H100 GPU",
        "table_name": "price_data",  # Existing H100 table
    },
    "H100_HYPERSCALERS_HOURLY": {
        "market_id": "0xf4aa47cc83b0d01511ca8025a996421dda6fbab1764466da4b0de6408d3db2e2",
        "market_name": "H100-HyperScalers-PERP",
        "display_name": "H100 HyperScalers",
        "table_name": "h100_hyperscalers_perp_prices",
    },
    "H100_NON_HYPERSCALERS_HOURLY": {
        "market_id": "0x9d2d658888da74a10ac9263fc14dcac4a834dd53e8edf664b4cc3b2b4a23f214",
        "market_name": "H100-non-HyperScalers-PERP",
        "display_name": "H100 non-HyperScalers",
        "table_name": "h100_non_hyperscalers_perp_prices",
    },
}

# MultiAssetOracle ABI (minimal - just getPrice)
ORACLE_ABI = [
    {
        "type": "function",
        "name": "getPrice",
        "inputs": [
            {"name": "assetId", "type": "bytes32", "internalType": "bytes32"}
        ],
        "outputs": [
            {"name": "", "type": "uint256", "internalType": "uint256"}
        ],
        "stateMutability": "view",
    },
]

@dataclass
class MarketPrices:
    """Container for market price data."""
    oracle_price: float
    market_name: str
    display_name: str


class PricePusher:
    """Fetches prices from blockchain and pushes to database."""

    def __init__(self, rpc_url: str, oracle_address: str, base_url: str, anon_key: str = ""):
        self.base_url = base_url
        self.anon_key = anon_key
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to RPC: {rpc_url}")

        self.oracle = self.w3.eth.contract(
            address=Web3.to_checksum_address(oracle_address),
            abi=ORACLE_ABI,
        )

        print("=" * 60)
        print("ORACLE PRICE DATABASE PUSHER")
        print("=" * 60)
        print(f"Connected to Ethereum")
        print(f"   Chain ID: {self.w3.eth.chain_id}")
        print(f"   Latest block: {self.w3.eth.block_number}")
        print(f"   Oracle: {oracle_address}")
        print(f"   Database URL: {base_url}")
        if self.anon_key:
            print(f"   Supabase Auth: Enabled (using apikey)")
        else:
            print(f"   Supabase Auth: Disabled (may fail on protected endpoints)")
        print("=" * 60)

    def get_oracle_price(self, asset_id: str) -> Optional[float]:
        """Fetch oracle price for an asset."""
        try:
            price_raw = self.oracle.functions.getPrice(asset_id).call()
            return price_raw / 10 ** 18
        except Exception as exc:
            print(f"   ✗ Failed to fetch oracle price: {exc}")
            return None

    def fetch_market_prices(self) -> Dict[str, MarketPrices]:
        """Fetch oracle index prices from blockchain."""
        print("\n" + "=" * 60)
        print("FETCHING ORACLE PRICES FROM BLOCKCHAIN")
        print("=" * 60)

        prices = {}
        for asset_name, asset_id in ASSET_IDS.items():
            market_config = MARKETS.get(asset_name)
            if not market_config:
                continue

            # Fetch oracle price
            oracle_price = self.get_oracle_price(asset_id)
            if oracle_price is None:
                print(f"   ⚠ {market_config['display_name']}: Skipping (no oracle price)")
                continue

            prices[asset_name] = MarketPrices(
                oracle_price=oracle_price,
                market_name=market_config["market_name"],
                display_name=market_config["display_name"],
            )

            print(f"   ✓ {market_config['display_name']}: ${oracle_price:.6f}/hour (Index Price)")

        print("=" * 60)
        return prices

    def push_to_database(self, prices: Dict[str, MarketPrices], dry_run: bool = False) -> Tuple[int, int]:
        """Push oracle index prices to Supabase database via market-specific edge functions.

        Each market has its own endpoint and table for better data isolation.

        Args:
            prices: Dictionary of market prices to push
            dry_run: If True, only show what would be pushed without sending requests

        Returns:
            Tuple of (success_count, failed_count)
        """
        print("\n" + "=" * 60)
        if dry_run:
            print("DRY RUN - SHOWING WHAT WOULD BE PUSHED")
        else:
            print("PUSHING ORACLE PRICES TO DATABASE")
        print("=" * 60)

        block_number = self.w3.eth.block_number
        success_count = 0
        failed_count = 0

        for asset_name, price_data in prices.items():
            market_config = MARKETS.get(asset_name)
            endpoint = MARKET_ENDPOINTS.get(asset_name)

            if not market_config or not endpoint:
                print(f"   ⚠ {asset_name}: Missing configuration, skipping")
                continue

            # Prepare payload based on market
            # H100-PERP uses legacy endpoint that only expects price
            # New markets expect price and block_number
            if asset_name == "H100_HOURLY":
                payload = {
                    "price": str(price_data.oracle_price),
                }
            else:
                payload = {
                    "price": str(price_data.oracle_price),
                    "block_number": block_number,
                }

            # Dry run mode - just show what would be sent
            if dry_run:
                print(f"   ➤ {price_data.display_name}:")
                print(f"      Endpoint: {endpoint}")
                print(f"      Table: {market_config['table_name']}")
                print(f"      Payload: {payload}")
                success_count += 1
                continue

            # Retry logic for actual requests
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    # Build headers with optional Supabase authentication
                    headers = {"Content-Type": "application/json"}
                    if self.anon_key:
                        headers["apikey"] = self.anon_key
                        headers["Authorization"] = f"Bearer {self.anon_key}"
                    
                    # Call market-specific edge function
                    response = requests.post(
                        endpoint,
                        json=payload,
                        headers=headers,
                        timeout=10,
                    )

                    if response.status_code == 200:
                        print(f"   ✓ {price_data.display_name}: Pushed to {market_config['table_name']}")
                        success_count += 1
                        break  # Success, exit retry loop
                    else:
                        error_msg = f"HTTP {response.status_code}"
                        try:
                            error_detail = response.text[:100]  # Limit error message length
                            error_msg += f" - {error_detail}"
                        except:
                            pass

                        if attempt < MAX_RETRIES:
                            print(f"   ⚠ {price_data.display_name}: {error_msg} (retrying {attempt}/{MAX_RETRIES})")
                            time.sleep(RETRY_DELAY)
                        else:
                            print(f"   ✗ {price_data.display_name}: {error_msg} (failed after {MAX_RETRIES} attempts)")
                            failed_count += 1

                except requests.exceptions.Timeout:
                    if attempt < MAX_RETRIES:
                        print(f"   ⚠ {price_data.display_name}: Request timeout (retrying {attempt}/{MAX_RETRIES})")
                        time.sleep(RETRY_DELAY)
                    else:
                        print(f"   ✗ {price_data.display_name}: Request timeout (failed after {MAX_RETRIES} attempts)")
                        failed_count += 1

                except requests.exceptions.RequestException as exc:
                    error_msg = str(exc)[:100]  # Limit error message length
                    if attempt < MAX_RETRIES:
                        print(f"   ⚠ {price_data.display_name}: {error_msg} (retrying {attempt}/{MAX_RETRIES})")
                        time.sleep(RETRY_DELAY)
                    else:
                        print(f"   ✗ {price_data.display_name}: {error_msg} (failed after {MAX_RETRIES} attempts)")
                        failed_count += 1

        print("=" * 60)
        print(f"Results: {success_count} succeeded, {failed_count} failed")
        print("=" * 60)

        return (success_count, failed_count)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Push oracle index prices to Supabase database (vAMM prices tracked by frontend)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Market-specific endpoints:
  - H100-PERP: /fetch-price → price_data table
  - H100-HyperScalers-PERP: /push-h100-hyperscalers-price → h100_hyperscalers_perp_prices table
  - H100-non-HyperScalers-PERP: /push-h100-non-hyperscalers-price → h100_non_hyperscalers_perp_prices table

Each market has its own edge function and database table for better data isolation.
        """
    )
    parser.add_argument(
        "--rpc-url",
        default=SEPOLIA_RPC_URL,
        help="Ethereum RPC URL",
    )
    parser.add_argument(
        "--oracle",
        default=MULTI_ASSET_ORACLE_ADDRESS,
        help="MultiAssetOracle contract address",
    )
    parser.add_argument(
        "--db-url",
        default=SUPABASE_BASE_URL,
        help="Supabase base URL (for edge functions)",
    )
    parser.add_argument(
        "--anon-key",
        default=SUPABASE_ANON_KEY,
        help="Supabase anon key for edge function authentication",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch prices and show what would be pushed without sending requests",
    )
    args = parser.parse_args()

    try:
        # Initialize pusher
        pusher = PricePusher(args.rpc_url, args.oracle, args.db_url, args.anon_key)

        # Fetch prices from blockchain
        prices = pusher.fetch_market_prices()

        if not prices:
            print("\n" + "=" * 60)
            print("ERROR: No prices fetched from blockchain")
            print("=" * 60)
            print("   This may indicate:")
            print("   1. Oracle prices not yet set (run push_to_contract.py first)")
            print("   2. RPC connection issues")
            print("   3. Contract address mismatch")
            print("=" * 60)
            sys.exit(1)

        # Push to database (or dry run)
        success_count, failed_count = pusher.push_to_database(prices, dry_run=args.dry_run)

        # Exit handling
        if args.dry_run:
            print("\n" + "=" * 60)
            print("✓ DRY RUN COMPLETE")
            print("=" * 60)
            print(f"   Would push {success_count} market(s) to database")
            print("   To actually push prices, run without --dry-run")
            print("=" * 60)
            sys.exit(0)

        if failed_count > 0:
            print("\n" + "=" * 60)
            print(f"⚠ WARNING: {failed_count} market(s) failed to update")
            print("=" * 60)
            print("   Troubleshooting:")
            print("   1. Check Supabase edge function logs")
            print("   2. Verify edge function endpoints are deployed")
            print("   3. Ensure database tables exist")
            print("   4. Check network connectivity")
            print("=" * 60)
            sys.exit(1)

        print("\n" + "=" * 60)
        print("✓ SUCCESS! ALL ORACLE PRICES PUSHED TO DATABASE")
        print("=" * 60)
        print(f"   {success_count} market(s) updated successfully")
        print("   Prices are now available for the frontend")
        print("   vAMM mark prices are tracked separately by the frontend")
        print("=" * 60)
        sys.exit(0)

    except ConnectionError as exc:
        print("\n" + "=" * 60)
        print("ERROR: BLOCKCHAIN CONNECTION FAILED")
        print("=" * 60)
        print(f"   {exc}")
        print("\n   Troubleshooting:")
        print("   1. Check SEPOLIA_RPC_URL in .env")
        print("   2. Verify RPC provider is accessible")
        print("   3. Try alternative RPC endpoint (Alchemy, Infura, QuickNode)")
        print("=" * 60)
        sys.exit(1)

    except Exception as exc:
        print("\n" + "=" * 60)
        print("ERROR: OPERATION FAILED")
        print("=" * 60)
        print(f"   {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

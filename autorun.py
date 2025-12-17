#!/usr/bin/env python3
"""Fetch oracle prices from blockchain and push to Supabase database.

This script runs after push_to_contract.py to sync the on-chain oracle prices
to the Supabase database for the frontend to display. It fetches prices from the
MultiAssetOracle contract and pushes them to the database via edge function.

Can be run independently or as part of the automated pipeline.
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
SEPOLIA_RPC_URL = os.getenv("SEPOLIA_RPC_URL", "https://rpc.sepolia.org")
MULTI_ASSET_ORACLE_ADDRESS = os.getenv(
    "MULTI_ASSET_ORACLE_ADDRESS",
    "0xB44d652354d12Ac56b83112c6ece1fa2ccEfc683",
)
SUPABASE_PRICE_FUNCTION_URL = os.getenv(
    "SUPABASE_PRICE_FUNCTION_URL",
    "https://basxvmmtxwlxylpukqjj.supabase.co/functions/v1/fetch-price",
)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Asset IDs (keccak256 hashes)
ASSET_IDS = {
    "H100_HOURLY": "0x82af7da7090d6235dbc9f8cfccfb82eee2e9cb33d50be18eabf66c158261796a",
    "H100_HYPERSCALERS_HOURLY": "0x4907d2c1e61b87a99a260f8529c3c4f9e2374edae1f5ab1464a8e79d0f2c26de",
    "H100_NON_HYPERSCALERS_HOURLY": "0xd6e43f59d2c94773a52e2c20f09762901247d1aaf2090d0b99e85c55c9833626",
}

# Market configuration
MARKETS = {
    "H100_HOURLY": {
        "market_id": "0x2bc0c3f3ef82289c7da8a9335c83ea4f2b5b8bd62b67c4f4e0dba00b304c2937",
        "market_name": "H100-PERP",
        "vamm_address": "0xF7210ccC245323258CC15e0Ca094eBbe2DC2CD85",
        "display_name": "H100 GPU",
    },
    "H100_HYPERSCALERS_HOURLY": {
        "market_id": "0xf4aa47cc83b0d01511ca8025a996421dda6fbab1764466da4b0de6408d3db2e2",
        "market_name": "H100-HyperScalers-PERP",
        "vamm_address": "0xFE1df531084Dcf0Fe379854823bC5d402932Af99",
        "display_name": "H100 HyperScalers",
    },
    "H100_NON_HYPERSCALERS_HOURLY": {
        "market_id": "0x9d2d658888da74a10ac9263fc14dcac4a834dd53e8edf664b4cc3b2b4a23f214",
        "market_name": "H100-non-HyperScalers-PERP",
        "vamm_address": "0x19574B8C91717389231DA5b0579564d6F81a79B0",
        "display_name": "H100 non-HyperScalers",
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

    def __init__(self, rpc_url: str, oracle_address: str, db_url: str):
        self.db_url = db_url

        # Connect to blockchain
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
        print(f"   Database URL: {db_url}")
        print("=" * 60)

    def get_oracle_price(self, asset_id: str) -> Optional[float]:
        """Fetch oracle price for an asset."""
        try:
            price_raw = self.oracle.functions.getPrice(asset_id).call()
            # Convert from 18 decimals to float
            return price_raw / 10**18
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
                print(
                    f"   ⚠ {market_config['display_name']}: Skipping (no oracle price)"
                )
                continue

            prices[asset_name] = MarketPrices(
                oracle_price=oracle_price,
                market_name=market_config["market_name"],
                display_name=market_config["display_name"],
            )

            print(
                f"   ✓ {market_config['display_name']}: ${oracle_price:.6f}/hour (Index Price)"
            )

        print("=" * 60)
        return prices

    def push_to_database(self, prices: Dict[str, MarketPrices]) -> Tuple[int, int]:
        """Push oracle index prices to Supabase database via edge function.

        Returns:
            Tuple of (success_count, failed_count)
        """
        print("\n" + "=" * 60)
        print("PUSHING ORACLE PRICES TO DATABASE")
        print("=" * 60)

        block_number = self.w3.eth.block_number
        success_count = 0
        failed_count = 0

        for asset_name, price_data in prices.items():
            market_config = MARKETS.get(asset_name)
            if not market_config:
                continue

            # Prepare data for price_snapshots table (oracle price only)
            snapshot_data = {
                "market_id": market_config["market_id"],
                "market_name": price_data.market_name,
                "vamm_address": market_config["vamm_address"],
                "oracle_price": str(price_data.oracle_price),
                "block_number": block_number,
            }

            # Retry logic
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    # Call Supabase edge function
                    response = requests.post(
                        self.db_url,
                        json=snapshot_data,
                        headers={"Content-Type": "application/json"},
                        timeout=10,
                    )

                    if response.status_code == 200:
                        print(f"   ✓ {price_data.display_name}: Pushed successfully")
                        success_count += 1
                        break  # Success, exit retry loop
                    else:
                        error_msg = f"HTTP {response.status_code} - {response.text}"
                        if attempt < MAX_RETRIES:
                            print(
                                f"   ⚠ {price_data.display_name}: {error_msg} (retrying {attempt}/{MAX_RETRIES})"
                            )
                            time.sleep(RETRY_DELAY)
                        else:
                            print(f"   ✗ {price_data.display_name}: {error_msg}")
                            failed_count += 1

                except requests.exceptions.RequestException as exc:
                    if attempt < MAX_RETRIES:
                        print(
                            f"   ⚠ {price_data.display_name}: Request failed - {exc} (retrying {attempt}/{MAX_RETRIES})"
                        )
                        time.sleep(RETRY_DELAY)
                    else:
                        print(
                            f"   ✗ {price_data.display_name}: Request failed - {exc}"
                        )
                        failed_count += 1

        print("=" * 60)
        print(f"Results: {success_count} succeeded, {failed_count} failed")
        print("=" * 60)

        return (success_count, failed_count)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch oracle prices from blockchain and push to Supabase database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
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
        default=SUPABASE_PRICE_FUNCTION_URL,
        help="Supabase edge function URL",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch prices but don't push to database",
    )
    args = parser.parse_args()

    try:
        # Initialize pusher
        pusher = PricePusher(args.rpc_url, args.oracle, args.db_url)

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

        # Dry run mode - skip database push
        if args.dry_run:
            print("\n" + "=" * 60)
            print("DRY RUN - SKIPPING DATABASE PUSH")
            print("=" * 60)
            print("   Fetched prices successfully:")
            for asset_name, price_data in prices.items():
                print(f"   {price_data.display_name}: ${price_data.oracle_price:.6f}/hour")
            print("=" * 60)
            print("\n✓ Dry run successful. To push to database, run without --dry-run")
            sys.exit(0)

        # Push to database
        success_count, failed_count = pusher.push_to_database(prices)

        if failed_count > 0:
            print("\n" + "=" * 60)
            print(f"⚠ WARNING: {failed_count} markets failed to update")
            print("=" * 60)
            print("   Check Supabase edge function logs for details")
            sys.exit(1)

        print("\n" + "=" * 60)
        print("✓ SUCCESS! ALL ORACLE PRICES PUSHED TO DATABASE")
        print("=" * 60)
        print(f"   {success_count} market(s) updated successfully")
        print("   Prices are now available for the frontend")
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
        print("   3. Try alternative RPC endpoint")
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

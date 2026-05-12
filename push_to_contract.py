#!/usr/bin/env python3
"""Push H100 index prices to ByteStrike CuOracle on Sepolia."""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Optional

from dotenv import load_dotenv

from cu_oracle_client import (
    DEFAULT_CU_ORACLE_ADDRESS,
    INDEX_ASSET_IDS,
    CuOraclePriceUpdater,
    asset_update,
)

load_dotenv()

SEPOLIA_RPC_URL = os.getenv("SEPOLIA_RPC_URL", "https://ethereum-sepolia-rpc.publicnode.com")
PRIVATE_KEY = os.getenv("ORACLE_UPDATER_PRIVATE_KEY") or os.getenv("PRIVATE_KEY")
CU_ORACLE_ADDRESS = os.getenv("CU_ORACLE_ADDRESS", DEFAULT_CU_ORACLE_ADDRESS)


def read_prices_from_csv(csv_file: str) -> Optional[Dict[str, float]]:
    """Read H100 index prices from gpu_index_calculator.py output."""
    try:
        with open(csv_file, "r", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    except FileNotFoundError:
        print(f"ERROR: CSV file not found: {csv_file}")
        return None
    except Exception as exc:
        print(f"ERROR: Failed to read CSV {csv_file}: {exc}")
        return None

    if not rows:
        print(f"ERROR: CSV file is empty: {csv_file}")
        return None

    latest = rows[-1]
    required_columns = ["Full_Index_Price", "Hyperscalers_Only_Price", "Non_Hyperscalers_Only_Price"]
    missing = [column for column in required_columns if column not in latest]
    if missing:
        print(f"ERROR: CSV missing required columns: {missing}")
        print(f"Available columns: {list(latest.keys())}")
        return None

    try:
        prices = {
            "H100_HOURLY": float(latest["Full_Index_Price"]),
            "H100_HYPERSCALERS_HOURLY": float(latest["Hyperscalers_Only_Price"]),
            "H100_NON_HYPERSCALERS_HOURLY": float(latest["Non_Hyperscalers_Only_Price"]),
        }
    except (TypeError, ValueError) as exc:
        print(f"ERROR: Invalid price values in CSV: {exc}")
        return None

    print("=" * 60)
    print("H100 INDEX PRICES FROM PIPELINE")
    print("=" * 60)
    print(f"Calculation Date: {latest.get('Calculation_Date', 'unknown')}")
    for name, price in prices.items():
        config = INDEX_ASSET_IDS[name]
        print(f"{name} -> {config['market']} ({config['asset_symbol']}): ${price:.6f}/hr")
    print("=" * 60)
    return prices


def log_update(prices: Dict[str, float], commit_hashes, reveal_hashes, updater: CuOraclePriceUpdater) -> None:
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "network": "sepolia",
        "contract_type": "CuOracle",
        "cu_oracle": updater.oracle_address,
        "updater_address": updater.address,
        "commit_txs": commit_hashes,
        "reveal_txs": reveal_hashes,
        "prices": {
            name: {
                "market": INDEX_ASSET_IDS[name]["market"],
                "asset_symbol": INDEX_ASSET_IDS[name]["asset_symbol"],
                "asset_id": INDEX_ASSET_IDS[name]["asset_id"],
                "price_usd": price,
            }
            for name, price in prices.items()
        },
    }

    log_file = "contract_update_log.json"
    logs = []
    if os.path.exists(log_file):
        try:
            with open(log_file, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
                logs = loaded if isinstance(loaded, list) else []
        except Exception:
            logs = []

    logs.append(log_entry)
    logs = logs[-100:]
    with open(log_file, "w", encoding="utf-8") as handle:
        json.dump(logs, handle, indent=2)
    print(f"Logged update to {log_file}")


def build_updates(prices: Dict[str, float]):
    updates = []
    for name, price in prices.items():
        if price <= 0:
            raise ValueError(f"{name} price must be positive, got {price}")
        if price > 100:
            print(f"WARNING: {name} price ${price:.2f}/hr seems unusually high")
        updates.append(asset_update(name, INDEX_ASSET_IDS[name], price))
    return updates


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Push H100 GPU index prices to ByteStrike CuOracle",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--csv", default="h100_gpu_index.csv", help="Path to GPU index CSV")
    parser.add_argument(
        "--manual-prices",
        nargs=3,
        type=float,
        metavar=("FULL_INDEX", "HYPERSCALERS", "NON_HYPERSCALERS"),
        help="Manual price override. Example: --manual-prices 3.75 4.20 2.95",
    )
    parser.add_argument("--no-verify", action="store_true", help="Skip read-back verification")
    parser.add_argument("--dry-run", action="store_true", help="Print planned updates without sending transactions")
    parser.add_argument(
        "--register",
        action="store_true",
        help="Accepted for backwards compatibility; assets are already registered in CuOracle",
    )
    args = parser.parse_args()

    if args.register:
        print("NOTE: --register is ignored; CuOracle assets were registered during protocol deployment.")

    if args.manual_prices:
        prices = {
            "H100_HOURLY": args.manual_prices[0],
            "H100_HYPERSCALERS_HOURLY": args.manual_prices[1],
            "H100_NON_HYPERSCALERS_HOURLY": args.manual_prices[2],
        }
    else:
        prices = read_prices_from_csv(args.csv)
        if prices is None:
            sys.exit(1)

    try:
        updates = build_updates(prices)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    if args.dry_run:
        print("\nDRY RUN - no transactions will be sent")
        for update in updates:
            print(f"  {update.asset_name} -> {update.market}: {update.price_formatted}")
        sys.exit(0)

    if not PRIVATE_KEY:
        print("ERROR: Private key not configured")
        print("Set ORACLE_UPDATER_PRIVATE_KEY or PRIVATE_KEY. The key must own CuOracle for reveal.")
        sys.exit(1)

    try:
        updater = CuOraclePriceUpdater(
            rpc_url=SEPOLIA_RPC_URL,
            private_key=PRIVATE_KEY,
            oracle_address=CU_ORACLE_ADDRESS,
        )
        commit_hashes, reveal_hashes = updater.commit_and_reveal(updates, verify=not args.no_verify)
        log_update(prices, commit_hashes, reveal_hashes, updater)
    except Exception as exc:
        print("\nERROR: CUORACLE UPDATE FAILED")
        print(f"  {exc}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    print("\nSUCCESS: H100 index prices updated on ByteStrike CuOracle")
    print("Reveal transactions:")
    for tx_hash in reveal_hashes:
        print(f"  https://sepolia.etherscan.io/tx/{tx_hash}")


if __name__ == "__main__":
    main()

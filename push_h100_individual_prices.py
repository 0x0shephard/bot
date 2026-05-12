#!/usr/bin/env python3
"""Push AWS/Azure/GCP H100 provider prices to ByteStrike CuOracle."""

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from typing import List

from dotenv import load_dotenv

from cu_oracle_client import (
    DEFAULT_CU_ORACLE_ADDRESS,
    H100_PROVIDER_ASSET_IDS,
    CuOraclePriceUpdater,
    OraclePriceUpdate,
    asset_update,
)

load_dotenv()

SEPOLIA_RPC_URL = os.getenv("SEPOLIA_RPC_URL", "https://ethereum-sepolia-rpc.publicnode.com")
PRIVATE_KEY = os.getenv("ORACLE_UPDATER_PRIVATE_KEY") or os.getenv("PRIVATE_KEY") or os.getenv("WALLET_PRIVATE_KEY")
CU_ORACLE_ADDRESS = os.getenv("CU_ORACLE_ADDRESS", DEFAULT_CU_ORACLE_ADDRESS)


def log_updates(updates: List[OraclePriceUpdate], commit_hashes, reveal_hashes, updater: CuOraclePriceUpdater) -> None:
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "network": "sepolia",
        "contract_type": "CuOracle",
        "cu_oracle": updater.oracle_address,
        "updater_address": updater.address,
        "commit_txs": commit_hashes,
        "reveal_txs": reveal_hashes,
        "updates": [
            {
                "asset_name": update.asset_name,
                "market": update.market,
                "asset_id": update.asset_id,
                "price_usd": update.price_usd,
                "price_scaled": update.price_scaled,
            }
            for update in updates
        ],
    }

    log_file = "h100_provider_price_log.json"
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


def maybe_add_update(updates: List[OraclePriceUpdate], arg_name: str, asset_name: str, price: float) -> None:
    if price is None:
        return
    if math.isnan(price):
        print(f"WARNING: Skipping {asset_name}; --{arg_name} is NaN")
        return
    if price <= 0:
        raise ValueError(f"{asset_name} price must be positive, got {price}")
    if price > 100:
        print(f"WARNING: {asset_name} price ${price:.2f}/hr seems unusually high")
    updates.append(asset_update(asset_name, H100_PROVIDER_ASSET_IDS[asset_name], price))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Update AWS/Azure/GCP H100 prices on ByteStrike CuOracle",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python push_h100_individual_prices.py --aws 3.85 --azure 2.12 --gcp 3.88
  python push_h100_individual_prices.py --aws 3.85
  python push_h100_individual_prices.py --show
        """,
    )
    parser.add_argument("--aws", type=float, help="AWS H100 price in USD/hour")
    parser.add_argument("--azure", type=float, help="Azure H100 price in USD/hour")
    parser.add_argument("--gcp", type=float, help="GCP H100 price in USD/hour")
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Accepted for backwards compatibility; CuOracle reveals are sent per asset",
    )
    parser.add_argument("--show", action="store_true", help="Show current prices and exit")
    parser.add_argument("--dry-run", action="store_true", help="Print planned updates without sending transactions")
    parser.add_argument("--no-verify", action="store_true", help="Skip read-back verification")
    args = parser.parse_args()

    if args.batch:
        print("NOTE: --batch is accepted for compatibility; CuOracle has single-asset commit/reveal methods.")

    if not PRIVATE_KEY and not args.dry_run:
        print("ERROR: Private key not configured")
        print("Set ORACLE_UPDATER_PRIVATE_KEY, PRIVATE_KEY, or WALLET_PRIVATE_KEY. The key must own CuOracle.")
        sys.exit(1)

    try:
        updates: List[OraclePriceUpdate] = []
        maybe_add_update(updates, "aws", "AWS_H100_HOURLY", args.aws)
        maybe_add_update(updates, "azure", "AZURE_H100_HOURLY", args.azure)
        maybe_add_update(updates, "gcp", "GCP_H100_HOURLY", args.gcp)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    if args.dry_run:
        print("DRY RUN - no transactions will be sent")
        for update in updates:
            print(f"  {update.asset_name} -> {update.market}: {update.price_formatted}")
        sys.exit(0)

    try:
        updater = CuOraclePriceUpdater(
            rpc_url=SEPOLIA_RPC_URL,
            private_key=PRIVATE_KEY,
            oracle_address=CU_ORACLE_ADDRESS,
        )

        print("\nCurrent H100 provider prices:")
        for name, config in H100_PROVIDER_ASSET_IDS.items():
            current = updater.get_latest_price_usd(config["asset_id"])
            if current is None:
                print(f"  {name} ({config['market']}): no price set")
            else:
                print(f"  {name} ({config['market']}): ${current:.6f}/hr")

        if args.show:
            sys.exit(0)

        if not updates:
            print("\nNo price updates specified.")
            print("Use --aws, --azure, and/or --gcp to specify prices.")
            sys.exit(1)

        commit_hashes, reveal_hashes = updater.commit_and_reveal(updates, verify=not args.no_verify)
        log_updates(updates, commit_hashes, reveal_hashes, updater)
    except Exception as exc:
        print("\nERROR: CUORACLE UPDATE FAILED")
        print(f"  {exc}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    print("\nSUCCESS: H100 provider prices updated on ByteStrike CuOracle")
    print("Reveal transactions:")
    for tx_hash in reveal_hashes:
        print(f"  https://sepolia.etherscan.io/tx/{tx_hash}")


if __name__ == "__main__":
    main()

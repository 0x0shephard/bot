#!/usr/bin/env python3
"""Index Oracle price updater script for H100 GPU rental rates."""

import csv
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence, Tuple

from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3

load_dotenv()

SEPOLIA_RPC_URL = os.getenv("SEPOLIA_RPC_URL", "https://rpc.sepolia.org")
PRIVATE_KEY = os.getenv("ORACLE_UPDATER_PRIVATE_KEY") or os.getenv("WALLET_PRIVATE_KEY")
INDEX_ORACLE_ADDRESS = os.getenv(
    "INDEX_ORACLE_ADDRESS",
    "0x3cA2Da03e4b6dB8fe5a24c22Cf5EB2A34B59cbad",  # UpdatableETHOracle for H100 GPU prices
)
ASSET_LABEL = os.getenv("ORACLE_ASSET_LABEL", "H100_GPU_HOURLY")
PRICE_DECIMALS = int(os.getenv("ORACLE_DECIMALS", "18"))
BOT_MODE = os.getenv("BOT_MODE", "false").lower() in ("true", "1", "yes")

# Simple oracle ABI - just setPrice and getPrice
INDEX_ORACLE_ABI: Sequence[dict] = [
    {
        "type": "function",
        "name": "setPrice",
        "inputs": [
            {"name": "newPrice", "type": "uint256", "internalType": "uint256"},
        ],
        "outputs": [],
        "stateMutability": "nonpayable",
    },
    {
        "type": "function",
        "name": "getPrice",
        "inputs": [],
        "outputs": [
            {"name": "", "type": "uint256", "internalType": "uint256"}
        ],
        "stateMutability": "view",
    },
    {
        "type": "event",
        "name": "PriceUpdated",
        "inputs": [
            {"name": "newPrice", "type": "uint256", "indexed": True, "internalType": "uint256"},
            {"name": "timestamp", "type": "uint256", "indexed": False, "internalType": "uint256"},
        ],
        "anonymous": False,
    },
]


@dataclass
class PriceData:
    price_raw: int

    @property
    def price(self) -> float:
        return self.price_raw / 10 ** PRICE_DECIMALS


class IndexOraclePriceUpdater:
    """Update H100 GPU rental price on the index oracle contract.

    This oracle is used by the vAMM for funding rate calculations.
    It's a simple updatable oracle with setPrice(uint256) function.
    """

    def __init__(
        self,
        rpc_url: str,
        private_key: str,
        contract_address: str,
        asset_label: str,
        decimals: int,
    ):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to Sepolia RPC: {rpc_url}")
        self.account = Account.from_key(private_key)
        self.address = self.account.address
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=INDEX_ORACLE_ABI,
        )
        self.decimals = decimals
        self.asset_label = asset_label
        balance_eth = self.w3.from_wei(self.w3.eth.get_balance(self.address), "ether")
        print("Connected to Sepolia testnet")
        print(f"   Chain ID: {self.w3.eth.chain_id}")
        print(f"   Latest block: {self.w3.eth.block_number}")
        print(f"   Updater address: {self.address}")
        print(f"   Balance: {balance_eth:.4f} ETH")
        print(f"   Index Oracle: {contract_address}")
        print(f"   Asset: {self.asset_label}")
        print(f"   Price decimals: {self.decimals}")
        latest = self.get_current_price()
        if latest.price_raw:
            print(
                f"   Current oracle price: ${latest.price:.6f}/hr"
            )
        else:
            print("   No price set yet")

    def _build_dynamic_fee(self) -> Tuple[int, int]:
        base_fee = self.w3.eth.gas_price
        max_priority = self.w3.to_wei(1, "gwei")
        max_fee = max(base_fee * 2, max_priority * 2)
        return max_fee, max_priority

    def _send_transaction(self, func, gas_limit: int) -> Tuple[str, dict]:
        """Build, sign, and send a transaction to the blockchain.

        Compatible with modern Web3.py versions (v6+).
        """
        max_fee, max_priority = self._build_dynamic_fee()
        tx = func.build_transaction(
            {
                "from": self.address,
                "nonce": self.w3.eth.get_transaction_count(self.address),
                "gas": gas_limit,
                "maxFeePerGas": max_fee,
                "maxPriorityFeePerGas": max_priority,
                "chainId": 11155111,
            }
        )
        signed = self.account.sign_transaction(tx)

        # Modern Web3.py (v6+) uses 'raw_transaction' or 'rawTransaction' attributes
        # Try both for maximum compatibility
        if hasattr(signed, "raw_transaction"):
            raw_tx = signed.raw_transaction
        elif hasattr(signed, "rawTransaction"):
            raw_tx = signed.rawTransaction
        else:
            # Fallback: some versions return bytes directly
            raw_tx = signed

        tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        return tx_hash.hex(), dict(receipt)

    def get_current_price(self) -> PriceData:
        """Get current price from the oracle."""
        try:
            price_raw = self.contract.functions.getPrice().call()
            return PriceData(price_raw=price_raw)
        except Exception:
            return PriceData(price_raw=0)

    def should_update_price(self, new_price_usd: float, threshold_percent: float = 1.0) -> bool:
        """Check if the new price differs enough from current to warrant an update.

        Args:
            new_price_usd: New price to potentially set
            threshold_percent: Minimum % change required (default: 1%)

        Returns:
            True if price should be updated, False if change is too small
        """
        current = self.get_current_price()
        if current.price_raw == 0:
            return True  # No price set yet, always update

        delta = abs(new_price_usd - current.price)
        change_pct = (delta / current.price) * 100 if current.price else 0

        return change_pct >= threshold_percent

    def update_price(self, price_usd: float, skip_verification: bool = False) -> str:
        """Update the oracle price to the new H100 GPU rental rate.

        Args:
            price_usd: New price in USD per hour (e.g., 3.78)
            skip_verification: If True, skip on-chain verification (faster for bots)

        Returns:
            Transaction hash of the update transaction
        """
        price_scaled = int(price_usd * (10 ** self.decimals))
        current = self.get_current_price()

        if current.price_raw:
            delta = price_usd - current.price
            change_pct = (delta / current.price) * 100 if current.price else 0
            print(f"Current oracle: ${current.price:.6f}/hr (Δ {change_pct:+.2f}%)")

        print(f"Updating to: ${price_usd:.6f}/hr")
        print("Sending transaction...")

        tx_hash, receipt = self._send_transaction(
            self.contract.functions.setPrice(price_scaled),
            gas_limit=100_000,
        )

        print(f"Transaction confirmed: {tx_hash}")
        print(f"Gas used: {receipt['gasUsed']:,}")

        # Verify the update (optional for bot mode)
        if not skip_verification:
            latest = self.get_current_price()
            if latest.price_raw == price_scaled:
                print(f"✓ On-chain price verified: ${latest.price:.6f}/hr")
            else:
                print(f"⚠ WARNING: On-chain price mismatch!")
                print(f"   Expected: ${price_usd:.6f}/hr")
                print(f"   Got: ${latest.price:.6f}/hr")
        else:
            print("⏩ Skipping verification (bot mode)")

        self.log_update(price_usd, tx_hash, receipt['blockNumber'])
        return tx_hash

    def read_price_from_csv(self, csv_file: str) -> Optional[float]:
        """Read GPU price from pipeline-generated CSV file.

        Expected format: h100_gpu_index.csv with columns:
        - Full_Index_Price: Weighted average price across all providers
        - Calculation_Date: Timestamp of calculation
        - Hyperscalers_Only_Price (optional): Price from major cloud providers only
        - Non_Hyperscalers_Only_Price (optional): Price from smaller providers only
        """
        try:
            with open(csv_file, "r", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                rows = list(reader)
        except FileNotFoundError:
            print(f"ERROR: CSV file not found: {csv_file}")
            print("   Ensure the GPU price pipeline has completed successfully")
            print("   Expected file from: gpu_index_calculator.py output")
            return None
        except Exception as exc:
            print(f"ERROR: Failed to read CSV {csv_file}: {exc}")
            return None

        if not rows:
            print(f"ERROR: CSV file is empty: {csv_file}")
            print("   The pipeline may have failed to generate data")
            return None

        # Get the latest index price (last row)
        latest = rows[-1]

        # Validate required columns exist
        if "Full_Index_Price" not in latest:
            print(f"ERROR: CSV missing 'Full_Index_Price' column")
            print(f"   Available columns: {list(latest.keys())}")
            print("   Ensure you're using output from gpu_index_calculator.py")
            return None

        try:
            price = float(latest["Full_Index_Price"])
        except (ValueError, TypeError) as exc:
            print(f"ERROR: Invalid price value: {latest['Full_Index_Price']}")
            print(f"   Parse error: {exc}")
            return None

        timestamp = latest.get("Calculation_Date", "unknown")
        print("="*60)
        print("GPU INDEX PRICE FROM PIPELINE")
        print("="*60)
        print(f"   Calculation Date: {timestamp}")
        print(f"   Full Index Price: ${price:.6f}/hour")

        # Show additional index data if available
        if "Hyperscalers_Only_Price" in latest:
            hyperscaler_price = float(latest["Hyperscalers_Only_Price"])
            print(f"   Hyperscalers Only: ${hyperscaler_price:.6f}/hour")
        if "Non_Hyperscalers_Only_Price" in latest:
            non_hyperscaler_price = float(latest["Non_Hyperscalers_Only_Price"])
            print(f"   Non-Hyperscalers: ${non_hyperscaler_price:.6f}/hour")
        print("="*60)

        return price

    def log_update(self, price_usd: float, tx_hash: str, block_number: int) -> None:
        """Log blockchain update to JSON file for pipeline tracking.

        Maintains a rolling log of the last 100 updates with complete metadata.
        Compatible with pipeline monitoring and debugging tools.
        """
        from datetime import timezone

        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "index_price_usd": price_usd,
            "index_price_scaled": int(price_usd * (10 ** self.decimals)),
            "tx_hash": tx_hash,
            "block_number": block_number,
            "contract_address": INDEX_ORACLE_ADDRESS,
            "asset_label": self.asset_label,
            "network": "sepolia",
            "decimals": self.decimals,
            "updater_address": self.address,
            "etherscan_url": f"https://sepolia.etherscan.io/tx/{tx_hash}",
        }

        log_file = "contract_update_log.json"
        logs = []

        # Load existing logs
        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8") as handle:
                    logs = json.load(handle)
                if not isinstance(logs, list):
                    print(f"WARNING: {log_file} has invalid format, resetting log")
                    logs = []
            except json.JSONDecodeError as exc:
                print(f"WARNING: Failed to parse {log_file}: {exc}")
                print("   Creating new log file")
                logs = []
            except Exception as exc:
                print(f"WARNING: Error reading {log_file}: {exc}")
                logs = []

        # Append new entry and keep last 100
        logs.append(log_entry)
        logs = logs[-100:]

        # Write updated logs
        try:
            with open(log_file, "w", encoding="utf-8") as handle:
                json.dump(logs, handle, indent=2)
            print(f"✓ Logged update to {log_file} (entry {len(logs)}/100)")
        except Exception as exc:
            print(f"ERROR: Failed to write log file: {exc}")


def main() -> None:
    """Main entry point for pushing GPU index prices to blockchain.

    This script integrates with the GPU pricing pipeline by:
    1. Reading the final index price from h100_gpu_index.csv
    2. Executing a setPrice transaction on the Index Oracle contract
    3. Logging the update for pipeline monitoring and debugging

    Pipeline Integration:
    - Input: h100_gpu_index.csv (from gpu_index_calculator.py)
    - Output: contract_update_log.json (transaction history)
    - Environment: Requires SEPOLIA_RPC_URL and ORACLE_UPDATER_PRIVATE_KEY
    """
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Push H100 GPU index price to Index Oracle smart contract",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Pipeline Integration:
  This script is designed to work as Step 7 of the GPU pricing pipeline.
  It expects h100_gpu_index.csv to be generated by gpu_index_calculator.py.

Environment Variables:
  SEPOLIA_RPC_URL              Ethereum RPC endpoint (default: https://rpc.sepolia.org)
  ORACLE_UPDATER_PRIVATE_KEY   Wallet private key for signing transactions
  INDEX_ORACLE_ADDRESS         Index oracle contract address (H100 GPU price feed)
  ORACLE_ASSET_LABEL           Asset identifier (default: H100_GPU_HOURLY)
  ORACLE_DECIMALS              Price decimals (default: 18)

Examples:
  # Use pipeline-generated CSV (default)
  python push_to_contract.py

  # Use custom CSV file
  python push_to_contract.py --csv custom_prices.csv

  # Override with manual price (bypass CSV)
  python push_to_contract.py --price 3.78

  # Bot mode with fast execution (no verification)
  python push_to_contract.py --csv h100_gpu_index.csv --no-verify

  # Only update if price changed by at least 0.5%
  python push_to_contract.py --threshold 0.5

  # Bot mode with threshold (recommended for automated pipelines)
  python push_to_contract.py --csv h100_gpu_index.csv --no-verify --threshold 0.5

  # Dry run to check price difference without updating
  python push_to_contract.py --dry-run --threshold 1.0
        """
    )
    parser.add_argument(
        "--csv",
        default="h100_gpu_index.csv",
        help="Path to GPU index CSV (default: h100_gpu_index.csv from pipeline)",
    )
    parser.add_argument(
        "--price",
        type=float,
        help="Manual price override (USD/hour). Bypasses CSV reading.",
    )
    parser.add_argument("--asset-label", default=ASSET_LABEL, help="Asset label for oracle")
    parser.add_argument(
        "--decimals",
        type=int,
        default=PRICE_DECIMALS,
        help="Price decimals for on-chain storage",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip price verification after update (faster for bots)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.0,
        help="Minimum %% price change required for update (default: 0.0 = always update). Use 1.0 for 1%% threshold",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check price difference without executing update",
    )
    args = parser.parse_args()

    # Validate environment
    if not PRIVATE_KEY:
        print("=" * 60)
        print("ERROR: Private key not configured")
        print("=" * 60)
        print("Set one of these environment variables:")
        print("  - ORACLE_UPDATER_PRIVATE_KEY")
        print("  - WALLET_PRIVATE_KEY")
        print("\nFor GitHub Actions, add as a repository secret.")
        print("=" * 60)
        sys.exit(1)

    # Initialize oracle updater
    print("\n" + "=" * 60)
    print("INDEX ORACLE PRICE UPDATER")
    print("=" * 60)
    try:
        updater = IndexOraclePriceUpdater(
            rpc_url=SEPOLIA_RPC_URL,
            private_key=PRIVATE_KEY,
            contract_address=INDEX_ORACLE_ADDRESS,
            asset_label=args.asset_label,
            decimals=args.decimals,
        )
    except ConnectionError as exc:
        print(f"\nERROR: Failed to connect to blockchain: {exc}")
        print("Check SEPOLIA_RPC_URL and network connectivity")
        sys.exit(1)
    except Exception as exc:
        print(f"\nERROR: Failed to initialize updater: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Determine price source
    if args.price is not None:
        price = args.price
        print("\n" + "=" * 60)
        print("MANUAL PRICE OVERRIDE")
        print("=" * 60)
        print(f"   Using manual price: ${price:.6f}/hour")
        print("   (Bypassing CSV pipeline data)")
        print("=" * 60)
    else:
        price = updater.read_price_from_csv(args.csv)
        if price is None:
            print("\n" + "=" * 60)
            print("ERROR: Unable to read price from CSV")
            print("=" * 60)
            print("Possible causes:")
            print("  1. Pipeline has not completed yet (run gpu_index_calculator.py)")
            print("  2. CSV file missing or corrupted")
            print("  3. Invalid CSV format")
            print("\nTo bypass, use: --price <value>")
            print("=" * 60)
            sys.exit(1)

    # Validate price
    if price <= 0:
        print(f"\nERROR: Price must be greater than zero (got {price})")
        print("Check pipeline data or manual price input")
        sys.exit(1)

    if price > 100:
        print(f"\nWARNING: Price ${price:.2f}/hour seems unusually high")
        print("Expected range: $1-10/hour for H100 GPUs")
        print("Proceeding anyway...\n")

    # Check if update is needed based on threshold
    if args.threshold > 0:
        should_update = updater.should_update_price(price, threshold_percent=args.threshold)
        current = updater.get_current_price()

        if current.price_raw > 0:
            delta = abs(price - current.price)
            change_pct = (delta / current.price) * 100 if current.price else 0

            print("\n" + "=" * 60)
            print("PRICE CHANGE ANALYSIS")
            print("=" * 60)
            print(f"   Current on-chain: ${current.price:.6f}/hr")
            print(f"   New price: ${price:.6f}/hr")
            print(f"   Change: {change_pct:+.2f}%")
            print(f"   Threshold: {args.threshold}%")
            print(f"   Update needed: {'YES' if should_update else 'NO'}")
            print("=" * 60)

            if not should_update:
                print(f"\n⏩ Skipping update - price change ({change_pct:.2f}%) below threshold ({args.threshold}%)")
                if args.dry_run:
                    print("   (Dry run mode)")
                sys.exit(0)

    # Dry run mode - exit before updating
    if args.dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN MODE - NO UPDATE EXECUTED")
        print("=" * 60)
        print(f"   Would update to: ${price:.6f}/hr")
        print("=" * 60)
        sys.exit(0)

    # Execute blockchain update
    print("\n" + "=" * 60)
    print("EXECUTING BLOCKCHAIN UPDATE")
    print("=" * 60)
    try:
        tx_hash = updater.update_price(price, skip_verification=args.no_verify)
        print("\n" + "=" * 60)
        print("SUCCESS! PRICE UPDATED ON-CHAIN")
        print("=" * 60)
        print(f"   Transaction: {tx_hash}")
        print(f"   Etherscan: https://sepolia.etherscan.io/tx/{tx_hash}")
        print(f"   Price: ${price:.6f}/hour")
        print("=" * 60)
        sys.exit(0)
    except Exception as exc:
        print("\n" + "=" * 60)
        print("ERROR: BLOCKCHAIN UPDATE FAILED")
        print("=" * 60)
        print(f"   {exc}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

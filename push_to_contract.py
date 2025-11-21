#!/usr/bin/env python3
"""CuOracle price updater script."""

import csv
import json
import os
import secrets
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
CU_ORACLE_ADDRESS = os.getenv(
    "CU_ORACLE_ADDRESS",
    "0xB28502a76ED13877fCCd33dc9301b8250b14efd5",
)
ASSET_ID_HEX = os.getenv("CU_ORACLE_ASSET_ID")
ASSET_LABEL = os.getenv("CU_ORACLE_ASSET_LABEL", "H100_GPU_HOURLY")
PRICE_DECIMALS = int(os.getenv("CU_ORACLE_DECIMALS", "18"))
COMMIT_DELAY_SECONDS = float(os.getenv("CU_ORACLE_COMMIT_DELAY_SECONDS", "2"))

CU_ORACLE_ABI: Sequence[dict] = [
    {
        "type": "function",
        "name": "commitPrice",
        "inputs": [
            {"name": "assetId", "type": "bytes32", "internalType": "bytes32"},
            {"name": "commit", "type": "bytes32", "internalType": "bytes32"},
        ],
        "outputs": [],
        "stateMutability": "nonpayable",
    },
    {
        "type": "function",
        "name": "updatePrices",
        "inputs": [
            {"name": "assetId", "type": "bytes32", "internalType": "bytes32"},
            {"name": "price", "type": "uint256", "internalType": "uint256"},
            {"name": "nonce", "type": "bytes32", "internalType": "bytes32"},
        ],
        "outputs": [],
        "stateMutability": "nonpayable",
    },
    {
        "type": "function",
        "name": "getLatestPrice",
        "inputs": [
            {"name": "assetId", "type": "bytes32", "internalType": "bytes32"},
        ],
        "outputs": [
            {
                "components": [
                    {"name": "price", "type": "uint256", "internalType": "uint256"},
                    {"name": "lastUpdatedAt", "type": "uint256", "internalType": "uint256"},
                ],
                "name": "",
                "type": "tuple",
                "internalType": "struct CuOracle.PriceData",
            }
        ],
        "stateMutability": "view",
    },
]


@dataclass
class PriceData:
    price_raw: int
    last_updated: int

    @property
    def price(self) -> float:
        return self.price_raw / 10 ** PRICE_DECIMALS


class CuOraclePriceUpdater:
    def __init__(
        self,
        rpc_url: str,
        private_key: str,
        contract_address: str,
        asset_id_hex: Optional[str],
        asset_label: str,
        decimals: int,
        commit_delay: float,
    ):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to Sepolia RPC: {rpc_url}")
        self.account = Account.from_key(private_key)
        self.address = self.account.address
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=CU_ORACLE_ABI,
        )
        self.decimals = decimals
        self.commit_delay = commit_delay
        self.asset_label = asset_label
        self.asset_id = self._derive_asset_id(asset_id_hex, asset_label)
        self.asset_id_hex = Web3.to_hex(self.asset_id)
        balance_eth = self.w3.from_wei(self.w3.eth.get_balance(self.address), "ether")
        print("Connected to Sepolia testnet")
        print(f"   Chain ID: {self.w3.eth.chain_id}")
        print(f"   Latest block: {self.w3.eth.block_number}")
        print(f"   Updater address: {self.address}")
        print(f"   Balance: {balance_eth:.4f} ETH")
        print(f"   CuOracle: {contract_address}")
        print(f"   Asset ID: {self.asset_id_hex} (label='{self.asset_label}')")
        print(f"   Price decimals: {self.decimals}")
        latest = self.get_current_price()
        if latest.price_raw:
            print(
                f"   Current oracle price: ${latest.price:.6f}/hr at block timestamp {latest.last_updated}"
            )
        else:
            print("   No price set yet for this asset")

    @staticmethod
    def _derive_asset_id(asset_id_hex: Optional[str], label: str) -> bytes:
        if asset_id_hex:
            data = Web3.to_bytes(hexstr=asset_id_hex)
            if len(data) > 32:
                raise ValueError("CU_ORACLE_ASSET_ID must be <= 32 bytes")
            return data.rjust(32, b"\x00")
        return Web3.keccak(text=label)

    def _build_dynamic_fee(self) -> Tuple[int, int]:
        base_fee = self.w3.eth.gas_price
        max_priority = self.w3.to_wei(1, "gwei")
        max_fee = max(base_fee * 2, max_priority * 2)
        return max_fee, max_priority

    def _send_transaction(self, func, gas_limit: int) -> Tuple[str, dict]:
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
        raw_tx = getattr(signed, "raw_transaction", signed.rawTransaction)
        tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        return tx_hash.hex(), dict(receipt)

    def get_current_price(self) -> PriceData:
        try:
            price_raw, last_updated = self.contract.functions.getLatestPrice(self.asset_id).call()
            return PriceData(price_raw=price_raw, last_updated=last_updated)
        except Exception:
            return PriceData(price_raw=0, last_updated=0)

    def update_price(self, price_usd: float) -> str:
        price_scaled = int(price_usd * (10 ** self.decimals))
        nonce_bytes32 = secrets.token_bytes(32)
        current = self.get_current_price()
        if current.price_raw:
            delta = price_usd - current.price
            change_pct = (delta / current.price) * 100 if current.price else 0
            print(f"Current oracle: ${current.price:.6f}/hr (Δ {change_pct:+.2f}%)")
        commit_hash = Web3.keccak(
            self.w3.codec.encode_abi(["uint256", "bytes32"], [price_scaled, nonce_bytes32])
        )
        print("Committing price...")
        commit_tx, _ = self._send_transaction(
            self.contract.functions.commitPrice(self.asset_id, commit_hash),
            gas_limit=150_000,
        )
        print(f"Commit tx: {commit_tx}")
        delay = max(self.commit_delay, 1)
        print(f"Waiting {delay:.1f}s before reveal")
        time.sleep(delay)
        print("Revealing price...")
        reveal_tx, _ = self._send_transaction(
            self.contract.functions.updatePrices(
                self.asset_id,
                price_scaled,
                nonce_bytes32,
            ),
            gas_limit=250_000,
        )
        print(f"Reveal tx: {reveal_tx}")
        latest = self.get_current_price()
        if latest.price_raw == price_scaled:
            print(f"On-chain price now ${latest.price:.6f}/hr")
        self.log_update(price_usd, reveal_tx, latest.last_updated)
        return reveal_tx

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
            "contract_address": CU_ORACLE_ADDRESS,
            "asset_id": self.asset_id_hex,
            "asset_label": self.asset_label,
            "network": "sepolia",
            "decimals": self.decimals,
            "updater_address": self.address,
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
    2. Executing a commit-reveal transaction on the CuOracle contract
    3. Logging the update for pipeline monitoring and debugging

    Pipeline Integration:
    - Input: h100_gpu_index.csv (from gpu_index_calculator.py)
    - Output: contract_update_log.json (transaction history)
    - Environment: Requires SEPOLIA_RPC_URL and ORACLE_UPDATER_PRIVATE_KEY
    """
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Push H100 GPU index price to CuOracle smart contract",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Pipeline Integration:
  This script is designed to work as Step 7 of the GPU pricing pipeline.
  It expects h100_gpu_index.csv to be generated by gpu_index_calculator.py.

Environment Variables:
  SEPOLIA_RPC_URL              Ethereum RPC endpoint (default: https://rpc.sepolia.org)
  ORACLE_UPDATER_PRIVATE_KEY   Wallet private key for signing transactions
  CU_ORACLE_ADDRESS            Smart contract address
  CU_ORACLE_ASSET_LABEL        Asset identifier (default: H100_GPU_HOURLY)
  CU_ORACLE_DECIMALS           Price decimals (default: 18)
  CU_ORACLE_COMMIT_DELAY_SECONDS  Delay between commit/reveal (default: 2)

Examples:
  # Use pipeline-generated CSV (default)
  python push_to_contract.py

  # Use custom CSV file
  python push_to_contract.py --csv custom_prices.csv

  # Override with manual price (bypass CSV)
  python push_to_contract.py --price 3.75
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
    parser.add_argument("--asset-id", default=ASSET_ID_HEX, help="Asset ID (hex bytes32)")
    parser.add_argument(
        "--decimals",
        type=int,
        default=PRICE_DECIMALS,
        help="Price decimals for on-chain storage",
    )
    parser.add_argument(
        "--commit-delay",
        type=float,
        default=COMMIT_DELAY_SECONDS,
        help="Seconds to wait between commit and reveal",
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
    print("CUORACLE PRICE UPDATER")
    print("=" * 60)
    try:
        updater = CuOraclePriceUpdater(
            rpc_url=SEPOLIA_RPC_URL,
            private_key=PRIVATE_KEY,
            contract_address=CU_ORACLE_ADDRESS,
            asset_id_hex=args.asset_id,
            asset_label=args.asset_label,
            decimals=args.decimals,
            commit_delay=args.commit_delay,
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

    # Execute blockchain update
    print("\n" + "=" * 60)
    print("EXECUTING BLOCKCHAIN UPDATE")
    print("=" * 60)
    try:
        tx_hash = updater.update_price(price)
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

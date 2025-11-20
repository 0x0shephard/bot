#!/usr/bin/env python3
"""
CuOracle price updater script.
Pushes H100 GPU index prices to Sepolia testnet using commit-reveal mechanism.
"""

import csv
import json
import os
import secrets
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Sequence, Tuple

from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3
from web3.exceptions import ContractLogicError, TimeExhausted

load_dotenv()

# Environment variables with defaults
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

# Constants
MIN_PRICE_USD = 0.01  # Minimum valid price
MAX_PRICE_USD = 100.0  # Maximum valid price (sanity check)
DEFAULT_CSV_PATH = "h100_gpu_index.csv"
LOG_FILE_PATH = "contract_update_log.json"
MAX_LOG_ENTRIES = 100

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
        """Build EIP-1559 dynamic fee parameters."""
        try:
            base_fee = self.w3.eth.gas_price
            max_priority = self.w3.to_wei(2, "gwei")  # Increased for faster inclusion
            max_fee = base_fee * 2 + max_priority
            return max_fee, max_priority
        except Exception as exc:
            print(f"Warning: Could not fetch gas price, using defaults: {exc}")
            # Fallback to safe defaults
            return self.w3.to_wei(50, "gwei"), self.w3.to_wei(2, "gwei")

    def _send_transaction(self, func, gas_limit: int) -> Tuple[str, dict]:
        """Build, sign, and send a transaction to the blockchain."""
        max_fee, max_priority = self._build_dynamic_fee()

        try:
            nonce = self.w3.eth.get_transaction_count(self.address)
            tx = func.build_transaction(
                {
                    "from": self.address,
                    "nonce": nonce,
                    "gas": gas_limit,
                    "maxFeePerGas": max_fee,
                    "maxPriorityFeePerGas": max_priority,
                    "chainId": 11155111,  # Sepolia chain ID
                }
            )

            # Sign transaction
            signed = self.account.sign_transaction(tx)

            # Get raw transaction bytes
            # The SignedTransaction namedtuple has different attribute names across versions:
            # - eth-account < 0.9: uses 'rawTransaction'
            # - eth-account >= 0.9: uses 'raw_transaction'
            # Access by index [0] is most reliable as it's the first field in the namedtuple
            if hasattr(signed, "raw_transaction"):
                raw_tx = signed.raw_transaction
            elif hasattr(signed, "rawTransaction"):
                raw_tx = signed.rawTransaction
            elif isinstance(signed, tuple) and len(signed) > 0:
                # SignedTransaction is a namedtuple, first element is always the raw tx
                raw_tx = signed[0]
            else:
                raise AttributeError(
                    f"Cannot extract raw transaction from signed object. "
                    f"Type: {type(signed)}, Dir: {[a for a in dir(signed) if not a.startswith('_')]}"
                )

            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
            print(f"  Transaction sent: {tx_hash.hex()}")

            # Wait for receipt with timeout
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)

            # Check transaction status
            if receipt.get("status") != 1:
                raise ContractLogicError("Transaction failed on-chain")

            return tx_hash.hex(), dict(receipt)

        except TimeExhausted:
            raise TimeExhausted(f"Transaction {tx_hash.hex()} timed out after 180 seconds")
        except Exception as exc:
            raise Exception(f"Transaction failed: {exc}") from exc

    def get_current_price(self) -> PriceData:
        try:
            price_raw, last_updated = self.contract.functions.getLatestPrice(self.asset_id).call()
            return PriceData(price_raw=price_raw, last_updated=last_updated)
        except Exception:
            return PriceData(price_raw=0, last_updated=0)

    def update_price(self, price_usd: float) -> str:
        """
        Update the oracle price using commit-reveal mechanism.

        Args:
            price_usd: Price in USD (will be scaled by decimals)

        Returns:
            Transaction hash of the reveal transaction
        """
        # Validate price
        if not MIN_PRICE_USD <= price_usd <= MAX_PRICE_USD:
            raise ValueError(
                f"Price ${price_usd:.2f} outside valid range "
                f"[${MIN_PRICE_USD}, ${MAX_PRICE_USD}]"
            )

        # Scale price to contract precision
        price_scaled = int(price_usd * (10 ** self.decimals))
        nonce_bytes32 = secrets.token_bytes(32)

        # Display current price and change
        current = self.get_current_price()
        if current.price_raw:
            delta = price_usd - current.price
            change_pct = (delta / current.price) * 100 if current.price else 0
            print(f"\nCurrent on-chain price: ${current.price:.6f}/hr")
            print(f"New price: ${price_usd:.6f}/hr (Δ {change_pct:+.2f}%)")
        else:
            print(f"\nSetting initial price: ${price_usd:.6f}/hr")

        # Phase 1: Commit
        print("\n=== PHASE 1: COMMIT ===")
        commit_hash = Web3.keccak(
            self.w3.codec.encode(["uint256", "bytes32"], [price_scaled, nonce_bytes32])
        )
        print(f"Commit hash: {Web3.to_hex(commit_hash)}")

        try:
            commit_tx, commit_receipt = self._send_transaction(
                self.contract.functions.commitPrice(self.asset_id, commit_hash),
                gas_limit=150_000,
            )
            gas_used = commit_receipt.get("gasUsed", 0)
            print(f"  ✓ Commit successful! Tx: {commit_tx}")
            print(f"  Gas used: {gas_used:,}")

        except Exception as exc:
            raise Exception(f"Commit phase failed: {exc}") from exc

        # Wait between commit and reveal
        delay = max(self.commit_delay, 1)
        print(f"\nWaiting {delay:.1f}s before reveal phase...")
        time.sleep(delay)

        # Phase 2: Reveal
        print("\n=== PHASE 2: REVEAL ===")
        try:
            reveal_tx, reveal_receipt = self._send_transaction(
                self.contract.functions.updatePrices(
                    self.asset_id,
                    price_scaled,
                    nonce_bytes32,
                ),
                gas_limit=250_000,
            )
            gas_used = reveal_receipt.get("gasUsed", 0)
            print(f"  ✓ Reveal successful! Tx: {reveal_tx}")
            print(f"  Gas used: {gas_used:,}")

        except Exception as exc:
            raise Exception(f"Reveal phase failed: {exc}") from exc

        # Verify update
        print("\n=== VERIFICATION ===")
        latest = self.get_current_price()
        if latest.price_raw == price_scaled:
            print(f"  ✓ On-chain price confirmed: ${latest.price:.6f}/hr")
        else:
            print(f"  ⚠ Warning: On-chain price mismatch!")
            print(f"    Expected: ${price_usd:.6f}/hr")
            print(f"    Got: ${latest.price:.6f}/hr")

        # Log the update
        self.log_update(price_usd, commit_tx, reveal_tx, latest.last_updated)

        return reveal_tx

    def read_price_from_csv(self, csv_file: str) -> Optional[float]:
        """
        Read the latest H100 GPU index price from CSV file.

        Args:
            csv_file: Path to the CSV file containing price data

        Returns:
            Price in USD or None if unable to read
        """
        if not os.path.exists(csv_file):
            print(f"ERROR: CSV file not found: {csv_file}")
            return None

        try:
            with open(csv_file, "r", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                rows = list(reader)
        except Exception as exc:
            print(f"ERROR: Failed to read CSV {csv_file}: {exc}")
            return None

        if not rows:
            print(f"ERROR: CSV file is empty: {csv_file}")
            return None

        # Get the latest row
        latest = rows[-1]

        # Try to extract Full_Index_Price (primary format)
        if "Full_Index_Price" in latest:
            try:
                price = float(latest["Full_Index_Price"])
                timestamp = latest.get("Calculation_Date", "unknown")
                print("\n=== READING CSV DATA ===")
                print(f"  Source: {csv_file}")
                print(f"  Timestamp: {timestamp}")
                print(f"  Full Index Price: ${price:.6f}/hour")

                # Display additional metrics if available
                if "Hyperscalers_Only_Price" in latest:
                    print(f"  Hyperscalers Only: ${float(latest['Hyperscalers_Only_Price']):.6f}/hour")
                if "Non_Hyperscalers_Only_Price" in latest:
                    print(f"  Non-Hyperscalers Only: ${float(latest['Non_Hyperscalers_Only_Price']):.6f}/hour")

                return price
            except (ValueError, KeyError) as exc:
                print(f"ERROR: Invalid price data in CSV: {exc}")
                return None

        # Fallback: Try legacy format with 'asset' and 'price' columns
        asset_rows = [row for row in rows if row.get("asset", "").upper() == "H100"]
        if not asset_rows:
            print(f"ERROR: No valid price data found in {csv_file}")
            print(f"  Expected column 'Full_Index_Price' or asset='H100'")
            return None

        latest = asset_rows[-1]
        try:
            price = float(latest["price"])
            timestamp = latest.get("timestamp", "unknown")
            print("\n=== READING CSV DATA (Legacy Format) ===")
            print(f"  Source: {csv_file}")
            print(f"  Timestamp: {timestamp}")
            print(f"  Price: ${price:.6f}/hour")
            return price
        except (ValueError, KeyError) as exc:
            print(f"ERROR: Invalid price data: {exc}")
            return None

    def log_update(
        self,
        price_usd: float,
        commit_tx: str,
        reveal_tx: str,
        block_timestamp: int,
    ) -> None:
        """
        Log the price update to a JSON file.

        Args:
            price_usd: Price in USD
            commit_tx: Commit transaction hash
            reveal_tx: Reveal transaction hash
            block_timestamp: Blockchain timestamp of update
        """
        log_entry = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "price_usd": price_usd,
            "price_scaled": int(price_usd * (10 ** self.decimals)),
            "commit_tx_hash": commit_tx,
            "reveal_tx_hash": reveal_tx,
            "block_timestamp": block_timestamp,
            "contract_address": CU_ORACLE_ADDRESS,
            "asset_id": self.asset_id_hex,
            "asset_label": self.asset_label,
            "network": "sepolia",
            "decimals": self.decimals,
            "etherscan_url": f"https://sepolia.etherscan.io/tx/{reveal_tx}",
        }

        # Read existing logs
        logs = []
        if os.path.exists(LOG_FILE_PATH):
            try:
                with open(LOG_FILE_PATH, "r", encoding="utf-8") as handle:
                    logs = json.load(handle)
                    if not isinstance(logs, list):
                        logs = []
            except Exception as exc:
                print(f"Warning: Could not read existing log file: {exc}")
                logs = []

        # Append new entry and trim to max size
        logs.append(log_entry)
        logs = logs[-MAX_LOG_ENTRIES:]

        # Write back to file
        try:
            with open(LOG_FILE_PATH, "w", encoding="utf-8") as handle:
                json.dump(logs, handle, indent=2)
            print(f"\n✓ Update logged to {LOG_FILE_PATH}")
        except Exception as exc:
            print(f"Warning: Failed to write log file: {exc}")


def main() -> None:
    """Main entry point for the price updater script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Push H100 GPU index price to CuOracle smart contract on Sepolia",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update from CSV (default: h100_gpu_index.csv)
  python push_to_contract.py

  # Update from specific CSV file
  python push_to_contract.py --csv custom_prices.csv

  # Update with manual price
  python push_to_contract.py --price 3.79

  # Customize commit-reveal delay
  python push_to_contract.py --commit-delay 5.0

Environment Variables:
  SEPOLIA_RPC_URL              - Sepolia RPC endpoint
  ORACLE_UPDATER_PRIVATE_KEY   - Wallet private key
  CU_ORACLE_ADDRESS            - Contract address
  CU_ORACLE_ASSET_LABEL        - Asset label (default: H100_GPU_HOURLY)
  CU_ORACLE_DECIMALS           - Price decimals (default: 18)
        """,
    )
    parser.add_argument(
        "--csv",
        default=DEFAULT_CSV_PATH,
        help=f"Path to CSV file with price data (default: {DEFAULT_CSV_PATH})",
    )
    parser.add_argument(
        "--price",
        type=float,
        help="Manual price override (bypasses CSV reading)",
    )
    parser.add_argument(
        "--asset-label",
        default=ASSET_LABEL,
        help=f"Asset label for the oracle (default: {ASSET_LABEL})",
    )
    parser.add_argument(
        "--asset-id",
        default=ASSET_ID_HEX,
        help="Asset ID as hex string (optional, derived from label if not set)",
    )
    parser.add_argument(
        "--decimals",
        type=int,
        default=PRICE_DECIMALS,
        help=f"Price decimal precision (default: {PRICE_DECIMALS})",
    )
    parser.add_argument(
        "--commit-delay",
        type=float,
        default=COMMIT_DELAY_SECONDS,
        help=f"Delay between commit and reveal in seconds (default: {COMMIT_DELAY_SECONDS})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read price from CSV but don't send transactions",
    )

    args = parser.parse_args()

    # Validate environment
    print("=" * 70)
    print("CuOracle H100 GPU Price Updater")
    print("=" * 70)

    if not PRIVATE_KEY:
        print("\n❌ ERROR: Private key not configured!")
        print("   Set ORACLE_UPDATER_PRIVATE_KEY or WALLET_PRIVATE_KEY environment variable")
        print("   or add to .env file")
        sys.exit(1)

    try:
        # Initialize updater
        updater = CuOraclePriceUpdater(
            rpc_url=SEPOLIA_RPC_URL,
            private_key=PRIVATE_KEY,
            contract_address=CU_ORACLE_ADDRESS,
            asset_id_hex=args.asset_id,
            asset_label=args.asset_label,
            decimals=args.decimals,
            commit_delay=args.commit_delay,
        )

        # Determine price
        if args.price is not None:
            price = args.price
            print(f"\n✓ Using manual price: ${price:.6f}/hour")
        else:
            price = updater.read_price_from_csv(args.csv)
            if price is None:
                print("\n❌ ERROR: Unable to read price from CSV")
                sys.exit(1)

        # Validate price
        if price <= 0:
            print(f"\n❌ ERROR: Price must be greater than zero (got ${price})")
            sys.exit(1)

        if price < MIN_PRICE_USD or price > MAX_PRICE_USD:
            print(f"\n⚠️  WARNING: Price ${price:.2f} outside normal range")
            print(f"   Expected range: ${MIN_PRICE_USD} - ${MAX_PRICE_USD}")
            response = input("   Continue anyway? (y/N): ")
            if response.lower() != "y":
                print("   Aborted by user")
                sys.exit(0)

        # Dry run mode
        if args.dry_run:
            print("\n=== DRY RUN MODE ===")
            print(f"Would update price to: ${price:.6f}/hour")
            print(f"Scaled value: {int(price * (10 ** args.decimals))}")
            print("No transactions sent.")
            sys.exit(0)

        # Execute update
        print("\n" + "=" * 70)
        print("EXECUTING PRICE UPDATE")
        print("=" * 70)

        tx_hash = updater.update_price(price)

        print("\n" + "=" * 70)
        print("✅ SUCCESS!")
        print("=" * 70)
        print(f"Price updated to: ${price:.6f}/hour")
        print(f"Reveal transaction: {tx_hash}")
        print(f"Etherscan: https://sepolia.etherscan.io/tx/{tx_hash}")
        print("=" * 70)

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(130)
    except ValueError as exc:
        print(f"\n❌ ERROR: Invalid input - {exc}")
        sys.exit(1)
    except ConnectionError as exc:
        print(f"\n❌ ERROR: Connection failed - {exc}")
        print("   Check your RPC endpoint and internet connection")
        sys.exit(1)
    except Exception as exc:
        print(f"\n❌ ERROR: Update failed")
        print(f"   {exc}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

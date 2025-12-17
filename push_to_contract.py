#!/usr/bin/env python3
"""Multi-Asset Oracle price updater script for H100 GPU rental rates."""

import csv
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence, Tuple, Dict

from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3

load_dotenv()

SEPOLIA_RPC_URL = os.getenv("SEPOLIA_RPC_URL", "https://rpc.sepolia.org")
PRIVATE_KEY = os.getenv("ORACLE_UPDATER_PRIVATE_KEY") or os.getenv("PRIVATE_KEY")
MULTI_ASSET_ORACLE_ADDRESS = os.getenv(
    "MULTI_ASSET_ORACLE_ADDRESS",
    "0xB44d652354d12Ac56b83112c6ece1fa2ccEfc683",  # MultiAssetOracle on Sepolia
)
PRICE_DECIMALS = int(os.getenv("ORACLE_DECIMALS", "18"))

# Asset IDs (keccak256 hashes)
ASSET_IDS = {
    "H100_HOURLY": "0x82af7da7090d6235dbc9f8cfccfb82eee2e9cb33d50be18eabf66c158261796a",
    "H100_HYPERSCALERS_HOURLY": "0x4907d2c1e61b87a99a260f8529c3c4f9e2374edae1f5ab1464a8e79d0f2c26de",
    "H100_NON_HYPERSCALERS_HOURLY": "0xd6e43f59d2c94773a52e2c20f09762901247d1aaf2090d0b99e85c55c9833626",
}

# MultiAssetOracle ABI
MULTI_ASSET_ORACLE_ABI: Sequence[dict] = [
    {
        "type": "function",
        "name": "registerAsset",
        "inputs": [
            {"name": "assetId", "type": "bytes32", "internalType": "bytes32"},
            {"name": "initialPrice", "type": "uint256", "internalType": "uint256"},
        ],
        "outputs": [],
        "stateMutability": "nonpayable",
    },
    {
        "type": "function",
        "name": "updatePrice",
        "inputs": [
            {"name": "assetId", "type": "bytes32", "internalType": "bytes32"},
            {"name": "newPrice", "type": "uint256", "internalType": "uint256"},
        ],
        "outputs": [],
        "stateMutability": "nonpayable",
    },
    {
        "type": "function",
        "name": "batchUpdatePrices",
        "inputs": [
            {"name": "assetIds", "type": "bytes32[]", "internalType": "bytes32[]"},
            {"name": "newPrices", "type": "uint256[]", "internalType": "uint256[]"},
        ],
        "outputs": [],
        "stateMutability": "nonpayable",
    },
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
    {
        "type": "function",
        "name": "getPriceData",
        "inputs": [
            {"name": "assetId", "type": "bytes32", "internalType": "bytes32"}
        ],
        "outputs": [
            {"name": "price", "type": "uint256", "internalType": "uint256"},
            {"name": "updatedAt", "type": "uint256", "internalType": "uint256"}
        ],
        "stateMutability": "view",
    },
    {
        "type": "function",
        "name": "isAssetRegistered",
        "inputs": [
            {"name": "assetId", "type": "bytes32", "internalType": "bytes32"}
        ],
        "outputs": [
            {"name": "", "type": "bool", "internalType": "bool"}
        ],
        "stateMutability": "view",
    },
    {
        "type": "event",
        "name": "PriceUpdated",
        "inputs": [
            {"name": "assetId", "type": "bytes32", "indexed": True, "internalType": "bytes32"},
            {"name": "price", "type": "uint256", "indexed": True, "internalType": "uint256"},
            {"name": "timestamp", "type": "uint256", "indexed": False, "internalType": "uint256"},
        ],
        "anonymous": False,
    },
    {
        "type": "event",
        "name": "AssetRegistered",
        "inputs": [
            {"name": "assetId", "type": "bytes32", "indexed": True, "internalType": "bytes32"},
            {"name": "initialPrice", "type": "uint256", "indexed": False, "internalType": "uint256"},
        ],
        "anonymous": False,
    },
]


@dataclass
class AssetPrice:
    asset_id: str
    asset_name: str
    price_raw: int

    @property
    def price(self) -> float:
        return self.price_raw / 10 ** PRICE_DECIMALS


class MultiAssetOraclePriceUpdater:
    """Update H100 GPU rental prices on the multi-asset oracle contract.

    This oracle manages prices for 3 assets:
    - H100_HOURLY: Weighted average across all providers
    - H100_HYPERSCALERS_HOURLY: HyperScalers only (AWS, GCP, Azure)
    - H100_NON_HYPERSCALERS_HOURLY: Non-HyperScalers only (Lambda, CoreWeave, etc.)
    """

    def __init__(
        self,
        rpc_url: str,
        private_key: str,
        contract_address: str,
        decimals: int,
    ):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to Sepolia RPC: {rpc_url}")
        self.account = Account.from_key(private_key)
        self.address = self.account.address
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=MULTI_ASSET_ORACLE_ABI,
        )
        self.decimals = decimals
        balance_eth = self.w3.from_wei(self.w3.eth.get_balance(self.address), "ether")
        print("Connected to Sepolia testnet")
        print(f"   Chain ID: {self.w3.eth.chain_id}")
        print(f"   Latest block: {self.w3.eth.block_number}")
        print(f"   Updater address: {self.address}")
        print(f"   Balance: {balance_eth:.4f} ETH")
        print(f"   MultiAssetOracle: {contract_address}")
        print(f"   Price decimals: {self.decimals}")

        # Check asset registration
        for name, asset_id in ASSET_IDS.items():
            is_registered = self.is_asset_registered(asset_id)
            status = "✓ Registered" if is_registered else "✗ Not registered"
            print(f"   {name}: {status}")

            if is_registered:
                current_price = self.get_current_price(asset_id)
                if current_price.price_raw:
                    print(f"      Current price: ${current_price.price:.6f}/hr")

    def _build_dynamic_fee(self) -> Tuple[int, int]:
        base_fee = self.w3.eth.gas_price
        max_priority = self.w3.to_wei(1, "gwei")
        max_fee = max(base_fee * 2, max_priority * 2)
        return max_fee, max_priority

    def _send_transaction(self, func, gas_limit: int) -> Tuple[str, dict]:
        """Build, sign, and send a transaction to the blockchain."""
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

        if hasattr(signed, "raw_transaction"):
            raw_tx = signed.raw_transaction
        elif hasattr(signed, "rawTransaction"):
            raw_tx = signed.rawTransaction
        else:
            raw_tx = signed

        tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        return tx_hash.hex(), dict(receipt)

    def is_asset_registered(self, asset_id: str) -> bool:
        """Check if an asset is registered in the oracle."""
        try:
            return self.contract.functions.isAssetRegistered(asset_id).call()
        except Exception:
            return False

    def get_current_price(self, asset_id: str) -> AssetPrice:
        """Get current price for a specific asset from the oracle."""
        try:
            price_raw = self.contract.functions.getPrice(asset_id).call()
            asset_name = [k for k, v in ASSET_IDS.items() if v == asset_id][0]
            return AssetPrice(asset_id=asset_id, asset_name=asset_name, price_raw=price_raw)
        except Exception:
            asset_name = [k for k, v in ASSET_IDS.items() if v == asset_id][0]
            return AssetPrice(asset_id=asset_id, asset_name=asset_name, price_raw=0)

    def register_asset(self, asset_id: str, initial_price_usd: float) -> str:
        """Register a new asset with initial price."""
        price_scaled = int(initial_price_usd * (10 ** self.decimals))
        asset_name = [k for k, v in ASSET_IDS.items() if v == asset_id][0]

        print(f"Registering {asset_name} with initial price ${initial_price_usd:.6f}/hr")
        print("Sending transaction...")

        tx_hash, receipt = self._send_transaction(
            self.contract.functions.registerAsset(asset_id, price_scaled),
            gas_limit=150_000,
        )

        print(f"Transaction confirmed: {tx_hash}")
        print(f"Gas used: {receipt['gasUsed']:,}")
        return tx_hash

    def update_single_price(self, asset_id: str, price_usd: float) -> str:
        """Update price for a single asset."""
        price_scaled = int(price_usd * (10 ** self.decimals))
        current = self.get_current_price(asset_id)

        if current.price_raw:
            delta = price_usd - current.price
            change_pct = (delta / current.price) * 100 if current.price else 0
            print(f"Current {current.asset_name}: ${current.price:.6f}/hr (Δ {change_pct:+.2f}%)")

        print(f"Updating {current.asset_name} to: ${price_usd:.6f}/hr")
        print("Sending transaction...")

        tx_hash, receipt = self._send_transaction(
            self.contract.functions.updatePrice(asset_id, price_scaled),
            gas_limit=100_000,
        )

        print(f"Transaction confirmed: {tx_hash}")
        print(f"Gas used: {receipt['gasUsed']:,}")

        # Verify the update
        latest = self.get_current_price(asset_id)
        if latest.price_raw == price_scaled:
            print(f"✓ On-chain price verified: ${latest.price:.6f}/hr")
        else:
            print(f"⚠ WARNING: On-chain price mismatch!")
            print(f"   Expected: ${price_usd:.6f}/hr")
            print(f"   Got: ${latest.price:.6f}/hr")

        return tx_hash

    def batch_update_prices(self, prices: Dict[str, float], verify: bool = True) -> str:
        """Batch update prices for all assets (more gas efficient).

        Args:
            prices: Dict mapping asset_id to price_usd
            verify: Whether to verify prices on-chain after update (default: True)
        """
        asset_ids = list(prices.keys())
        price_values = [int(prices[aid] * (10 ** self.decimals)) for aid in asset_ids]

        print("Batch updating prices for all assets:")
        for asset_id in asset_ids:
            asset_name = [k for k, v in ASSET_IDS.items() if v == asset_id][0]
            current = self.get_current_price(asset_id)
            new_price = prices[asset_id]

            if current.price_raw:
                delta = new_price - current.price
                change_pct = (delta / current.price) * 100 if current.price else 0
                print(f"   {asset_name}: ${current.price:.6f} → ${new_price:.6f} (Δ {change_pct:+.2f}%)")
            else:
                print(f"   {asset_name}: → ${new_price:.6f}")

        print("Sending batch transaction...")

        tx_hash, receipt = self._send_transaction(
            self.contract.functions.batchUpdatePrices(asset_ids, price_values),
            gas_limit=300_000,
        )

        print(f"Transaction confirmed: {tx_hash}")
        print(f"Gas used: {receipt['gasUsed']:,}")

        # Verify all updates (optional)
        if verify:
            print("Verifying updates:")
            all_verified = True
            for asset_id in asset_ids:
                asset_name = [k for k, v in ASSET_IDS.items() if v == asset_id][0]
                latest = self.get_current_price(asset_id)
                expected = int(prices[asset_id] * (10 ** self.decimals))

                if latest.price_raw == expected:
                    print(f"   ✓ {asset_name}: ${latest.price:.6f}/hr")
                else:
                    print(f"   ✗ {asset_name}: Expected ${prices[asset_id]:.6f}, got ${latest.price:.6f}")
                    all_verified = False

            if not all_verified:
                print("⚠ WARNING: Some prices failed to update correctly!")
        else:
            print("Skipping on-chain verification (--no-verify)")

        return tx_hash

    def read_prices_from_csv(self, csv_file: str) -> Optional[Dict[str, float]]:
        """Read GPU prices from pipeline-generated CSV file.

        Expected format: h100_gpu_index.csv with columns:
        - Full_Index_Price: Weighted average price across all providers
        - Hyperscalers_Only_Price: Price from major cloud providers only
        - Non_Hyperscalers_Only_Price: Price from smaller providers only
        - Calculation_Date: Timestamp of calculation
        """
        try:
            with open(csv_file, "r", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                rows = list(reader)
        except FileNotFoundError:
            print(f"ERROR: CSV file not found: {csv_file}")
            print("   Ensure the GPU price pipeline has completed successfully")
            return None
        except Exception as exc:
            print(f"ERROR: Failed to read CSV {csv_file}: {exc}")
            return None

        if not rows:
            print(f"ERROR: CSV file is empty: {csv_file}")
            return None

        # Get the latest index prices (last row)
        latest = rows[-1]

        # Validate required columns
        required_columns = ["Full_Index_Price", "Hyperscalers_Only_Price", "Non_Hyperscalers_Only_Price"]
        missing = [col for col in required_columns if col not in latest]
        if missing:
            print(f"ERROR: CSV missing required columns: {missing}")
            print(f"   Available columns: {list(latest.keys())}")
            return None

        try:
            prices = {
                ASSET_IDS["H100_HOURLY"]: float(latest["Full_Index_Price"]),
                ASSET_IDS["H100_HYPERSCALERS_HOURLY"]: float(latest["Hyperscalers_Only_Price"]),
                ASSET_IDS["H100_NON_HYPERSCALERS_HOURLY"]: float(latest["Non_Hyperscalers_Only_Price"]),
            }
        except (ValueError, TypeError) as exc:
            print(f"ERROR: Invalid price values in CSV: {exc}")
            return None

        timestamp = latest.get("Calculation_Date", "unknown")
        print("=" * 60)
        print("GPU INDEX PRICES FROM PIPELINE")
        print("=" * 60)
        print(f"   Calculation Date: {timestamp}")
        print(f"   Full Index Price: ${prices[ASSET_IDS['H100_HOURLY']]:.6f}/hour")
        print(f"   HyperScalers Only: ${prices[ASSET_IDS['H100_HYPERSCALERS_HOURLY']]:.6f}/hour")
        print(f"   Non-HyperScalers Only: ${prices[ASSET_IDS['H100_NON_HYPERSCALERS_HOURLY']]:.6f}/hour")
        print("=" * 60)

        return prices

    def log_update(self, prices: Dict[str, float], tx_hash: str, block_number: int) -> None:
        """Log blockchain update to JSON file."""
        from datetime import timezone

        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prices": {
                "h100_hourly": prices.get(ASSET_IDS["H100_HOURLY"]),
                "h100_hyperscalers": prices.get(ASSET_IDS["H100_HYPERSCALERS_HOURLY"]),
                "h100_non_hyperscalers": prices.get(ASSET_IDS["H100_NON_HYPERSCALERS_HOURLY"]),
            },
            "tx_hash": tx_hash,
            "block_number": block_number,
            "contract_address": MULTI_ASSET_ORACLE_ADDRESS,
            "network": "sepolia",
            "decimals": self.decimals,
            "updater_address": self.address,
        }

        log_file = "contract_update_log.json"
        logs = []

        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8") as handle:
                    logs = json.load(handle)
                if not isinstance(logs, list):
                    logs = []
            except Exception:
                logs = []

        logs.append(log_entry)
        logs = logs[-100:]

        try:
            with open(log_file, "w", encoding="utf-8") as handle:
                json.dump(logs, handle, indent=2)
            print(f"✓ Logged update to {log_file} (entry {len(logs)}/100)")
        except Exception as exc:
            print(f"ERROR: Failed to write log file: {exc}")


def read_csv_prices_standalone(csv_file: str) -> Optional[Dict[str, float]]:
    """Read GPU prices from CSV without blockchain connection (for dry-run mode).

    Expected format: h100_gpu_index.csv with columns:
    - Full_Index_Price: Weighted average price across all providers
    - Hyperscalers_Only_Price: Price from major cloud providers only
    - Non_Hyperscalers_Only_Price: Price from smaller providers only
    - Calculation_Date: Timestamp of calculation
    """
    try:
        with open(csv_file, "r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
    except FileNotFoundError:
        print(f"ERROR: CSV file not found: {csv_file}")
        print("   Ensure the GPU price pipeline has completed successfully")
        return None
    except Exception as exc:
        print(f"ERROR: Failed to read CSV {csv_file}: {exc}")
        return None

    if not rows:
        print(f"ERROR: CSV file is empty: {csv_file}")
        return None

    # Get the latest index prices (last row)
    latest = rows[-1]

    # Validate required columns
    required_columns = ["Full_Index_Price", "Hyperscalers_Only_Price", "Non_Hyperscalers_Only_Price"]
    missing = [col for col in required_columns if col not in latest]
    if missing:
        print(f"ERROR: CSV missing required columns: {missing}")
        print(f"   Available columns: {list(latest.keys())}")
        return None

    try:
        prices = {
            ASSET_IDS["H100_HOURLY"]: float(latest["Full_Index_Price"]),
            ASSET_IDS["H100_HYPERSCALERS_HOURLY"]: float(latest["Hyperscalers_Only_Price"]),
            ASSET_IDS["H100_NON_HYPERSCALERS_HOURLY"]: float(latest["Non_Hyperscalers_Only_Price"]),
        }
    except (ValueError, TypeError) as exc:
        print(f"ERROR: Invalid price values in CSV: {exc}")
        return None

    timestamp = latest.get("Calculation_Date", "unknown")
    print("=" * 60)
    print("GPU INDEX PRICES FROM PIPELINE")
    print("=" * 60)
    print(f"   Calculation Date: {timestamp}")
    print(f"   Full Index Price: ${prices[ASSET_IDS['H100_HOURLY']]:.6f}/hour")
    print(f"   HyperScalers Only: ${prices[ASSET_IDS['H100_HYPERSCALERS_HOURLY']]:.6f}/hour")
    print(f"   Non-HyperScalers Only: ${prices[ASSET_IDS['H100_NON_HYPERSCALERS_HOURLY']]:.6f}/hour")
    print("=" * 60)

    return prices


def main() -> None:
    """Main entry point for pushing GPU index prices to blockchain."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Push H100 GPU index prices to MultiAssetOracle smart contract",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--csv",
        default="h100_gpu_index.csv",
        help="Path to GPU index CSV (default: h100_gpu_index.csv)",
    )
    parser.add_argument(
        "--register",
        action="store_true",
        help="Register assets if not already registered",
    )
    parser.add_argument(
        "--manual-prices",
        nargs=3,
        type=float,
        metavar=("H100", "HYPERSCALERS", "NON_HYPERSCALERS"),
        help="Manual price override (bypasses CSV). Example: --manual-prices 3.79 4.20 2.95",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip on-chain price verification after update (faster, used in CI/CD)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the update without sending transactions",
    )
    args = parser.parse_args()

    # Validate environment
    if not PRIVATE_KEY and not args.dry_run:
        print("ERROR: Private key not configured")
        print("Set ORACLE_UPDATER_PRIVATE_KEY or PRIVATE_KEY environment variable")
        print("(Use --dry-run to test without a private key)")
        sys.exit(1)

    # Initialize oracle updater
    print("\n" + "=" * 60)
    print("MULTI-ASSET ORACLE PRICE UPDATER")
    if args.dry_run:
        print("MODE: DRY RUN (no transactions will be sent)")
    print("=" * 60)

    if args.dry_run:
        # Dry run mode - skip blockchain initialization
        updater = None
    else:
        try:
            updater = MultiAssetOraclePriceUpdater(
                rpc_url=SEPOLIA_RPC_URL,
                private_key=PRIVATE_KEY,
                contract_address=MULTI_ASSET_ORACLE_ADDRESS,
                decimals=PRICE_DECIMALS,
            )
        except Exception as exc:
            print(f"\nERROR: Failed to initialize updater: {exc}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    # Register assets if requested
    if args.register and not args.dry_run:
        print("\n" + "=" * 60)
        print("REGISTERING ASSETS")
        print("=" * 60)
        for name, asset_id in ASSET_IDS.items():
            if not updater.is_asset_registered(asset_id):
                try:
                    default_price = 3.79  # Default initial price
                    updater.register_asset(asset_id, default_price)
                    print(f"✓ Registered {name}")
                except Exception as exc:
                    print(f"✗ Failed to register {name}: {exc}")
            else:
                print(f"✓ {name} already registered")

    # Determine price source
    if args.manual_prices:
        prices = {
            ASSET_IDS["H100_HOURLY"]: args.manual_prices[0],
            ASSET_IDS["H100_HYPERSCALERS_HOURLY"]: args.manual_prices[1],
            ASSET_IDS["H100_NON_HYPERSCALERS_HOURLY"]: args.manual_prices[2],
        }
        print("\n" + "=" * 60)
        print("MANUAL PRICE OVERRIDE")
        print("=" * 60)
        print(f"   H100 (Full): ${prices[ASSET_IDS['H100_HOURLY']]:.6f}/hr")
        print(f"   HyperScalers: ${prices[ASSET_IDS['H100_HYPERSCALERS_HOURLY']]:.6f}/hr")
        print(f"   Non-HyperScalers: ${prices[ASSET_IDS['H100_NON_HYPERSCALERS_HOURLY']]:.6f}/hr")
        print("=" * 60)
    else:
        # Read prices from CSV (works in both dry-run and normal mode)
        if args.dry_run:
            # For dry run, read CSV directly without updater
            prices = read_csv_prices_standalone(args.csv)
        else:
            prices = updater.read_prices_from_csv(args.csv)

        if prices is None:
            print("\nERROR: Unable to read prices from CSV")
            print("Use --manual-prices to bypass CSV")
            sys.exit(1)

    # Validate prices
    for asset_id, price in prices.items():
        asset_name = [k for k, v in ASSET_IDS.items() if v == asset_id][0]
        if price <= 0:
            print(f"\nERROR: {asset_name} price must be > 0 (got {price})")
            sys.exit(1)
        if price > 100:
            print(f"\nWARNING: {asset_name} price ${price:.2f}/hr seems unusually high")

    # Execute blockchain update
    print("\n" + "=" * 60)
    if args.dry_run:
        print("DRY RUN COMPLETE - NO BLOCKCHAIN UPDATE")
        print("=" * 60)
        print("   Would update the following prices:")
        for asset_id, price in prices.items():
            asset_name = [k for k, v in ASSET_IDS.items() if v == asset_id][0]
            print(f"   {asset_name}: ${price:.6f}/hr")
        print("=" * 60)
        print("\nDry run successful. To execute, run without --dry-run")
        sys.exit(0)

    print("EXECUTING BLOCKCHAIN UPDATE")
    print("=" * 60)
    try:
        tx_hash = updater.batch_update_prices(prices, verify=not args.no_verify)
        block_number = updater.w3.eth.block_number
        updater.log_update(prices, tx_hash, block_number)

        print("\n" + "=" * 60)
        print("SUCCESS! PRICES UPDATED ON-CHAIN")
        print("=" * 60)
        print(f"   Transaction: {tx_hash}")
        print(f"   Etherscan: https://sepolia.etherscan.io/tx/{tx_hash}")
        print("=" * 60)
        print("\nTIP: Run 'python autorun.py' to sync prices to database")
        sys.exit(0)
    except Exception as exc:
        print("\n" + "=" * 60)
        print("ERROR: BLOCKCHAIN UPDATE FAILED")
        print("=" * 60)
        print(f"   {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

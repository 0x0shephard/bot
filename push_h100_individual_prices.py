#!/usr/bin/env python3
"""
H100 Provider-Specific Oracle Price Updater

Updates GPU rental prices for H100 markets on the MultiAssetOracle contract.
Supports AWS, Azure, and GCP H100 GPU hourly rental rates.

Usage:
    # Update all H100 provider prices
    python scripts/update_h100_provider_prices.py --aws 3.85 --azure 2.12 --gcp 3.88

    # Update single provider
    python scripts/update_h100_provider_prices.py --aws 3.85

    # Batch update (more gas efficient)
    python scripts/update_h100_provider_prices.py --aws 3.85 --azure 2.12 --gcp 3.88 --batch
"""

import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3

load_dotenv()

# Configuration
SEPOLIA_RPC_URL = os.getenv("SEPOLIA_RPC_URL", "https://rpc.sepolia.org")
PRIVATE_KEY = os.getenv("PRIVATE_KEY") or os.getenv("ORACLE_UPDATER_PRIVATE_KEY") or os.getenv("WALLET_PRIVATE_KEY")

# MultiAssetOracle contract address on Sepolia
MULTI_ASSET_ORACLE_ADDRESS = "0xB44d652354d12Ac56b83112c6ece1fa2ccEfc683"

# H100 Provider-Specific Asset IDs (keccak256 hashes)
H100_ASSET_IDS = {
    "AWS_H100_HOURLY": "0x7d262bdf6fe868e6f4fbaae8df4383382d51684d63ed56221ae3657e10f822f6",
    "AZURE_H100_HOURLY": "0x9c7133267a94b0099c1cc21d1c7aef7d7daeb63a0fe81021715a9247be2e10a7",
    "GCP_H100_HOURLY": "0x80b8897ba24f84fcb99b7b482f45ae335104fa06f096a7d4718870ce143c892b",
}

# Price decimals (1e18 format)
PRICE_DECIMALS = 18

# MultiAssetOracle ABI (minimal)
MULTI_ASSET_ORACLE_ABI = [
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
            {"name": "assetId", "type": "bytes32", "internalType": "bytes32"},
        ],
        "outputs": [
            {"name": "", "type": "uint256", "internalType": "uint256"},
        ],
        "stateMutability": "view",
    },
    {
        "type": "function",
        "name": "prices",
        "inputs": [
            {"name": "", "type": "bytes32", "internalType": "bytes32"},
        ],
        "outputs": [
            {"name": "", "type": "uint256", "internalType": "uint256"},
        ],
        "stateMutability": "view",
    },
    {
        "type": "function",
        "name": "lastUpdated",
        "inputs": [
            {"name": "", "type": "bytes32", "internalType": "bytes32"},
        ],
        "outputs": [
            {"name": "", "type": "uint256", "internalType": "uint256"},
        ],
        "stateMutability": "view",
    },
    {
        "type": "function",
        "name": "isAssetRegistered",
        "inputs": [
            {"name": "assetId", "type": "bytes32", "internalType": "bytes32"},
        ],
        "outputs": [
            {"name": "", "type": "bool", "internalType": "bool"},
        ],
        "stateMutability": "view",
    },
    {
        "type": "event",
        "name": "PriceUpdated",
        "inputs": [
            {"name": "assetId", "type": "bytes32", "indexed": True},
            {"name": "newPrice", "type": "uint256", "indexed": True},
            {"name": "timestamp", "type": "uint256", "indexed": False},
        ],
        "anonymous": False,
    },
]


@dataclass
class PriceUpdate:
    """Represents a price update for a specific asset."""
    asset_name: str
    asset_id: str
    price_usd: float
    price_scaled: int

    @property
    def price_formatted(self) -> str:
        return f"${self.price_usd:.2f}/hr"


class H100OraclePriceUpdater:
    """Update H100 GPU rental prices on the MultiAssetOracle contract."""

    def __init__(self, rpc_url: str, private_key: str, contract_address: str):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to RPC: {rpc_url}")

        self.account = Account.from_key(private_key)
        self.address = self.account.address
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=MULTI_ASSET_ORACLE_ABI,
        )
        self.contract_address = contract_address

        # Display connection info
        balance_eth = self.w3.from_wei(self.w3.eth.get_balance(self.address), "ether")
        print("=" * 60)
        print("H100 PROVIDER ORACLE PRICE UPDATER")
        print("=" * 60)
        print(f"Connected to Sepolia testnet")
        print(f"  Chain ID: {self.w3.eth.chain_id}")
        print(f"  Latest block: {self.w3.eth.block_number}")
        print(f"  Updater address: {self.address}")
        print(f"  Balance: {balance_eth:.4f} ETH")
        print(f"  MultiAssetOracle: {contract_address}")
        print("=" * 60)

    def _build_dynamic_fee(self) -> Tuple[int, int]:
        """Calculate dynamic gas fees."""
        base_fee = self.w3.eth.gas_price
        max_priority = self.w3.to_wei(1, "gwei")
        max_fee = max(base_fee * 2, max_priority * 2)
        return max_fee, max_priority

    def _send_transaction(self, func, gas_limit: int) -> Tuple[str, dict]:
        """Build, sign, and send a transaction."""
        max_fee, max_priority = self._build_dynamic_fee()
        tx = func.build_transaction({
            "from": self.address,
            "nonce": self.w3.eth.get_transaction_count(self.address),
            "gas": gas_limit,
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": max_priority,
            "chainId": 11155111,
        })
        signed = self.account.sign_transaction(tx)

        # Handle different web3.py versions
        if hasattr(signed, "raw_transaction"):
            raw_tx = signed.raw_transaction
        elif hasattr(signed, "rawTransaction"):
            raw_tx = signed.rawTransaction
        else:
            raw_tx = signed

        tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        return tx_hash.hex(), dict(receipt)

    def get_current_price(self, asset_id: str) -> Optional[float]:
        """Get current price for an asset from the oracle."""
        try:
            price_raw = self.contract.functions.prices(asset_id).call()
            if price_raw == 0:
                return None
            return price_raw / (10 ** PRICE_DECIMALS)
        except Exception as e:
            print(f"  Warning: Could not read price: {e}")
            return None

    def get_last_updated(self, asset_id: str) -> Optional[int]:
        """Get last update timestamp for an asset."""
        try:
            return self.contract.functions.lastUpdated(asset_id).call()
        except Exception:
            return None

    def is_asset_registered(self, asset_id: str) -> bool:
        """Check if an asset is registered in the oracle."""
        try:
            return self.contract.functions.isAssetRegistered(asset_id).call()
        except Exception:
            return False

    def update_single_price(self, update: PriceUpdate) -> str:
        """Update price for a single asset."""
        print(f"\nUpdating {update.asset_name}...")
        print(f"  Asset ID: {update.asset_id}")

        # Get current price
        current_price = self.get_current_price(update.asset_id)
        if current_price:
            delta = update.price_usd - current_price
            change_pct = (delta / current_price) * 100
            print(f"  Current: ${current_price:.4f}/hr")
            print(f"  New: ${update.price_usd:.4f}/hr ({change_pct:+.2f}%)")
        else:
            print(f"  New: ${update.price_usd:.4f}/hr (first update)")

        # Send transaction
        print("  Sending transaction...")
        tx_hash, receipt = self._send_transaction(
            self.contract.functions.updatePrice(update.asset_id, update.price_scaled),
            gas_limit=100_000,
        )

        print(f"  TX: {tx_hash}")
        print(f"  Gas used: {receipt['gasUsed']:,}")

        # Verify
        new_price = self.get_current_price(update.asset_id)
        if new_price and abs(new_price - update.price_usd) < 0.0001:
            print(f"  Verified: ${new_price:.4f}/hr")
        else:
            print(f"  Warning: Verification mismatch!")

        return tx_hash

    def batch_update_prices(self, updates: List[PriceUpdate]) -> str:
        """Update prices for multiple assets in a single transaction."""
        print(f"\nBatch updating {len(updates)} assets...")

        asset_ids = []
        prices = []

        for update in updates:
            print(f"  {update.asset_name}: ${update.price_usd:.4f}/hr")
            asset_ids.append(update.asset_id)
            prices.append(update.price_scaled)

            # Show current price
            current = self.get_current_price(update.asset_id)
            if current:
                delta = update.price_usd - current
                change_pct = (delta / current) * 100
                print(f"    Current: ${current:.4f}/hr ({change_pct:+.2f}%)")

        # Send batch transaction
        print("\nSending batch transaction...")
        tx_hash, receipt = self._send_transaction(
            self.contract.functions.batchUpdatePrices(asset_ids, prices),
            gas_limit=50_000 + (len(updates) * 50_000),  # Base + per-asset gas
        )

        print(f"TX: {tx_hash}")
        print(f"Gas used: {receipt['gasUsed']:,}")
        print(f"Gas per asset: {receipt['gasUsed'] // len(updates):,}")

        # Verify all updates
        print("\nVerifying updates...")
        all_verified = True
        for update in updates:
            new_price = self.get_current_price(update.asset_id)
            if new_price and abs(new_price - update.price_usd) < 0.0001:
                print(f"  {update.asset_name}: ${new_price:.4f}/hr")
            else:
                print(f"  {update.asset_name}: VERIFICATION FAILED!")
                all_verified = False

        if all_verified:
            print("All prices verified successfully!")

        return tx_hash

    def show_current_prices(self):
        """Display current prices for all H100 assets."""
        print("\nCurrent H100 Provider Prices:")
        print("-" * 40)
        for name, asset_id in H100_ASSET_IDS.items():
            price = self.get_current_price(asset_id)
            last_updated = self.get_last_updated(asset_id)
            registered = self.is_asset_registered(asset_id)

            if not registered:
                print(f"  {name}: NOT REGISTERED")
            elif price:
                age = ""
                if last_updated:
                    age_seconds = int(datetime.now().timestamp()) - last_updated
                    if age_seconds < 3600:
                        age = f" ({age_seconds // 60}m ago)"
                    else:
                        age = f" ({age_seconds // 3600}h ago)"
                print(f"  {name}: ${price:.4f}/hr{age}")
            else:
                print(f"  {name}: No price set")
        print("-" * 40)

    def log_updates(self, updates: List[PriceUpdate], tx_hash: str):
        """Log updates to JSON file."""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tx_hash": tx_hash,
            "contract_address": self.contract_address,
            "network": "sepolia",
            "updater_address": self.address,
            "updates": [
                {
                    "asset_name": u.asset_name,
                    "asset_id": u.asset_id,
                    "price_usd": u.price_usd,
                    "price_scaled": u.price_scaled,
                }
                for u in updates
            ],
        }

        log_file = "h100_provider_price_log.json"
        logs = []

        if os.path.exists(log_file):
            try:
                with open(log_file, "r") as f:
                    logs = json.load(f)
                if not isinstance(logs, list):
                    logs = []
            except Exception:
                logs = []

        logs.append(log_entry)
        logs = logs[-100:]  # Keep last 100 entries

        with open(log_file, "w") as f:
            json.dump(logs, f, indent=2)
        print(f"\nLogged update to {log_file}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Update H100 provider-specific GPU prices on MultiAssetOracle",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update all providers
  python scripts/update_h100_provider_prices.py --aws 3.85 --azure 2.12 --gcp 3.88

  # Update single provider
  python scripts/update_h100_provider_prices.py --aws 3.85

  # Batch update (more gas efficient)
  python scripts/update_h100_provider_prices.py --aws 3.85 --azure 2.12 --gcp 3.88 --batch

  # Show current prices only
  python scripts/update_h100_provider_prices.py --show

Environment Variables:
  SEPOLIA_RPC_URL    Ethereum RPC endpoint
  PRIVATE_KEY        Wallet private key for signing transactions
        """,
    )

    parser.add_argument("--aws", type=float, help="AWS H100 price in USD/hour")
    parser.add_argument("--azure", type=float, help="Azure H100 price in USD/hour")
    parser.add_argument("--gcp", type=float, help="GCP H100 price in USD/hour")
    parser.add_argument("--batch", action="store_true", help="Use batch update (more gas efficient)")
    parser.add_argument("--show", action="store_true", help="Show current prices and exit")

    args = parser.parse_args()

    # Validate private key
    if not PRIVATE_KEY:
        print("ERROR: Private key not configured")
        print("Set PRIVATE_KEY or ORACLE_UPDATER_PRIVATE_KEY environment variable")
        sys.exit(1)

    # Initialize updater
    try:
        updater = H100OraclePriceUpdater(
            rpc_url=SEPOLIA_RPC_URL,
            private_key=PRIVATE_KEY,
            contract_address=MULTI_ASSET_ORACLE_ADDRESS,
        )
    except Exception as e:
        print(f"ERROR: Failed to initialize: {e}")
        sys.exit(1)

    # Show current prices
    updater.show_current_prices()

    if args.show:
        sys.exit(0)

    # Build update list
    updates: List[PriceUpdate] = []

    if args.aws:
        updates.append(PriceUpdate(
            asset_name="AWS_H100_HOURLY",
            asset_id=H100_ASSET_IDS["AWS_H100_HOURLY"],
            price_usd=args.aws,
            price_scaled=int(args.aws * (10 ** PRICE_DECIMALS)),
        ))

    if args.azure:
        updates.append(PriceUpdate(
            asset_name="AZURE_H100_HOURLY",
            asset_id=H100_ASSET_IDS["AZURE_H100_HOURLY"],
            price_usd=args.azure,
            price_scaled=int(args.azure * (10 ** PRICE_DECIMALS)),
        ))

    if args.gcp:
        updates.append(PriceUpdate(
            asset_name="GCP_H100_HOURLY",
            asset_id=H100_ASSET_IDS["GCP_H100_HOURLY"],
            price_usd=args.gcp,
            price_scaled=int(args.gcp * (10 ** PRICE_DECIMALS)),
        ))

    if not updates:
        print("\nNo price updates specified.")
        print("Use --aws, --azure, and/or --gcp to specify prices.")
        print("Example: --aws 3.85 --azure 2.12 --gcp 3.88")
        sys.exit(1)

    # Validate prices
    for update in updates:
        if update.price_usd <= 0:
            print(f"ERROR: Price must be positive: {update.asset_name} = {update.price_usd}")
            sys.exit(1)
        if update.price_usd > 100:
            print(f"WARNING: Price seems high: {update.asset_name} = ${update.price_usd}/hr")

    # Execute updates
    print("\n" + "=" * 60)
    print("EXECUTING PRICE UPDATES")
    print("=" * 60)

    try:
        if args.batch and len(updates) > 1:
            tx_hash = updater.batch_update_prices(updates)
        else:
            for update in updates:
                tx_hash = updater.update_single_price(update)

        # Log updates
        updater.log_updates(updates, tx_hash)

        # Final summary
        print("\n" + "=" * 60)
        print("SUCCESS!")
        print("=" * 60)
        print(f"Transaction: https://sepolia.etherscan.io/tx/{tx_hash}")
        print("\nUpdated prices:")
        for update in updates:
            print(f"  {update.asset_name}: ${update.price_usd:.4f}/hr")
        print("=" * 60)

    except Exception as e:
        print("\n" + "=" * 60)
        print("ERROR: Update failed!")
        print("=" * 60)
        print(f"  {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

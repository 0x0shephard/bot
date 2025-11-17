#!/usr/bin/env python3
"""
ByteStrike Oracle Price Updater
Updates H100 GPU hourly prices on Sepolia testnet using CuOracle commit-reveal scheme

Usage:
    python update_oracle_price.py --csv gpu_prices.csv --asset-id H100

Requirements:
    pip install web3 python-dotenv pandas
"""

import csv
import os
import time
import secrets
from datetime import datetime
from pathlib import Path
from typing import Optional

from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Sepolia Testnet Configuration
SEPOLIA_RPC_URL = os.getenv("SEPOLIA_RPC_URL", "https://eth-sepolia.g.alchemy.com/v2/YOUR_ALCHEMY_KEY")
PRIVATE_KEY = os.getenv("ORACLE_UPDATER_PRIVATE_KEY")  # Oracle updater wallet private key
ORACLE_CONTRACT_ADDRESS = "0x3cA2Da03e4b6dB8fe5a24c22Cf5EB2A34B59cbad"  # Your deployed CuOracle address

# CuOracle ABI (only the functions we need)
CUORACLE_ABI = [
    {
        "inputs": [
            {"internalType": "bytes32", "name": "_assetId", "type": "bytes32"},
            {"internalType": "bytes32", "name": "_commitHash", "type": "bytes32"}
        ],
        "name": "commitPrice",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "_assetId", "type": "bytes32"},
            {"internalType": "uint256", "name": "_price", "type": "uint256"},
            {"internalType": "uint256", "name": "_nonce", "type": "uint256"}
        ],
        "name": "updatePrices",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "_assetId", "type": "bytes32"}],
        "name": "getPrice",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "minCommitRevealDelay",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]


class OraclePriceUpdater:
    """Updates CuOracle prices using commit-reveal scheme"""

    def __init__(self, rpc_url: str, private_key: str, oracle_address: str):
        """Initialize Web3 connection and contract"""
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))

        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to Sepolia RPC: {rpc_url}")

        print(f"✅ Connected to Sepolia testnet")
        print(f"   Chain ID: {self.w3.eth.chain_id}")
        print(f"   Latest block: {self.w3.eth.block_number}")

        # Set up account
        self.account = Account.from_key(private_key)
        self.address = self.account.address
        print(f"   Updater address: {self.address}")

        # Get balance
        balance = self.w3.eth.get_balance(self.address)
        balance_eth = self.w3.from_wei(balance, 'ether')
        print(f"   Balance: {balance_eth:.4f} ETH")

        if balance == 0:
            print("⚠️  WARNING: Zero balance! Get Sepolia ETH from faucet:")
            print("   https://sepoliafaucet.com/")

        # Initialize contract
        self.oracle = self.w3.eth.contract(
            address=Web3.to_checksum_address(oracle_address),
            abi=CUORACLE_ABI
        )
        print(f"   Oracle contract: {oracle_address}")

        # Get oracle configuration
        try:
            self.min_delay = self.oracle.functions.minCommitRevealDelay().call()
            print(f"   Min commit-reveal delay: {self.min_delay} seconds")
        except Exception as e:
            print(f"⚠️  Could not read oracle config: {e}")
            self.min_delay = 60  # Default 1 minute

    def read_price_from_csv(self, csv_file: str, asset_name: str = "H100") -> Optional[float]:
        """
        Read latest GPU price from CSV file

        Supports two CSV formats:
        1. h100_gpu_index.csv format (from gpu_index_calculator.py):
           Total_Weight_Percent,Total_Weighted_Price,Full_Index_Price,Hyperscalers_Only_Price,Non_Hyperscalers_Only_Price,Hyperscaler_Weight,Non_Hyperscaler_Weight,Calculation_Date
           83.75,317.32,3.78,4.16,3.03,55.84,27.91,2025-11-14 12:49:50

        2. Legacy format:
           timestamp,asset,price
           2025-11-14 10:00:00,H100,3.75
        """
        try:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

                if not rows:
                    print(f"❌ CSV file is empty: {csv_file}")
                    return None

                # Check if this is the h100_gpu_index.csv format
                if 'Full_Index_Price' in rows[0]:
                    # This is the h100_gpu_index.csv format
                    latest = rows[-1]  # Get last row
                    price = float(latest['Full_Index_Price'])
                    timestamp = latest.get('Calculation_Date', 'unknown')

                    print(f"📊 Latest H100 Index Price from CSV:")
                    print(f"   Timestamp: {timestamp}")
                    print(f"   Full Index Price: ${price:.4f}/hour")
                    print(f"   Hyperscalers Only: ${float(latest['Hyperscalers_Only_Price']):.4f}/hour")
                    print(f"   Non-Hyperscalers Only: ${float(latest['Non_Hyperscalers_Only_Price']):.4f}/hour")
                    print(f"   Total Weight: {float(latest['Total_Weight_Percent']):.2f}%")

                    return price
                else:
                    # Legacy format
                    asset_rows = [r for r in rows if r.get('asset', '').upper() == asset_name.upper()]

                    if not asset_rows:
                        print(f"❌ No rows found for asset: {asset_name}")
                        return None

                    latest = asset_rows[-1]  # Get last row
                    price = float(latest['price'])
                    timestamp = latest.get('timestamp', 'unknown')

                    print(f"📊 Latest price from CSV:")
                    print(f"   Timestamp: {timestamp}")
                    print(f"   Asset: {asset_name}")
                    print(f"   Price: ${price:.2f}/hour")

                    return price

        except FileNotFoundError:
            print(f"❌ CSV file not found: {csv_file}")
            return None
        except Exception as e:
            print(f"❌ Error reading CSV: {e}")
            return None

    def commit_price(self, asset_id: bytes, price_wei: int, nonce: int) -> str:
        """
        Step 1: Commit price hash to oracle

        Returns transaction hash
        """
        # Create commitment hash: keccak256(abi.encodePacked(price, nonce))
        commit_hash = Web3.solidity_keccak(
            ['uint256', 'uint256'],
            [price_wei, nonce]
        )

        print(f"\n🔐 Committing price...")
        print(f"   Asset ID: {asset_id.hex()}")
        print(f"   Commit hash: {commit_hash.hex()}")
        print(f"   Nonce: {nonce}")

        # Build transaction
        tx = self.oracle.functions.commitPrice(
            asset_id,
            commit_hash
        ).build_transaction({
            'from': self.address,
            'nonce': self.w3.eth.get_transaction_count(self.address),
            'gas': 200000,
            'maxFeePerGas': self.w3.eth.gas_price * 2,
            'maxPriorityFeePerGas': self.w3.to_wei(1, 'gwei'),
            'chainId': 11155111  # Sepolia
        })

        # Sign and send
        signed_tx = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

        print(f"   Tx hash: {tx_hash.hex()}")
        print(f"   Waiting for confirmation...")

        # Wait for receipt
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt['status'] == 1:
            print(f"   ✅ Commit successful!")
            print(f"   Gas used: {receipt['gasUsed']}")
            return tx_hash.hex()
        else:
            print(f"   ❌ Commit failed!")
            raise Exception("Commit transaction failed")

    def reveal_price(self, asset_id: bytes, price_wei: int, nonce: int) -> str:
        """
        Step 2: Reveal price to oracle (after delay)

        Returns transaction hash
        """
        print(f"\n🔓 Revealing price...")
        print(f"   Asset ID: {asset_id.hex()}")
        print(f"   Price: {price_wei} wei ({self.w3.from_wei(price_wei, 'ether'):.2f})")
        print(f"   Nonce: {nonce}")

        # Build transaction
        tx = self.oracle.functions.updatePrices(
            asset_id,
            price_wei,
            nonce
        ).build_transaction({
            'from': self.address,
            'nonce': self.w3.eth.get_transaction_count(self.address),
            'gas': 200000,
            'maxFeePerGas': self.w3.eth.gas_price * 2,
            'maxPriorityFeePerGas': self.w3.to_wei(1, 'gwei'),
            'chainId': 11155111
        })

        # Sign and send
        signed_tx = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

        print(f"   Tx hash: {tx_hash.hex()}")
        print(f"   Waiting for confirmation...")

        # Wait for receipt
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt['status'] == 1:
            print(f"   ✅ Reveal successful!")
            print(f"   Gas used: {receipt['gasUsed']}")
            return tx_hash.hex()
        else:
            print(f"   ❌ Reveal failed!")
            raise Exception("Reveal transaction failed")

    def get_current_price(self, asset_id: bytes) -> float:
        """Get current price from oracle"""
        try:
            price_wei = self.oracle.functions.getPrice(asset_id).call()
            price_eth = self.w3.from_wei(price_wei, 'ether')
            return float(price_eth)
        except Exception as e:
            print(f"⚠️  Could not read current price: {e}")
            return 0.0

    def update_price(self, asset_name: str, price_usd: float):
        """
        Complete price update flow: commit -> wait -> reveal

        Args:
            asset_name: Name of asset (e.g., "H100", "A100")
            price_usd: Price in USD (will be converted to wei for 1e18 precision)
        """
        print(f"\n{'='*60}")
        print(f"🚀 Starting price update for {asset_name}")
        print(f"{'='*60}")

        # Convert asset name to bytes32
        asset_id = Web3.keccak(text=asset_name)

        # Get current price
        current_price = self.get_current_price(asset_id)
        print(f"\n📈 Price change:")
        print(f"   Current: ${current_price:.2f}/hour")
        print(f"   New: ${price_usd:.2f}/hour")
        print(f"   Change: {((price_usd - current_price) / current_price * 100) if current_price > 0 else 0:.2f}%")

        # Convert price to wei (scale by 1e18 for precision)
        # Example: $3.75 -> 3.75 * 1e18 = 3750000000000000000
        price_wei = self.w3.to_wei(price_usd, 'ether')

        # Generate random nonce
        nonce = secrets.randbits(256)

        # Step 1: Commit
        commit_tx = self.commit_price(asset_id, price_wei, nonce)
        print(f"\n   View on Etherscan:")
        print(f"   https://sepolia.etherscan.io/tx/{commit_tx}")

        # Step 2: Wait for minimum delay
        print(f"\n⏳ Waiting {self.min_delay} seconds for commit-reveal delay...")
        for remaining in range(self.min_delay, 0, -1):
            print(f"   {remaining} seconds remaining...", end='\r')
            time.sleep(1)
        print("\n   ✅ Delay complete!")

        # Step 3: Reveal
        reveal_tx = self.reveal_price(asset_id, price_wei, nonce)
        print(f"\n   View on Etherscan:")
        print(f"   https://sepolia.etherscan.io/tx/{reveal_tx}")

        # Verify update
        updated_price = self.get_current_price(asset_id)
        print(f"\n✅ Price update complete!")
        print(f"   Oracle now reports: ${updated_price:.2f}/hour")

        if abs(updated_price - price_usd) < 0.01:
            print(f"   ✅ Verification successful!")
        else:
            print(f"   ⚠️  Price mismatch - expected ${price_usd:.2f}, got ${updated_price:.2f}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Update ByteStrike Oracle prices from CSV')
    parser.add_argument('--csv', default='h100_gpu_index.csv', help='Path to CSV file with GPU prices (default: h100_gpu_index.csv)')
    parser.add_argument('--asset-id', default='H100', help='Asset identifier (default: H100)')
    parser.add_argument('--price', type=float, help='Manual price override (skips CSV)')

    args = parser.parse_args()

    # Validate environment
    if not PRIVATE_KEY:
        print("❌ ERROR: ORACLE_UPDATER_PRIVATE_KEY not set in .env file")
        print("\nCreate a .env file with:")
        print("ORACLE_UPDATER_PRIVATE_KEY=0xYOUR_PRIVATE_KEY_HERE")
        print("SEPOLIA_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/YOUR_ALCHEMY_KEY")
        return

    # Initialize updater
    try:
        updater = OraclePriceUpdater(
            rpc_url=SEPOLIA_RPC_URL,
            private_key=PRIVATE_KEY,
            oracle_address=ORACLE_CONTRACT_ADDRESS
        )
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return

    # Get price
    if args.price:
        price = args.price
        print(f"📊 Using manual price: ${price:.2f}/hour")
    else:
        price = updater.read_price_from_csv(args.csv, args.asset_id)
        if price is None:
            return

    # Update oracle
    try:
        updater.update_price(args.asset_id, price)
        print(f"\n{'='*60}")
        print(f"🎉 SUCCESS! Oracle updated on Sepolia testnet")
        print(f"{'='*60}\n")
    except Exception as e:
        print(f"\n❌ Update failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

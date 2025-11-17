#!/usr/bin/env python3
"""
H100 GPU Price Oracle - Smart Contract Updater
Pushes H100 GPU index price to Sepolia testnet smart contract

Usage:
    python push_to_contract.py --csv h100_gpu_index.csv
    python push_to_contract.py --price 3.75

Requirements:
    pip install web3 python-dotenv
"""

import csv
import os
import json
from datetime import datetime
from typing import Optional

from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Sepolia Testnet Configuration
SEPOLIA_RPC_URL = os.getenv("SEPOLIA_RPC_URL", "https://rpc.sepolia.org")
PRIVATE_KEY = os.getenv("ORACLE_UPDATER_PRIVATE_KEY") or os.getenv("WALLET_PRIVATE_KEY")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "0x3cA2Da03e4b6dB8fe5a24c22Cf5EB2A34B59cbad")

# H100PriceOracle ABI - setPrice contract
H100_ORACLE_ABI = [
    {
        "type": "function",
        "name": "setPrice",
        "inputs": [{"name": "newPrice", "type": "uint256", "internalType": "uint256"}],
        "outputs": [],
        "stateMutability": "nonpayable"
    },
    {
        "type": "function",
        "name": "getPrice",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256", "internalType": "uint256"}],
        "stateMutability": "view"
    },
    {
        "type": "function",
        "name": "decimals",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint8", "internalType": "uint8"}],
        "stateMutability": "view"
    }
]


class H100PriceUpdater:
    """Updates H100 GPU price on Sepolia smart contract"""

    def __init__(self, rpc_url: str, private_key: str, contract_address: str):
        """Initialize Web3 connection and contract"""
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))

        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to Sepolia RPC: {rpc_url}")

        print(f"Connected to Sepolia testnet")
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
            print("   WARNING: Zero balance! Get Sepolia ETH from faucet:")
            print("   https://sepoliafaucet.com/")

        # Initialize contract
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=H100_ORACLE_ABI
        )
        print(f"   Contract address: {contract_address}")

        # Get contract decimals
        try:
            self.decimals = self.contract.functions.decimals().call()
            print(f"   Contract decimals: {self.decimals}")
        except Exception as e:
            print(f"   Could not read decimals: {e}")
            self.decimals = 2  # Default to 2 decimals (cents)
            print(f"   Using default decimals: {self.decimals}")

        # Get current price
        try:
            current_price = self.contract.functions.getPrice().call()
            current_price_usd = current_price / (10 ** self.decimals)
            print(f"   Current price: ${current_price_usd:.4f}/hour ({current_price} raw)")
        except Exception as e:
            print(f"   Could not read current price: {e}")

    def read_price_from_csv(self, csv_file: str) -> Optional[float]:
        """
        Read latest GPU price from CSV file

        Supports two CSV formats:
        1. h100_gpu_index.csv format (from gpu_index_calculator.py):
           Total_Weight_Percent,Total_Weighted_Price,Full_Index_Price,...

        2. Legacy format:
           timestamp,asset,price
        """
        try:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

                if not rows:
                    print(f"CSV file is empty: {csv_file}")
                    return None

                # Check if this is the h100_gpu_index.csv format
                if 'Full_Index_Price' in rows[0]:
                    latest = rows[-1]
                    price = float(latest['Full_Index_Price'])
                    timestamp = latest.get('Calculation_Date', 'unknown')

                    print(f"\nLatest H100 Index Price from CSV:")
                    print(f"   Timestamp: {timestamp}")
                    print(f"   Full Index Price: ${price:.4f}/hour")
                    print(f"   Hyperscalers Only: ${float(latest.get('Hyperscalers_Only_Price', 0)):.4f}/hour")
                    print(f"   Non-Hyperscalers Only: ${float(latest.get('Non_Hyperscalers_Only_Price', 0)):.4f}/hour")
                    print(f"   Total Weight: {float(latest.get('Total_Weight_Percent', 0)):.2f}%")

                    return price
                else:
                    # Legacy format
                    asset_rows = [r for r in rows if r.get('asset', '').upper() == 'H100']

                    if not asset_rows:
                        print(f"No H100 rows found in CSV")
                        return None

                    latest = asset_rows[-1]
                    price = float(latest['price'])
                    timestamp = latest.get('timestamp', 'unknown')

                    print(f"\nLatest price from CSV:")
                    print(f"   Timestamp: {timestamp}")
                    print(f"   Price: ${price:.2f}/hour")

                    return price

        except FileNotFoundError:
            print(f"CSV file not found: {csv_file}")
            return None
        except Exception as e:
            print(f"Error reading CSV: {e}")
            return None

    def get_current_price(self) -> Optional[int]:
        """Get current price from contract (raw value with decimals)"""
        try:
            price_raw = self.contract.functions.getPrice().call()
            return price_raw
        except Exception as e:
            print(f"   Could not read current price: {e}")
            return None

    def update_price(self, price_usd: float) -> str:
        """
        Update H100 price on the smart contract

        Args:
            price_usd: Price in USD (e.g., 3.75 for $3.75/hour)

        Returns:
            Transaction hash
        """
        print(f"\n{'='*60}")
        print(f"Updating H100 Price on Sepolia")
        print(f"{'='*60}")

        # Convert USD to contract format based on decimals
        # e.g., if decimals=2: $3.75 -> 375
        # e.g., if decimals=4: $3.75 -> 37500
        price_scaled = int(price_usd * (10 ** self.decimals))

        # Get current price for comparison
        current_price_raw = self.get_current_price()
        if current_price_raw is not None:
            current_price_usd = current_price_raw / (10 ** self.decimals)
            print(f"\nPrice change:")
            print(f"   Current: ${current_price_usd:.4f}/hour ({current_price_raw} raw)")
            print(f"   New: ${price_usd:.4f}/hour ({price_scaled} raw)")
            if current_price_usd > 0:
                change_pct = ((price_usd - current_price_usd) / current_price_usd) * 100
                print(f"   Change: {change_pct:+.2f}%")
        else:
            print(f"\nNew price: ${price_usd:.4f}/hour ({price_scaled} raw)")

        # Build transaction
        print(f"\nBuilding transaction...")
        tx = self.contract.functions.setPrice(price_scaled).build_transaction({
            'from': self.address,
            'nonce': self.w3.eth.get_transaction_count(self.address),
            'gas': 100000,
            'maxFeePerGas': self.w3.eth.gas_price * 2,
            'maxPriorityFeePerGas': self.w3.to_wei(1, 'gwei'),
            'chainId': 11155111  # Sepolia
        })

        # Sign transaction
        print(f"Signing transaction...")
        signed_tx = self.account.sign_transaction(tx)

        # Send transaction
        print(f"Sending transaction...")
        # Handle both old and new Web3.py versions
        if hasattr(signed_tx, 'raw_transaction'):
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        else:
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

        tx_hash_hex = tx_hash.hex()
        print(f"   Transaction hash: {tx_hash_hex}")

        # Wait for receipt
        print(f"Waiting for confirmation...")
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt['status'] == 1:
            print(f"\nTransaction successful!")
            print(f"   Block number: {receipt['blockNumber']}")
            print(f"   Gas used: {receipt['gasUsed']}")
            print(f"   Effective gas price: {self.w3.from_wei(receipt['effectiveGasPrice'], 'gwei'):.2f} gwei")

            # Calculate cost
            cost_eth = self.w3.from_wei(receipt['gasUsed'] * receipt['effectiveGasPrice'], 'ether')
            print(f"   Transaction cost: {cost_eth:.6f} ETH")

            print(f"\n   View on Etherscan:")
            print(f"   https://sepolia.etherscan.io/tx/{tx_hash_hex}")

            # Verify update
            new_price_raw = self.get_current_price()
            if new_price_raw is not None:
                new_price_usd = new_price_raw / (10 ** self.decimals)
                print(f"\n   Verification: Contract now reports ${new_price_usd:.4f}/hour")

                if new_price_raw == price_scaled:
                    print(f"   Price update verified successfully!")
                else:
                    print(f"   WARNING: Price mismatch - expected {price_scaled}, got {new_price_raw}")

            # Log the update
            self.log_update(price_usd, tx_hash_hex, receipt['blockNumber'])

            return tx_hash_hex
        else:
            print(f"\nTransaction FAILED!")
            print(f"   Check transaction on Etherscan for details")
            raise Exception("Transaction failed")

    def log_update(self, price_usd: float, tx_hash: str, block_number: int):
        """Log the price update to a JSON file"""
        log_file = "contract_update_log.json"

        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "index_price_usd": price_usd,
            "index_price_cents": int(price_usd * 100),
            "tx_hash": tx_hash,
            "block_number": block_number,
            "contract_address": CONTRACT_ADDRESS,
            "network": "sepolia"
        }

        # Load existing log or create new
        logs = []
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    logs = json.load(f)
            except Exception:
                logs = []

        logs.append(log_entry)

        # Keep last 100 entries
        if len(logs) > 100:
            logs = logs[-100:]

        # Save log
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)

        print(f"\n   Update logged to {log_file}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Update H100 GPU price on Sepolia smart contract')
    parser.add_argument('--csv', default='h100_gpu_index.csv', help='Path to CSV file with GPU prices (default: h100_gpu_index.csv)')
    parser.add_argument('--price', type=float, help='Manual price in USD (skips CSV reading)')

    args = parser.parse_args()

    # Validate environment
    if not PRIVATE_KEY:
        print("ERROR: Private key not set!")
        print("\nSet one of these environment variables:")
        print("  ORACLE_UPDATER_PRIVATE_KEY=0xYOUR_PRIVATE_KEY")
        print("  WALLET_PRIVATE_KEY=0xYOUR_PRIVATE_KEY")
        print("\nOr create a .env file with the variable.")
        return

    print(f"\n{'='*60}")
    print(f"H100 GPU Price Oracle - Contract Updater")
    print(f"{'='*60}\n")

    # Initialize updater
    try:
        updater = H100PriceUpdater(
            rpc_url=SEPOLIA_RPC_URL,
            private_key=PRIVATE_KEY,
            contract_address=CONTRACT_ADDRESS
        )
    except Exception as e:
        print(f"Failed to initialize: {e}")
        return

    # Get price
    if args.price:
        price = args.price
        print(f"\nUsing manual price: ${price:.2f}/hour")
    else:
        price = updater.read_price_from_csv(args.csv)
        if price is None:
            print(f"\nFailed to read price from CSV. Exiting.")
            return

    # Validate price
    if price <= 0:
        print(f"\nERROR: Price must be greater than 0 (got ${price:.2f})")
        return

    if price > 100:
        print(f"\nWARNING: Price ${price:.2f}/hour seems unusually high. Proceeding anyway...")

    # Update contract
    try:
        tx_hash = updater.update_price(price)
        print(f"\n{'='*60}")
        print(f"SUCCESS! H100 price updated to ${price:.2f}/hour")
        print(f"Transaction: {tx_hash}")
        print(f"{'='*60}\n")
    except Exception as e:
        print(f"\nUpdate failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

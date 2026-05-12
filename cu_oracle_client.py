#!/usr/bin/env python3
"""Shared CuOracle commit-reveal client for ByteStrike Sepolia price bots."""

import os
import secrets
import time
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from typing import Iterable, List, Optional, Tuple

from eth_account import Account
from web3 import Web3


SEPOLIA_CHAIN_ID = 11155111
DEFAULT_CU_ORACLE_ADDRESS = "0x97f557594bA32e51c0eA215B1886111F24E957af"
PRICE_DECIMALS = 18

INDEX_ASSET_IDS = {
    "H100_HOURLY": {
        "market": "H100-GPU-PERP",
        "asset_symbol": "H100-GPU",
        "asset_id": "0xa9d8df3b447ff129b06fedc7de1d9692d53d107f0233181fb333b0dd0fe7ff33",
    },
    "H100_HYPERSCALERS_HOURLY": {
        "market": "H100-HyperScalers-PERP",
        "asset_symbol": "H100-HyperScalers",
        "asset_id": "0x79bd03720e349eb16eb997b6c27d1abaf8534556adb4719e484d5030f87bb3bf",
    },
    "H100_NON_HYPERSCALERS_HOURLY": {
        "market": "H100-non-HyperScalers-PERP-V2",
        "asset_symbol": "H100-non-HyperScalers",
        "asset_id": "0x03e18761e22317ee1d8c89c0c8d944f1592ec6ef26b7264b391e3ba6aae51e65",
    },
}

H100_PROVIDER_ASSET_IDS = {
    "AWS_H100_HOURLY": {
        "market": "AWS-H100-PERP",
        "asset_symbol": "AWS-H100",
        "asset_id": "0x33474ec291744718e5d36573b65c7b5cbf85740c766ba61ff1fdf324408de00c",
    },
    "AZURE_H100_HOURLY": {
        "market": "AZURE-H100-PERP",
        "asset_symbol": "AZURE-H100",
        "asset_id": "0xe73f2cbece22cd622973b57c976d23b4d197f34245b506aad9296988be8312ed",
    },
    "GCP_H100_HOURLY": {
        "market": "GCP-H100-PERP",
        "asset_symbol": "GCP-H100",
        "asset_id": "0x59af16e64573d8c27d6eb69ab1f1672f1826f2ea1bfd32b037ed2686dc8c3e4b",
    },
}

CU_ORACLE_ABI = [
    {
        "type": "function",
        "name": "commitPrice",
        "inputs": [
            {"name": "_assetId", "type": "bytes32"},
            {"name": "_commit", "type": "bytes32"},
        ],
        "outputs": [],
        "stateMutability": "nonpayable",
    },
    {
        "type": "function",
        "name": "updatePrices",
        "inputs": [
            {"name": "_assetId", "type": "bytes32"},
            {"name": "_price", "type": "uint256"},
            {"name": "_nonce", "type": "bytes32"},
        ],
        "outputs": [],
        "stateMutability": "nonpayable",
    },
    {
        "type": "function",
        "name": "getLatestPrice",
        "inputs": [{"name": "_assetId", "type": "bytes32"}],
        "outputs": [
            {
                "name": "",
                "type": "tuple",
                "components": [
                    {"name": "price", "type": "uint256"},
                    {"name": "lastUpdatedAt", "type": "uint256"},
                ],
            }
        ],
        "stateMutability": "view",
    },
    {
        "type": "function",
        "name": "supportedAssets",
        "inputs": [{"name": "", "type": "bytes32"}],
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
    },
    {
        "type": "function",
        "name": "owner",
        "inputs": [],
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
    },
    {
        "type": "function",
        "name": "allowedRoles",
        "inputs": [{"name": "", "type": "address"}],
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
    },
    {
        "type": "function",
        "name": "minCommitRevealDelay",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
    },
    {
        "type": "function",
        "name": "maxCommitAge",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
    },
]


@dataclass
class OraclePriceUpdate:
    asset_name: str
    market: str
    asset_id: str
    price_usd: float
    price_scaled: int
    nonce: Optional[bytes] = None

    @property
    def price_formatted(self) -> str:
        return f"${self.price_usd:.6f}/hr"


def price_to_x18(price_usd: float) -> int:
    scaled = (Decimal(str(price_usd)) * (Decimal(10) ** PRICE_DECIMALS)).quantize(
        Decimal("1"),
        rounding=ROUND_DOWN,
    )
    return int(scaled)


def asset_update(asset_name: str, asset_config: dict, price_usd: float) -> OraclePriceUpdate:
    return OraclePriceUpdate(
        asset_name=asset_name,
        market=asset_config["market"],
        asset_id=asset_config["asset_id"],
        price_usd=price_usd,
        price_scaled=price_to_x18(price_usd),
    )


class CuOraclePriceUpdater:
    """Commits and reveals prices to ByteStrike CuOracle."""

    def __init__(self, rpc_url: str, private_key: str, oracle_address: Optional[str] = None):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to Sepolia RPC: {rpc_url}")

        self.account = Account.from_key(private_key)
        self.address = self.account.address
        self.oracle_address = Web3.to_checksum_address(oracle_address or DEFAULT_CU_ORACLE_ADDRESS)
        self.contract = self.w3.eth.contract(address=self.oracle_address, abi=CU_ORACLE_ABI)
        self._next_nonce: Optional[int] = None

        balance_eth = self.w3.from_wei(self.w3.eth.get_balance(self.address), "ether")
        owner = self.contract.functions.owner().call()
        can_commit = self.address.lower() == owner.lower() or self.contract.functions.allowedRoles(self.address).call()
        can_reveal = self.address.lower() == owner.lower()

        print("=" * 60)
        print("BYTESTRIKE CUORACLE PRICE UPDATER")
        print("=" * 60)
        print(f"Chain ID: {self.w3.eth.chain_id}")
        print(f"Latest block: {self.w3.eth.block_number}")
        print(f"Updater address: {self.address}")
        print(f"Balance: {balance_eth:.6f} ETH")
        print(f"CuOracle: {self.oracle_address}")
        print(f"Oracle owner: {owner}")
        print(f"Can commit: {can_commit}")
        print(f"Can reveal: {can_reveal}")
        print("=" * 60)

        if not can_commit:
            raise PermissionError("Updater is not oracle owner and does not have allowedRoles commit permission")
        if not can_reveal:
            raise PermissionError("CuOracle.updatePrices is owner-only; ORACLE_UPDATER_PRIVATE_KEY must be owner key")

    def _fee_fields(self) -> dict:
        priority_gwei = Decimal(os.getenv("ORACLE_MAX_PRIORITY_FEE_GWEI", "0.001"))
        priority_fee = int(priority_gwei * Decimal(10**9))
        latest_block = self.w3.eth.get_block("latest")
        base_fee = latest_block.get("baseFeePerGas")
        if base_fee is None:
            return {"gasPrice": self.w3.eth.gas_price}
        max_fee = max(int(base_fee) * 2 + priority_fee, priority_fee * 2)
        return {
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": priority_fee,
        }

    def _send_transaction(self, func, gas_limit: int) -> Tuple[str, dict]:
        if self._next_nonce is None:
            self._next_nonce = self.w3.eth.get_transaction_count(self.address, "pending")

        tx = func.build_transaction(
            {
                "from": self.address,
                "nonce": self._next_nonce,
                "gas": gas_limit,
                "chainId": SEPOLIA_CHAIN_ID,
                **self._fee_fields(),
            }
        )
        self._next_nonce += 1
        signed = self.account.sign_transaction(tx)
        raw_tx = getattr(signed, "raw_transaction", getattr(signed, "rawTransaction", signed))
        tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=240)
        if int(receipt.get("status", 0)) != 1:
            raise RuntimeError(f"Transaction reverted: {tx_hash.hex()}")
        return tx_hash.hex(), dict(receipt)

    def get_latest_price(self, asset_id: str) -> Tuple[int, int]:
        price, last_updated_at = self.contract.functions.getLatestPrice(asset_id).call()
        return int(price), int(last_updated_at)

    def get_latest_price_usd(self, asset_id: str) -> Optional[float]:
        try:
            price, _ = self.get_latest_price(asset_id)
        except Exception:
            return None
        if price == 0:
            return None
        return price / 10**PRICE_DECIMALS

    def _commit_hash(self, update: OraclePriceUpdate) -> bytes:
        assert update.nonce is not None
        return Web3.solidity_keccak(["uint256", "bytes32"], [update.price_scaled, update.nonce])

    def _prepare_update(self, update: OraclePriceUpdate) -> OraclePriceUpdate:
        if update.price_scaled <= 0:
            raise ValueError(f"{update.asset_name} price must be positive")
        if not self.contract.functions.supportedAssets(update.asset_id).call():
            raise ValueError(f"{update.asset_name} is not registered in CuOracle: {update.asset_id}")
        update.nonce = Web3.keccak(
            text=f"{update.asset_id}:{update.price_scaled}:{time.time_ns()}:{secrets.token_hex(16)}"
        )
        return update

    def commit_and_reveal(
        self,
        updates: Iterable[OraclePriceUpdate],
        verify: bool = True,
    ) -> Tuple[List[str], List[str]]:
        prepared = [self._prepare_update(update) for update in updates]
        if not prepared:
            raise ValueError("No price updates provided")

        print("\nPrepared CuOracle updates:")
        for update in prepared:
            current = self.get_latest_price_usd(update.asset_id)
            if current:
                change_pct = ((update.price_usd - current) / current) * 100
                print(
                    f"  {update.asset_name} ({update.market}): "
                    f"${current:.6f} -> {update.price_formatted} ({change_pct:+.2f}%)"
                )
            else:
                print(f"  {update.asset_name} ({update.market}): {update.price_formatted}")

        commit_hashes: List[str] = []
        print("\nCommitting prices...")
        for update in prepared:
            commit = self._commit_hash(update)
            tx_hash, receipt = self._send_transaction(
                self.contract.functions.commitPrice(update.asset_id, commit),
                gas_limit=100_000,
            )
            commit_hashes.append(tx_hash)
            print(f"  commit {update.asset_name}: {tx_hash} (gas {receipt['gasUsed']:,})")

        min_delay = int(self.contract.functions.minCommitRevealDelay().call())
        wait_seconds = max(int(os.getenv("ORACLE_REVEAL_WAIT_SECONDS", "3")), min_delay + 1)
        print(f"\nWaiting {wait_seconds}s before reveal...")
        time.sleep(wait_seconds)

        reveal_hashes: List[str] = []
        print("\nRevealing prices...")
        for update in prepared:
            tx_hash, receipt = self._send_transaction(
                self.contract.functions.updatePrices(update.asset_id, update.price_scaled, update.nonce),
                gas_limit=120_000,
            )
            reveal_hashes.append(tx_hash)
            print(f"  reveal {update.asset_name}: {tx_hash} (gas {receipt['gasUsed']:,})")

        if verify:
            print("\nVerifying revealed prices...")
            for update in prepared:
                latest, last_updated_at = self.get_latest_price(update.asset_id)
                if latest != update.price_scaled:
                    raise RuntimeError(
                        f"Verification failed for {update.asset_name}: expected {update.price_scaled}, got {latest}"
                    )
                print(f"  {update.asset_name}: {update.price_formatted} at commit timestamp {last_updated_at}")
        else:
            print("\nSkipping on-chain verification (--no-verify)")

        return commit_hashes, reveal_hashes

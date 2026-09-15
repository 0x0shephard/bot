import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from cu_oracle_client import CuOraclePriceUpdater


class _TxHash(bytes):
    def hex(self):
        return "0xabc123"


class _FakeEth:
    def __init__(self):
        self.pending_nonces = iter((7, 8))
        self.send_attempts = 0

    def get_transaction_count(self, _address, _state):
        return next(self.pending_nonces)

    def get_block(self, _block):
        return {"baseFeePerGas": 1_000_000_000}

    def send_raw_transaction(self, _raw_tx):
        self.send_attempts += 1
        if self.send_attempts == 1:
            raise RuntimeError(
                "in-flight transaction limit reached for delegated accounts"
            )
        return _TxHash(b"accepted")

    def wait_for_transaction_receipt(self, _tx_hash, timeout):
        assert timeout == 240
        return {"status": 1, "gasUsed": 42_000}


class _FakeFunction:
    def __init__(self):
        self.nonces = []

    def build_transaction(self, tx):
        self.nonces.append(tx["nonce"])
        return tx


class CuOracleTransactionRetryTest(unittest.TestCase):
    def test_retries_delegated_account_limit_with_fresh_pending_nonce(self):
        updater = CuOraclePriceUpdater.__new__(CuOraclePriceUpdater)
        updater.w3 = SimpleNamespace(eth=_FakeEth())
        updater.address = "0x0000000000000000000000000000000000000001"
        updater.account = SimpleNamespace(
            sign_transaction=lambda tx: SimpleNamespace(raw_transaction=b"signed")
        )
        updater._next_nonce = None
        function = _FakeFunction()

        retry_env = {
            "ORACLE_TX_RETRY_ATTEMPTS": "2",
            "ORACLE_TX_RETRY_BASE_SECONDS": "1",
            "ORACLE_TX_RETRY_MAX_SECONDS": "1",
            "ORACLE_TX_RETRY_JITTER_SECONDS": "0",
        }
        with patch.dict(os.environ, retry_env), patch("cu_oracle_client.time.sleep") as sleep:
            tx_hash, receipt = updater._send_transaction(function, gas_limit=120_000)

        self.assertEqual(tx_hash, "0xabc123")
        self.assertEqual(receipt["status"], 1)
        self.assertEqual(function.nonces, [7, 8])
        self.assertEqual(updater._next_nonce, 9)
        sleep.assert_called_once_with(1)


if __name__ == "__main__":
    unittest.main()

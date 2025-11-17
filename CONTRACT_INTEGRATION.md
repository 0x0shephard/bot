# H100 GPU Price Oracle - Smart Contract Integration

## Quick Start

### 1. Deploy Smart Contract

Use the contract code in `SEPOLIA_DEPLOYMENT_GUIDE.md` and deploy to Sepolia testnet via:
- [Remix IDE](https://remix.ethereum.org) (easiest)
- Hardhat
- Foundry

### 2. Get Testnet ETH

Get free Sepolia ETH from faucets:
- https://sepoliafaucet.com/
- https://www.alchemy.com/faucets/ethereum-sepolia
- https://faucet.quicknode.com/ethereum/sepolia

### 3. Set Up GitHub Secrets

Add these secrets in: **Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | Description | Example |
|------------|-------------|---------|
| `SEPOLIA_RPC_URL` | Sepolia RPC endpoint | `https://rpc.sepolia.org` |
| `WALLET_PRIVATE_KEY` | Your wallet private key | `0x123...` |
| `CONTRACT_ADDRESS` | Deployed contract address | `0xABC...` |
| `CONTRACT_ABI` | Contract ABI (JSON) | `[{"inputs":[]...}]` |

⚠️ **IMPORTANT**: Export your private key from MetaMask. NEVER share or commit this key!

### 4. Test Locally (Optional)

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your values
nano .env

# Test the script
python push_to_contract.py
```

### 5. Workflow Integration

The GitHub Actions workflow will automatically:
1. Run all scrapers
2. Calculate GPU index
3. Push final price to your Sepolia contract

Monitor at: https://sepolia.etherscan.io/address/YOUR_CONTRACT_ADDRESS

## How It Works

```
┌─────────────┐
│  Scrapers   │  Collect H100 prices from 40+ providers
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Combined   │  Merge all JSON data
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Normalize  │  Convert currencies, calculate per-GPU price
└──────┬──────┘
       │
       ▼
┌─────────────┐
│GPU Index    │  Calculate weighted average: $X.XX/hr
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Blockchain  │  Push to Sepolia Smart Contract
└─────────────┘
```

## Contract Functions

### Write (Requires Gas)
- `updatePrice(uint256 _price)` - Updates H100 price on-chain

### Read (Free)
- `getCurrentPrice()` - Returns price in cents
- `getLastUpdated()` - Returns last update timestamp
- `updateCount` - Returns number of updates

## Price Format

The script sends price in **cents** to save gas and avoid decimals:
- Index: $2.45/hr → Contract: 245 (cents)
- Index: $3.50/hr → Contract: 350 (cents)

To get dollars: `contractPrice / 100`

## Monitoring

### View Transaction History
https://sepolia.etherscan.io/address/YOUR_CONTRACT_ADDRESS

### View Latest Update
```bash
# Read from contract
python -c "
from web3 import Web3
w3 = Web3(Web3.HTTPProvider('https://rpc.sepolia.org'))
contract = w3.eth.contract(address='YOUR_ADDRESS', abi=YOUR_ABI)
price_cents = contract.functions.getCurrentPrice().call()
print(f'Current H100 Price: \${price_cents/100:.2f}/hr')
"
```

### Transaction Log
Each update is saved to `contract_update_log.json`:
```json
{"timestamp": "2025-10-30T12:00:00", "index_price": 2.45, "tx_hash": "0x...", "block_number": 12345}
```

## Troubleshooting

### "Missing required environment variables"
- Add all 4 secrets in GitHub Settings → Secrets

### "Insufficient funds for gas"
- Get more Sepolia ETH from faucets
- Typical gas cost: ~0.001 ETH per update

### "execution reverted: Only owner can update"
- The wallet must match the contract owner
- Check: `contract.functions.owner().call()`

### "Transaction failed"
- Increase gas limit in `push_to_contract.py` (line 85)
- Check Sepolia network status

## Security Best Practices

✅ **DO:**
- Use GitHub Secrets for sensitive data
- Keep minimal ETH in automation wallet
- Monitor transaction logs
- Verify contract on Etherscan

❌ **DON'T:**
- Commit private keys to git
- Share your `.env` file
- Use mainnet for testing
- Store large amounts of ETH in automation wallet

## Cost Estimation

### Per Update (Sepolia)
- Gas: ~50,000 units
- Cost: ~0.0005 ETH (~$0.50 on mainnet)

### Monthly Cost (2 updates/day)
- Updates: 60/month
- Gas: 0.03 ETH/month
- Cost: ~$30/month on mainnet (testnet is free!)

## Advanced Configuration

### Custom Update Function

Edit `push_to_contract.py` line 82-86 to match your contract:

```python
# Simple price update
transaction = self.contract.functions.updatePrice(
    price_scaled
).build_transaction({...})

# With timestamp
transaction = self.contract.functions.updatePriceWithTimestamp(
    price_scaled,
    int(time.time())
).build_transaction({...})

# With metadata
transaction = self.contract.functions.updateGPUIndex(
    price_scaled,
    index_data['provider_count'],
    int(time.time())
).build_transaction({...})
```

### Gas Optimization

Reduce costs by:
1. Batching updates (update every 6/12 hours instead of continuous)
2. Using Layer 2 (Optimism, Arbitrum) instead of Ethereum
3. Implementing price change threshold (only update if price changes >5%)

## Frontend Integration

Read the price in your dApp:

```javascript
const Web3 = require('web3');
const web3 = new Web3('https://rpc.sepolia.org');

const abi = [...]; // Your contract ABI
const address = '0x...'; // Your contract address

const contract = new web3.eth.Contract(abi, address);

// Get current price
const priceCents = await contract.methods.getCurrentPrice().call();
const priceUSD = priceCents / 100;

console.log(`H100 GPU: $${priceUSD}/hr`);

// Get last update time
const timestamp = await contract.methods.getLastUpdated().call();
const date = new Date(timestamp * 1000);

console.log(`Last updated: ${date.toLocaleString()}`);
```

## Support

For issues or questions:
1. Check `SEPOLIA_DEPLOYMENT_GUIDE.md` for detailed setup
2. Review GitHub Actions logs
3. Verify contract on Sepolia Etherscan
4. Check transaction history for errors

## Resources

- [Remix IDE](https://remix.ethereum.org)
- [Sepolia Faucets](https://sepoliafaucet.com/)
- [Sepolia Etherscan](https://sepolia.etherscan.io)
- [Web3.py Docs](https://web3py.readthedocs.io/)
- [Solidity Docs](https://docs.soliditylang.org/)

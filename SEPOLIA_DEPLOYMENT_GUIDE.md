# H100 GPU Price Oracle - Sepolia Deployment Guide

## Overview
This guide helps you deploy and interact with a smart contract that stores H100 GPU pricing data on Sepolia testnet.

## Smart Contract Example

Here's a simple Solidity contract for storing GPU prices:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract H100PriceOracle {
    address public owner;
    uint256 public currentPrice;  // Price in cents (e.g., 250 = $2.50/hr)
    uint256 public lastUpdated;
    uint256 public updateCount;
    
    event PriceUpdated(uint256 newPrice, uint256 timestamp, uint256 updateNumber);
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can update");
        _;
    }
    
    constructor() {
        owner = msg.sender;
        lastUpdated = block.timestamp;
    }
    
    // Update the H100 price (price in cents)
    function updatePrice(uint256 _price) external onlyOwner {
        require(_price > 0, "Price must be greater than 0");
        currentPrice = _price;
        lastUpdated = block.timestamp;
        updateCount++;
        emit PriceUpdated(_price, block.timestamp, updateCount);
    }
    
    // Get current price in cents
    function getCurrentPrice() external view returns (uint256) {
        return currentPrice;
    }
    
    // Get price in dollars (with 2 decimals)
    function getPriceInDollars() external view returns (uint256) {
        return currentPrice; // Frontend divides by 100
    }
    
    // Get last update timestamp
    function getLastUpdated() external view returns (uint256) {
        return lastUpdated;
    }
    
    // Transfer ownership
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "Invalid address");
        owner = newOwner;
    }
}
```

## Setup Instructions

### 1. Deploy Contract to Sepolia

**Option A: Using Remix IDE**
1. Go to https://remix.ethereum.org
2. Create new file `H100PriceOracle.sol`
3. Paste the contract code above
4. Compile with Solidity 0.8.0+
5. Deploy using MetaMask connected to Sepolia
6. Copy the deployed contract address

**Option B: Using Hardhat**
```bash
npm install --save-dev hardhat
npx hardhat init
# Follow prompts and deploy
```

### 2. Get Sepolia Testnet ETH

Get free Sepolia ETH from faucets:
- https://sepoliafaucet.com/
- https://www.alchemy.com/faucets/ethereum-sepolia
- https://faucet.quicknode.com/ethereum/sepolia

### 3. Set Up Environment Variables

Create a `.env` file in your project root (DO NOT COMMIT THIS):

```bash
# Sepolia RPC URL (choose one)
SEPOLIA_RPC_URL=https://rpc.sepolia.org
# OR use Infura: https://sepolia.infura.io/v3/YOUR_PROJECT_ID
# OR use Alchemy: https://eth-sepolia.g.alchemy.com/v2/YOUR_API_KEY

# Your wallet private key (export from MetaMask)
WALLET_PRIVATE_KEY=0x1234567890abcdef...

# Deployed contract address
CONTRACT_ADDRESS=0xYourContractAddress...

# Contract ABI (minified, from Remix or Hardhat)
CONTRACT_ABI='[{"inputs":[],"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint256","name":"newPrice","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"timestamp","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"updateNumber","type":"uint256"}],"name":"PriceUpdated","type":"event"},{"inputs":[],"name":"currentPrice","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getCurrentPrice","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getLastUpdated","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getPriceInDollars","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"lastUpdated","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"owner","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"newOwner","type":"address"}],"name":"transferOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"updateCount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"_price","type":"uint256"}],"name":"updatePrice","outputs":[],"stateMutability":"nonpayable","type":"function"}]'
```

### 4. Install Python Dependencies

```bash
pip install web3 python-dotenv
```

### 5. Load Environment Variables

Add to your Python script:

```python
from dotenv import load_dotenv
load_dotenv()
```

Or export them in terminal:
```bash
export SEPOLIA_RPC_URL="https://rpc.sepolia.org"
export WALLET_PRIVATE_KEY="0x..."
export CONTRACT_ADDRESS="0x..."
export CONTRACT_ABI='[...]'
```

### 6. GitHub Secrets (for Actions)

For the GitHub workflow, add these as repository secrets:

1. Go to your repo → Settings → Secrets and variables → Actions
2. Add new secrets:
   - `SEPOLIA_RPC_URL`
   - `WALLET_PRIVATE_KEY`
   - `CONTRACT_ADDRESS`
   - `CONTRACT_ABI`

### 7. Test Locally

```bash
python push_to_contract.py
```

### 8. Add to GitHub Workflow

The workflow will automatically call `push_to_contract.py` after calculating the GPU index.

## Contract Functions

### Write Functions (Require Gas)
- `updatePrice(uint256 _price)` - Update H100 price (owner only)
- `transferOwnership(address newOwner)` - Transfer contract ownership

### Read Functions (Free)
- `getCurrentPrice()` - Get current price in cents
- `getPriceInDollars()` - Get price (divide by 100 for dollars)
- `getLastUpdated()` - Get timestamp of last update
- `updateCount` - Get number of updates

## Verify Contract on Etherscan

1. Go to https://sepolia.etherscan.io
2. Search for your contract address
3. Click "Contract" → "Verify and Publish"
4. Enter compiler version and contract code
5. Submit for verification

## Monitor Updates

View your contract updates at:
- https://sepolia.etherscan.io/address/YOUR_CONTRACT_ADDRESS

## Troubleshooting

### "Insufficient funds for gas"
- Get more Sepolia ETH from faucets

### "execution reverted: Only owner can update"
- Ensure the wallet private key matches the contract owner

### "Transaction failed"
- Check gas limit (increase if needed)
- Verify contract address is correct
- Ensure price value is > 0

### "Cannot connect to Sepolia"
- Try alternative RPC URLs (Infura, Alchemy)
- Check network connectivity

## Security Notes

⚠️ **IMPORTANT SECURITY WARNINGS:**

1. **Never commit private keys** - Use `.env` files in `.gitignore`
2. **Use GitHub Secrets** - Store sensitive data in repository secrets
3. **Test on Testnet First** - Always test on Sepolia before mainnet
4. **Limit Wallet Funds** - Only keep minimal ETH in automation wallet
5. **Monitor Gas Prices** - Set reasonable gas limits
6. **Verify Contracts** - Always verify on Etherscan

## Example Transaction

After running `push_to_contract.py`, you'll see:

```
✅ Transaction successful!
   Transaction Hash: 0xabc123...
   Block Number: 12345678
   Gas Used: 45678
   Explorer: https://sepolia.etherscan.io/tx/0xabc123...
```

## Frontend Integration

To read the price from your frontend:

```javascript
const Web3 = require('web3');
const web3 = new Web3('https://rpc.sepolia.org');

const contractABI = [...]; // Your ABI
const contractAddress = '0x...'; // Your contract

const contract = new web3.eth.Contract(contractABI, contractAddress);

// Read current price
const priceInCents = await contract.methods.getCurrentPrice().call();
const priceInDollars = priceInCents / 100;

console.log(`H100 Price: $${priceInDollars}/hr`);
```

## Advanced Features

Consider adding to your contract:
- Historical price tracking
- Multiple GPU types (H100, A100, etc.)
- Provider-specific prices
- Time-weighted averages
- Access control for multiple updaters
- Emergency pause functionality

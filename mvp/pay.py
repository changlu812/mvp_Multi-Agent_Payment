from web3 import Web3
import os
import requests
import json
from datetime import datetime, timedelta

LITE_API = "https://pusdc-kite-testnet.zentra.dev"

# 限额配置
LIMITS = {
    "single_transaction": 1000,  # 单笔限额（USDT）
    "daily": 5000,               # 日限额
    "monthly": 50000             # 月限额
}

# 交易记录存储文件
TRANSACTION_RECORD_FILE = "transaction_records.json"

# 白名单配置
WHITELIST = {
    "receivers": ["0x742d35Cc6634C0532925a3b844Bc454e4438f44e", "0x376d3737Da2A540318BbA02A98f03a97d1DD8f6d"],
    "time_windows": ["00:00-23:59"]  # 24小时允许交易
}

def load_transaction_records():
    """
    加载交易记录
    """
    if os.path.exists(TRANSACTION_RECORD_FILE):
        try:
            with open(TRANSACTION_RECORD_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_transaction_record(agent_address, amount, timestamp):
    """
    保存交易记录
    """
    records = load_transaction_records()
    if agent_address not in records:
        records[agent_address] = []
    records[agent_address].append({
        "amount": amount,
        "timestamp": timestamp
    })
    with open(TRANSACTION_RECORD_FILE, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

def check_limits(agent_address, amount):
    """
    检查交易限额
    """
    # 1. 检查单笔限额
    if amount > LIMITS["single_transaction"]:
        print(f"❌ 超出单笔限额 {LIMITS['single_transaction']} USDT")
        return False
    
    # 2. 检查日限额
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_start_timestamp = int(today_start.timestamp())
    
    records = load_transaction_records()
    daily_amount = 0
    monthly_amount = 0
    
    if agent_address in records:
        for record in records[agent_address]:
            record_time = datetime.fromtimestamp(record["timestamp"])
            # 计算日累计
            if record["timestamp"] >= today_start_timestamp:
                daily_amount += record["amount"]
            # 计算月累计
            if (now.year == record_time.year and 
                now.month == record_time.month):
                monthly_amount += record["amount"]
    
    # 检查日限额
    if daily_amount + amount > LIMITS["daily"]:
        print(f"❌ 超出日限额 {LIMITS['daily']} USDT")
        print(f"今日已使用: {daily_amount} USDT, 本次尝试: {amount} USDT")
        return False
    
    # 检查月限额
    if monthly_amount + amount > LIMITS["monthly"]:
        print(f"❌ 超出月限额 {LIMITS['monthly']} USDT")
        print(f"本月已使用: {monthly_amount} USDT, 本次尝试: {amount} USDT")
        return False
    
    return True

def check_whitelist(to_addr):
    """
    检查接收方是否在白名单中
    """
    if WHITELIST["receivers"] and to_addr not in WHITELIST["receivers"]:
        print(f"❌ 接收地址不在白名单中: {to_addr}")
        return False
    return True

# KiteAI Testnet Settings
RPC_URL = "https://rpc-testnet.gokite.ai/"
CHAIN_ID = 2368

LITE_ADDR = '0x35A9b4E215c8Bf9b7bFF83Ac08aD32dEE8D19F64'
USDT_ADDR = "0x0fF5393387ad2f9f691FD6Fd28e07E3969e27e63"

# Address book for recipients
address_book = {
    "target": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",  # Example address
    "alice": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",   # Example
    "bob": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"      # Example
}

# ERC20 Minimal ABI
ERC20_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"}
]

# LITE ABI (JSON format converted from string list)
LITE_ABI = [
    {"inputs": [{"name": "", "type": "address"}], "name": "privacyBalances", "outputs": [{"name": "", "type": "bytes"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "", "type": "address"}], "name": "privacyNonces", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "toAddr", "type": "address"}, {"name": "amountCipher", "type": "bytes"}, {"name": "currentSenderBalanceCipher", "type": "bytes"}, {"name": "updatedSenderBalanceCipher", "type": "bytes"}, {"name": "currentReceiverBalanceCipher", "type": "bytes"}, {"name": "updatedReceiverBalanceCipher", "type": "bytes"}, {"name": "signature", "type": "bytes"}], "name": "privacyTransfer", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [], "name": "chain_identifier", "outputs": [{"name": "", "type": "string"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "tick", "outputs": [{"name": "", "type": "string"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "erc20", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "witness", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"}
]

# Initialize Web3
w3 = Web3(Web3.HTTPProvider(RPC_URL))

def connect_and_check():
    if w3.is_connected():
        print(f"✅ Connected to KiteAI Testnet")
        print(f"Network ID: {w3.eth.chain_id}")

        # Create USDT contract instance
        usdt_contract = w3.eth.contract(address=USDT_ADDR, abi=ERC20_ABI)

        try:
            # Query USDT balance of LITE contract
            balance_raw = usdt_contract.functions.balanceOf(LITE_ADDR).call()
            try:
                decimals = usdt_contract.functions.decimals().call()
            except:
                decimals = 6 # Default for USDT if call fails
            
            balance_formatted = balance_raw / (10 ** decimals)
            
            print(f"\n--- Balance Info ---")
            print(f"LITE Contract: {LITE_ADDR}")
            print(f"USDT Balance: {balance_formatted} USDT")
            print(f"--------------------\n")
        except Exception as e:
            print(f"❌ Error querying USDT balance: {e}")
    else:
        print("❌ Failed to connect to KiteAI Testnet")

address_book = {
    'laowang': '0x35A9b4E215c8Bf9b7bFF83Ac08aD32dEE8D19F64', # Just as example, use real address here if different
    'target': '0x376d3737Da2A540318BbA02A98f03a97d1DD8f6d' # Example employee
}

def pay(name, amount_human=1.0):
    print(f"🚀 Starting payment for: {name}")
    
    # 1. Setup account and contract
    private_key = os.getenv("ETH_PRIVATE_KEY")
    if not private_key:
        print("❌ ETH_PRIVATE_KEY not found")
        return

    # Initialize Kite Agent
    from agent import KiteAgent
    agent = KiteAgent(private_key)
    account_addr = w3.to_checksum_address(agent.get_address())
    print(f"✅ Using Kite Agent with address: {account_addr}")
    
    # Get traditional account for fallback
    account = w3.eth.account.from_key(private_key)
    
    to_addr_raw = address_book.get(name)
    if not to_addr_raw:
        print(f"❌ Name {name} not found in address book")
        return
    to_addr = w3.to_checksum_address(to_addr_raw)

    # 2. 检查限额
    print("🔍 Checking transaction limits...")
    if not check_limits(account_addr, amount_human):
        return
    
    # 3. 检查白名单
    print("🔍 Checking whitelist...")
    if not check_whitelist(to_addr):
        return

    lite_contract = w3.eth.contract(address=w3.to_checksum_address(LITE_ADDR), abi=LITE_ABI)
    
    # Convert amount to internal representation (assuming 6 decimals for USDT)
    amount_parsed = int(amount_human * 10**6)

    try:
        # Fetch current state from contract
        print("📡 Fetching nonces and balances...")
        sender_nonce = lite_contract.functions.privacyNonces(account_addr).call()
        sender_balance = lite_contract.functions.privacyBalances(account_addr).call()
        receiver_balance = lite_contract.functions.privacyBalances(to_addr).call()

        # 2. Fetch signature from API
        print("✍️ Requesting witness signature from API...")
        
        params = {
            "from_addr": account.address,
            "to_addr": to_addr,
            "amount": str(amount_parsed),
            "nonce": str(sender_nonce + 1),
            "sender_balance": "0x" + sender_balance.hex() if sender_balance else "0x",
            "receiver_balance": "0x" + receiver_balance.hex() if receiver_balance else "0x"
        }
        
        response = requests.get(f"{LITE_API}/api/sign_transfer", params=params)
        if response.status_code != 200:
            print(f"❌ API Error: {response.status_code} - {response.text}")
            return
            
        data = response.json()
        print("✅ Witness signature received")

        # 3. Call privacyTransfer
        print("🔗 Building privacyTransfer transaction...")
        
        # Prepare arguments (ensure hex strings are converted to bytes)
        tx_args = [
            to_addr,
            w3.to_bytes(hexstr=data['amount_cipher']),
            w3.to_bytes(hexstr=data['current_sender_balance']),
            w3.to_bytes(hexstr=data['updated_sender_balance']),
            w3.to_bytes(hexstr=data['current_receiver_balance']),
            w3.to_bytes(hexstr=data['updated_receiver_balance']),
            w3.to_bytes(hexstr=data['signature'])
        ]
        
        # Build transaction
        nonce = w3.eth.get_transaction_count(account_addr)
        
        # Determine gas (optional: let it be estimated)
        transaction = lite_contract.functions.privacyTransfer(*tx_args).build_transaction({
            'chainId': CHAIN_ID,
            'gas': 2000000, # A safe limit for privacy operations
            'gasPrice': w3.eth.gas_price,
            'nonce': nonce,
            'from': account_addr
        })
        
        print("🔐 Signing transaction...")
        # Try to use Kite Agent for signing
        try:
            signed_tx = agent.sign_transaction(transaction)
            if hasattr(signed_tx, 'rawTransaction'):
                # Traditional signed transaction
                print("📡 Sending transaction to network...")
                tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            else:
                # Kite Agent signed transaction (simplified)
                print("📡 Sending transaction to network using Kite Agent...")
                # Fallback to traditional sending for now
                signed_tx = w3.eth.account.sign_transaction(transaction, private_key)
                tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        except Exception as e:
            print(f"⚠️  Kite Agent signing failed, falling back to traditional signing: {e}")
            signed_tx = w3.eth.account.sign_transaction(transaction, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        print(f"⌛ Transaction sent! Hash: {tx_hash.hex()}")
        print("Waiting for confirmation...")
        
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status == 1:
            print("✅ Transaction successful!")
            # 保存交易记录
            timestamp = int(datetime.now().timestamp())
            save_transaction_record(account_addr, amount_human, timestamp)
            print(f"📝 Transaction record saved: {amount_human} USDT to {to_addr}")
        else:
            print("❌ Transaction failed (status 0)")

    except Exception as e:
        print(f"❌ Payment failed: {e}")

if __name__ == "__main__":
    connect_and_check()
    # Example: Pay 'target' 1.0 USDT
    pay('target', 1.0)

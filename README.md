# 🫧 Bubble Check

**Bubble Check** is a fast Telegram bot that helps you:
- 🧠 Get full crypto token info with simple commands
- 🗺️ Generate interactive bubble maps to visualize token holder networks
- 🔎 Search tokens by contract address or symbol across multiple chains

All using **Python** and **Aiogram**!

---

## ✨ Features
- **/bm** — Get bubble map of token holders  
- **/bi** — Fetch token information (with auto token search support)
- Supports **contract address** or **token symbol** input
- Inline buttons to open **interactive visualizations**
- Real-time token searching powered by CoinGecko API
- Multi-chain support

---

## 🛠️ Tech Stack
- **Python 3.11+**
- **Aiogram** (Telegram bot framework)
- **HTTPX** (for async API calls)
- **CoinGecko API** (for token search)
- **Custom IBMStorage** (screenshot hosting)
- **D3.js visualization** (for bubble maps - accessed via link)
- **Custom Logger** for structured logging

---

## 🚀 Quick Start

1. Clone the repo:
   ```bash
   git clone https://github.com/emperorsixpacks/bubble_bot.git
   cd bubble-check
   ```

2. Install dependencies:
   ```bash
   pip install && uv sync
   ```

3. Create a `.env` file with:
   ```
   TELEGRAM_BOT_TOKEN=your-telegram-bot-token
   COIN_GECKO_API_KEY=your-coingecko-api-key
   IBM_API_KEY=your-ibm-storage-api-key
   IBM_SERVICE_ENDPOINT=your-ibm-endpoint
   IBM_BUCKET_INSTANCE_ID=your-ibm-instance-id
   IBM_BUCKET_NAME=your-ibm-bucket-name
   ```

4. Run the bot:
   ```bash
   python bot.py
   ```

5. or using docker:
   ```bash

   #build the image
   docker build -t bubble_bot . 
   
   #run the container in detached mode
   docker run -d --name bubble-check-container bubble-check

   ```


---

## 🧩 Supported Chains
- Ethereum (ETH)
- BNB Smart Chain (BSC)
- Polygon (POLY)
- Fantom (FTM)
- Avalanche (AVAX)
- Cronos (CRO)
- Arbitrum (ARBI)
- Base (BASE)
- Solana (SOL)
- Sonic (SONIC)

---

## 📜 Commands
| Command | Description |
|:--------|:------------|
| `/bm 0xcontract/chain` | Get bubble map for a token |
| `/bi $symbol/chain` or `/bi 0xcontract/chain` | Get token info and bubble map |

**Examples:**
- `/bm 0x123...abc/eth`
- `/bi $usdt/eth`
- `/bi 0xabc...def/bsc`

---

## ⚠️ Disclaimer
- **Always DYOR.** This bot pulls public data and is for research only.
- **No financial advice** is provided.
- Bubble maps are fetched from third-party sources; accuracy not guaranteed.

---

## 📣 Contribution
PRs, suggestions, and issues are super welcome!  
Just fork it, hack on it, and submit your magic. 🧙‍♂️

---

# 🧠 About
Bubble Check was built with love to help crypto traders, researchers, and curious minds explore token ecosystems more easily.

---

---

## 🌟 Notes
- You **don't need to deploy your own bubble map visualization** — bot fetches links!
- Future upgrades may include caching, gas analysis, and wallet clustering.


# ⛽🔥 Gas Station Finder Bot 🔥⛽

A powerful Telegram bot that finds real gas stations using Google Places API and delivers results in horizontal CSV format.

## 🌟 Features

- ⚡ **Real-time data** from Google Places API
- 🎯 **Multiple ZIP codes** support (up to 10 per request)
- 💾 **Horizontal CSV format** - Seller Name1, Address1, City1, State1, Zip1, etc.
- 🚀 **Lightning fast** results with smart caching
- 🎨 **Beautiful UI** with emojis and status updates
- 💰 **Cost optimized** with 30-minute caching

## 📱 How to Use

1. Start the bot: `/start`
2. Send any US ZIP code(s):
   - Single: `90210`
   - Multiple: `90210 10001 77001`
   - Up to 10 ZIP codes per request
3. Get instant CSV download + beautiful preview

## 🚀 Quick Deploy to Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com)

## 📋 Prerequisites

- **Telegram Bot Token** - Get from [@BotFather](https://t.me/BotFather)
- **Google Cloud API Key** - Get from [Google Cloud Console](https://console.cloud.google.com/)

## 🛠️ Local Setup

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/gas-station-bot.git
cd gas-station-bot
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Set Environment Variables
```bash
export TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
export GOOGLE_API_KEY="your_google_api_key"
```

### 4. Run Bot
```bash
python gas_station_bot.py
```

## ☁️ Deploy to Render

### Step 1: Push to GitHub
1. Create new repository on GitHub
2. Upload all files
3. Push your code

### Step 2: Deploy on Render
1. Go to [Render.com](https://render.com)
2. Connect your GitHub account
3. Create new **Web Service**
4. Select your repository
5. Configure:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python gas_station_bot.py`
6. Add Environment Variables:
   - `TELEGRAM_BOT_TOKEN` = your bot token
   - `GOOGLE_API_KEY` = your API key
7. Deploy!

## 🔧 Google Cloud Setup

### Enable Required APIs
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project or select existing
3. Enable these APIs:
   - **Places API**
   - **Geocoding API**
4. Create API Key in **Credentials**
5. Restrict API key (recommended):
   - Application restrictions: None
   - API restrictions: Places API, Geocoding API

### API Costs
- **Geocoding API:** $5 per 1,000 requests
- **Places API (Nearby Search):** $32 per 1,000 requests  
- **Places API (Place Details):** $17 per 1,000 requests

**Estimated cost per ZIP code:** $0.10 - $0.50

## 📊 CSV Format

The bot creates horizontal CSV with this format:
```csv
Seller Name1,Seller Address1,Seller City1,Seller State1,Seller Zip1,Seller Name2,Seller Address2,Seller City2,Seller State2,Seller Zip2,...
Shell,123 Main St,Beverly Hills,CA,90210,Chevron,456 Oak Ave,Beverly Hills,CA,90210,...
```

## 🎯 Example Usage

### Single ZIP Code
```
User: 90210
Bot: Finds 5 gas stations in Beverly Hills, CA
```

### Multiple ZIP Codes  
```
User: 90210 10001 77001
Bot: Finds up to 5 stations per ZIP (15 total max)
```

### Maximum Capacity
```
User: 90210 10001 77001 60601 33101 94102 30309 02101 98101 75201
Bot: Handles all 10 ZIP codes (50 stations max)
```

## 📁 Project Structure

```
gas-station-bot/
├── gas_station_bot.py    # Main bot code
├── requirements.txt      # Python dependencies
├── README.md            # This file
├── .gitignore          # Git ignore file
├── Procfile            # Render deployment config
└── LICENSE             # MIT License
```

## 🔒 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token from @BotFather | ✅ Yes |
| `GOOGLE_API_KEY` | Your Google Cloud API key | ✅ Yes |

## 🚨 Important Notes

- **API Limits:** Google Places has daily quotas
- **Caching:** Results cached for 30 minutes to save costs
- **Rate Limiting:** Built-in delays between API calls
- **Error Handling:** Graceful handling of API failures

## 📞 Support

- 🐛 **Bug Reports:** Open an issue
- 💡 **Feature Requests:** Create a discussion
- 📧 **Contact:** your-email@example.com

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Google Places API** for real gas station data
- **python-telegram-bot** for Telegram integration
- **Render.com** for easy deployment

---

**⭐ If this helped you, please star the repository!**

**🔥 Happy gas station hunting! ⛽**

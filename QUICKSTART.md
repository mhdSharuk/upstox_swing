# Quick Start Guide

## 🚀 Getting Started in 5 Minutes

### Step 1: Install Dependencies (1 min)
```bash
pip install -r requirements.txt
```

### Step 2: Configure Credentials (2 min)

Edit `config/credentials.py`:
```python
UPSTOX_API_KEY = "your_upstox_api_key"
UPSTOX_API_SECRET = "your_upstox_api_secret"
UPSTOX_TOTP_SECRET = "your_2fa_secret"
GOOGLE_SHEET_ID = "your_google_sheet_id"
```

Place your Google service account JSON in project root as `service_account.json`

### Step 3: Run the Pipeline (2 min)
```bash
python main.py
```

That's it! 🎉

---

## 📋 Quick Checklist

Before running:
- [ ] Python 3.8+ installed
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Upstox API credentials configured
- [ ] Google Sheet created and shared with service account
- [ ] Service account JSON file in project root
- [ ] `config/credentials.py` updated with all values

---

## 🔍 What the Script Does

1. **Authenticates** with Upstox (browser opens for first-time login)
2. **Fetches** ~3000+ NSE equity instrument keys
3. **Downloads** historical data:
   - 125-minute candles (past quarter)
   - Daily candles (past 3 years)
4. **Calculates** 6 supertrend indicators:
   - 2 for 125-minute timeframe
   - 4 for daily timeframe
5. **Detects** flat base patterns (0.1% tolerance)
6. **Saves** to Google Sheets:
   - Sheet "125min_data": Latest 200 candles per stock
   - Sheet "daily_data": Latest 60 candles per stock

---

## ⏱️ Expected Runtime

- Small portfolio (100 stocks): ~5-10 minutes
- Medium portfolio (500 stocks): ~20-30 minutes
- Large portfolio (1000+ stocks): ~45-60 minutes

*Time varies based on internet speed and API rate limits*

---

## 📊 Output Location

Your Google Sheet will have 2 sheets:
- `125min_data` - 125-minute timeframe data
- `daily_data` - Daily timeframe data

View at: `https://docs.google.com/spreadsheets/d/{YOUR_SHEET_ID}`

---

## 🐛 Quick Fixes

### Token Expired?
```bash
# Delete the old token and run again
rm upstox_token.json
python main.py
```

### Google Sheets Auth Error?
```bash
# Verify service account file exists and has correct permissions
ls -la service_account.json
# Make sure the service account email has "Editor" access to your sheet
```

### Rate Limit Hit?
The script handles this automatically with retries. Just let it run.

---

## 📝 Logs

Check `upstox_supertrend.log` for detailed execution logs.

---

## 💡 Pro Tips

1. **First Run**: Takes longer as it fetches all historical data
2. **Token Expiry**: Upstox tokens expire at 3:30 AM IST daily
3. **Data Updates**: Run daily after market close for latest data
4. **Memory Usage**: Processing thousands of stocks uses ~2-4 GB RAM
5. **Interruption**: Safe to interrupt (Ctrl+C) and restart

---

## 🆘 Need Help?

1. Check `README.md` for detailed documentation
2. Review logs in `upstox_supertrend.log`
3. Verify credentials in `config/credentials.py`
4. Ensure all dependencies installed

---

## 🎯 Success Indicators

You'll know it worked when you see:
```
✓ PIPELINE COMPLETED SUCCESSFULLY!
Data saved to: https://docs.google.com/spreadsheets/d/{YOUR_SHEET_ID}
```

Open your Google Sheet and you should see data in both timeframe sheets!

# Railway Deployment Fix

## The Error You Got

Railway couldn't find a start command because it needs to know which file to run.

## Fix: Upload These 3 New Files

### **1. Procfile** (tells Railway this is a worker, not a web app)
```
worker: python idx_bot_simple_v2.py
```

### **2. nixpacks.toml** (Railway build configuration)
```toml
[phases.setup]
nixPkgs = ['python39']

[phases.install]
cmds = ['pip install -r requirements.txt']

[start]
cmd = 'python idx_bot_simple_v2.py'
```

### **3. idx_bot_simple_v2.py** (updated bot that reads BOT_TOKEN from environment)
This replaces `idx_bot_simple.py` - it now reads the token from Railway's environment variables.

## 📤 What to Upload to GitHub

**Upload these files:**
1. ✅ idx_bot_simple_v2.py (NEW - use this instead)
2. ✅ idx_disclosure_scraper.py
3. ✅ inspect_idx_structure.py
4. ✅ requirements.txt
5. ✅ Procfile (NEW)
6. ✅ nixpacks.toml (NEW)

**Don't upload:**
- ❌ idx_bot_simple.py (old version)
- ❌ Any .db files
- ❌ Any test files

## 🚀 Deployment Steps

### Step 1: Upload to GitHub
1. Go to your `idx-disclosure-bot` repository
2. Delete old `idx_bot_simple.py` if you uploaded it
3. Click "Add file" → "Upload files"
4. Drag these NEW files:
   - Procfile
   - nixpacks.toml
   - idx_bot_simple_v2.py
5. Commit changes

### Step 2: Railway Configuration
1. Go to Railway dashboard
2. Click your project
3. Go to **"Variables"** tab
4. Add variable:
   - Key: `BOT_TOKEN`
   - Value: Your token from @BotFather (e.g., `123456789:ABCdefGHI...`)
5. Click **"Settings"** → Scroll down → Click **"Redeploy"**

### Step 3: Check Logs
1. Click **"Deployments"** tab
2. Click latest deployment
3. You should see:
   ```
   Bot starting...
   Active subscribers: 0
   ```

✅ If you see that, the bot is running!

## 🧪 Test the Bot

1. Open Telegram
2. Find your bot (username you set with @BotFather)
3. Send `/start`
4. You should get the welcome message
5. Try `/latest` to test the scraper

## 🐛 If It Still Fails

Check Railway logs for errors. Common issues:

### "No module named 'telegram'"
→ Make sure `requirements.txt` is uploaded

### "BOT_TOKEN not set"
→ Add BOT_TOKEN in Railway Variables tab

### "Railpack process exited with an error"
→ Check that Procfile and nixpacks.toml are uploaded

### Scraper returns no data
→ IDX website structure might have changed
→ Run `inspect_idx_structure.py` locally first
→ Update the parser in `idx_disclosure_scraper.py`

## 📁 Final File Structure on GitHub

```
idx-disclosure-bot/
├── Procfile
├── nixpacks.toml
├── idx_bot_simple_v2.py
├── idx_disclosure_scraper.py
├── inspect_idx_structure.py
├── requirements.txt
└── SIMPLE_SETUP.md (optional)
```

That's it! The bot should now deploy successfully on Railway. 🚀

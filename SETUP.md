# Setup Instructions

Follow these steps to set up and run the AI News Content Agent.

## Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- Git (for version control)

## Installation Steps

### 1. Clone or Navigate to Project Directory

```bash
cd AI_News_Agent
```

### 2. Create Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file:
```bash
copy .env.example .env
```

Edit `.env` and add your credentials (see next section).

## Required Credentials

You need to obtain the following before running the agent:

### 1. Anthropic API Key

**STOP - Manual Action Required:**

To use Claude for LinkedIn post generation, you need an Anthropic API key.

1. Go to: https://console.anthropic.com/
2. Sign up or log in
3. Navigate to "API Keys" section
4. Click "Create Key"
5. Copy the key (starts with `sk-ant-`)
6. Paste it in your `.env` file:
   ```
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   ```

**Reply "done" when you have your API key.**

---

### 2. Gmail App Password

**STOP - Manual Action Required:**

To send emails, you need a Gmail App Password (not your regular password).

1. Go to your Google Account: https://myaccount.google.com/
2. Navigate to Security → 2-Step Verification (enable if not already)
3. Scroll down to "App passwords"
4. Select "Mail" and "Windows Computer"
5. Click "Generate"
6. Copy the 16-character password
7. Add to `.env`:
   ```
   SENDER_EMAIL=your.email@gmail.com
   SENDER_PASSWORD=your-16-char-app-password
   RECEIVER_EMAIL=your.email@gmail.com
   ```

**Reply "done" when you have your Gmail App Password.**

---

## Testing the Setup

Once you've configured your `.env` file, test each component:

### Test 1: News Fetching
```bash
python tests/test_news_fetch.py
```
This should fetch recent AI news articles.

### Test 2: Database
```bash
python tests/test_database.py
```
This tests duplicate detection.

### Test 3: Scoring
```bash
python tests/test_scoring.py
```
This tests the article ranking algorithm.

### Test 4: Full Run
```bash
python main.py
```
This runs the complete pipeline.

## Project Status

✅ News fetching from RSS feeds
✅ Duplicate detection with SQLite
✅ News scoring and ranking
⏳ LinkedIn post generation (requires API key)
⏳ Email sending (requires Gmail credentials)
⏳ GitHub Actions automation

## Next Steps

After testing, we'll implement:
1. Claude API integration for post generation
2. Email sending via SMTP
3. GitHub Actions for daily automation

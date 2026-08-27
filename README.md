# AI News Content Agent 🤖

An intelligent automation system that fetches the latest AI news, scores articles by relevance, generates engaging LinkedIn posts using Google Gemini AI, and delivers them to your inbox—ready to copy and paste.

## What It Does

Every time you run this agent:

1. **Fetches** latest AI news from 13+ premium sources (OpenAI, Anthropic, Google AI, arXiv, etc.)
2. **Filters** out articles you've already posted
3. **Scores** articles based on AI relevance, developer interest, innovation, and freshness
4. **Generates** a professional LinkedIn post using Google Gemini AI
5. **Emails** you a beautifully formatted HTML email with the post draft
6. **Tracks** posted articles to prevent duplicates

## Features

✅ **Multi-Source News Aggregation** - 13 AI/ML RSS feeds
✅ **Smart Scoring Algorithm** - Ranks articles by relevance, impact, and freshness
✅ **AI-Powered Content Generation** - Google Gemini creates engaging posts
✅ **Professional Email Delivery** - HTML formatted with metadata and stats
✅ **Duplicate Prevention** - SQLite database tracks posted content
✅ **Configurable** - Easy .env file configuration
✅ **Fully Tested** - Test suites for all major components
✅ **Free to Run** - Uses Google Gemini free tier (1,500 requests/day)

## Quick Start

### Prerequisites

- Python 3.8+
- Gmail account (for sending emails)
- Google Gemini API key (free)

### Installation

1. **Clone or download the project**
   ```bash
   cd AI_News_Agent
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your credentials:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   SENDER_EMAIL=your_email@gmail.com
   SENDER_PASSWORD=your_gmail_app_password
   RECEIVER_EMAIL=your_email@gmail.com
   ```

4. **Get your API keys**
   - **Gemini API**: Visit https://makersuite.google.com/app/apikey
   - **Gmail App Password**: Visit https://myaccount.google.com/apppasswords

### Run

```bash
python main.py
```

That's it! Check your email for your LinkedIn post draft.

## Project Structure

```
AI_News_Agent/
├── agents/                 # AI-powered agents
│   ├── news_scorer.py     # Scores and ranks articles
│   └── post_generator.py  # Generates LinkedIn posts (Gemini)
├── config/                # Configuration management
│   ├── __init__.py        # Config loader
│   └── sources.py         # RSS feed sources
├── database/              # Data persistence
│   ├── news_db.py         # SQLite database manager
│   └── news.db            # Article tracking database
├── models/                # Data models
│   └── __init__.py        # NewsArticle, LinkedInPost
├── services/              # External integrations
│   ├── news_fetcher.py    # RSS feed fetcher
│   └── email_service.py   # SMTP email sender
├── tests/                 # Test suites
│   ├── test_post_generator.py
│   ├── test_email_service.py
│   └── [other tests]
├── utils/                 # Utilities
│   └── logger.py          # Logging configuration
├── logs/                  # Application logs
├── docs/                  # Documentation
├── main.py               # Main application entry point
├── requirements.txt      # Python dependencies
├── .env.example         # Environment variable template
└── README.md            # This file
```

## Testing

### Test All Components
```bash
# Test post generation
python tests/test_post_generator.py

# Test email delivery
python tests/test_email_service.py

# Test news fetching
python tests/test_news_fetch.py

# Test database
python tests/test_database.py

# Test scoring
python tests/test_scoring.py
```

## Automation

### Daily Automation (Windows)

1. Open Task Scheduler
2. Create Basic Task
3. Trigger: Daily at your preferred time
4. Action: Start a program
   - Program: `python`
   - Arguments: `C:\path\to\AI_News_Agent\main.py`
   - Start in: `C:\path\to\AI_News_Agent`

### Daily Automation (Linux/Mac)

Add to crontab:
```bash
# Run daily at 9 AM
0 9 * * * cd /path/to/AI_News_Agent && python main.py
```

## API Usage & Costs

### Google Gemini (Free Tier)
- **Model**: gemini-3.6-flash
- **Rate Limits**: 15 requests/min, 1,500 requests/day
- **Cost**: $0 (free tier)
- **Perfect for**: 1 post per day

### Gmail SMTP
- **Cost**: Free
- **Requirements**: App password (2FA required)
- **Limits**: 500 emails/day (way more than needed)

## Troubleshooting

### "GEMINI_API_KEY not found"
- Check `.env` file exists (not `.env.example`)
- Verify API key is correct (no quotes needed)
- Make sure you've enabled the Generative Language API

### "SMTP authentication failed"
- Use Gmail app password, not regular password
- Enable 2-factor authentication first
- Visit: https://myaccount.google.com/apppasswords

### "No articles fetched"
- Some sources may be temporarily down
- arXiv usually has 100+ daily articles
- Check logs/agent.log for details

### "Post generation failed"
- Check Gemini API quota (1,500/day limit)
- Verify internet connection
- Try running test_post_generator.py to isolate issue

## Technologies Used

- **Python 3.8+**
- **Google Gemini API** - AI content generation
- **SQLite** - Duplicate detection database
- **Gmail SMTP** - Email delivery
- **feedparser** - RSS feed parsing
- **requests** - HTTP client

## License

MIT License - Use freely for personal or commercial projects

## Author

BSAI Student - Learning Project

---

**Built with ❤️ for AI content creators**

Last Updated: July 2026

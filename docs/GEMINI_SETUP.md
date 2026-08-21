# Google Gemini API Setup Guide

## Getting Your Gemini API Key

1. **Visit Google AI Studio**
   - Go to https://makersuite.google.com/app/apikey
   - Sign in with your Google account

2. **Create API Key**
   - Click "Create API Key"
   - Select or create a Google Cloud project
   - Copy the generated API key

3. **Add to .env File**
   ```bash
   GEMINI_API_KEY=your_actual_api_key_here
   ```

## Gemini Free Tier Limits

The free tier includes:
- 15 requests per minute (RPM)
- 1 million tokens per minute (TPM)
- 1,500 requests per day (RPD)

This is more than enough for our use case (1 post per day).

## API Model Used

We're using **gemini-pro** which is:
- Free to use
- Optimized for text generation
- Supports up to 30,720 input tokens
- Generates up to 2,048 output tokens

## Testing the Integration

Run the test script to verify everything works:

```bash
python tests/test_post_generator.py
```

## Troubleshooting

### Error: "API key not found"
- Make sure you've created a `.env` file (copy from `.env.example`)
- Check that `GEMINI_API_KEY` is set correctly
- No quotes needed around the API key value

### Error: "API key not valid"
- Verify the API key is correct
- Make sure you've enabled the Generative Language API in Google Cloud Console
- Try regenerating the API key

### Error: "Rate limit exceeded"
- You've exceeded the free tier limits
- Wait a minute and try again
- For production use, consider upgrading to paid tier

## Why Gemini Instead of Anthropic?

1. **No Billing Required**: Gemini's free tier doesn't require credit card setup
2. **Sufficient for Our Needs**: 1,500 requests/day is perfect for 1 post/day
3. **Good Quality**: Gemini Pro produces high-quality content generation
4. **Already Have API Key**: You mentioned having one from another project

## Next Steps

After setting up the API key:
1. Run `python tests/test_post_generator.py` to verify it works
2. Run the full pipeline with `python main.py`
3. Check your email for the generated LinkedIn post

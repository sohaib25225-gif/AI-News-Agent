# GitHub Actions Setup Guide

## Overview

This guide walks you through setting up GitHub Actions to run the AI News Agent automatically every day at 8:50 AM Pakistan Time.

## Step 1: Push Code to GitHub

If you haven't already:

```bash
cd "C:\Users\qari\OneDrive\Documents\MY_projects\AI_News_Agent"

# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Add AI News Agent with GitHub Actions workflow"

# Add remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/AI_News_Agent.git

# Push to GitHub
git push -u origin main
```

## Step 2: Add GitHub Secrets

GitHub Secrets allow you to securely store sensitive information like API keys and passwords.

### How to Add Secrets:

1. **Go to your GitHub repository**
   - Navigate to https://github.com/YOUR_USERNAME/AI_News_Agent

2. **Open Settings**
   - Click the "Settings" tab at the top of the repository

3. **Navigate to Secrets**
   - In the left sidebar, click "Secrets and variables"
   - Click "Actions"

4. **Add New Repository Secret**
   - Click the green "New repository secret" button

5. **Add Each Secret** (repeat for all 4 secrets):

   **Secret 1: GEMINI_API_KEY**
   ```
   Name: GEMINI_API_KEY
   Value: your_actual_gemini_api_key_here
   ```
   Click "Add secret"

   **Secret 2: SENDER_EMAIL**
   ```
   Name: SENDER_EMAIL
   Value: your_email@gmail.com
   ```
   Click "Add secret"

   **Secret 3: SENDER_PASSWORD**
   ```
   Name: SENDER_PASSWORD
   Value: your_gmail_app_password_here
   ```
   Click "Add secret"

   **Secret 4: RECEIVER_EMAIL**
   ```
   Name: RECEIVER_EMAIL
   Value: recipient_email@gmail.com
   ```
   Click "Add secret"

6. **Verify Secrets Are Added**
   - You should see all 4 secrets listed
   - You won't be able to see the values (they're encrypted)

## Step 3: Enable GitHub Actions

1. **Go to the Actions tab**
   - Click "Actions" at the top of your repository

2. **Enable Workflows** (if prompted)
   - Click "I understand my workflows, go ahead and enable them"

3. **Find Your Workflow**
   - You should see "Daily AI News Agent" workflow listed

## Step 4: Test the Workflow (Manual Trigger)

Before waiting for the scheduled run, test it manually:

1. **Go to Actions tab**
   - Click on "Daily AI News Agent" workflow

2. **Run workflow manually**
   - Click "Run workflow" button (on the right)
   - Select branch: "main"
   - Click green "Run workflow" button

3. **Monitor the run**
   - Click on the running workflow to see live logs
   - Wait for it to complete (~1-2 minutes)

4. **Check your email**
   - You should receive the LinkedIn post draft

## Step 5: Verify Scheduled Run

The workflow is now scheduled to run automatically:
- **Time**: 8:50 AM Pakistan Time (PKT)
- **Frequency**: Daily
- **Timezone**: Asia/Karachi (UTC+5)

### When Will It Run?

The workflow runs at:
- **3:50 AM UTC** = **8:50 AM PKT**

You can verify the next scheduled run in the Actions tab.

## Troubleshooting

### Workflow Doesn't Appear

**Problem**: Actions tab shows no workflows

**Solution**:
1. Make sure `.github/workflows/daily-news-agent.yml` was pushed to GitHub
2. Check the file is in the correct location
3. Verify YAML syntax is correct

### Workflow Fails

**Problem**: Workflow runs but fails

**Solution**:
1. Click on the failed workflow run
2. Expand the failed step to see error logs
3. Common issues:
   - Missing secrets (double-check all 4 are added)
   - Invalid API key (verify Gemini API key works)
   - SMTP authentication failed (verify Gmail app password)

### No Email Received

**Problem**: Workflow succeeds but no email arrives

**Solution**:
1. Check spam folder
2. Verify SENDER_EMAIL and RECEIVER_EMAIL secrets are correct
3. Check workflow logs for SMTP errors

### Manual Trigger Button Missing

**Problem**: Can't find "Run workflow" button

**Solution**:
1. Make sure you're on the "Actions" tab
2. Click on "Daily AI News Agent" in the left sidebar
3. The button appears on the right side (may need to scroll)

## Monitoring

### View Workflow History
- Go to Actions tab
- Click "Daily AI News Agent"
- See all past runs with status (success/failure)

### View Logs
- Click on any workflow run
- Expand steps to see detailed logs
- Logs are kept for 90 days

### Failed Runs
- If a run fails, you'll see a red X
- Click to view logs and diagnose
- Logs are uploaded as artifacts (downloadable for 7 days)

## Security Notes

### Secrets Best Practices
✅ Secrets are encrypted and never exposed in logs
✅ Only visible to workflow runs
✅ Can be updated anytime without changing code
✅ Not accessible to forks of your repository

### Important Warnings
⚠️ Never commit `.env` file to GitHub
⚠️ Never hardcode API keys in code
⚠️ Use secrets for all sensitive data
⚠️ Rotate keys if accidentally exposed

## Schedule Details

### Cron Expression
```
50 3 * * *
```

Breakdown:
- `50` - Minute (50)
- `3` - Hour (3 AM UTC)
- `*` - Every day of month
- `*` - Every month
- `*` - Every day of week

### Converting Times

Pakistan Time (PKT) is UTC+5:
- 8:50 AM PKT = 3:50 AM UTC

To change the schedule:
1. Edit `.github/workflows/daily-news-agent.yml`
2. Modify the cron expression
3. Commit and push changes

Example: Run at 9:00 AM PKT instead:
```yaml
- cron: '0 4 * * *'  # 4:00 AM UTC = 9:00 AM PKT
```

## Testing Checklist

Before relying on automated runs:

- [ ] All 4 secrets added to GitHub
- [ ] Manual workflow run succeeds
- [ ] Email received from manual run
- [ ] Workflow appears in Actions tab
- [ ] Schedule is correct (8:50 AM PKT = 3:50 AM UTC)
- [ ] No sensitive data in repository code

## Next Steps

After setup:
1. Wait for first scheduled run (tomorrow at 8:50 AM PKT)
2. Check your email
3. Monitor Actions tab for success
4. Copy post to LinkedIn and engage!

## Support

If issues persist:
1. Check workflow logs in Actions tab
2. Verify secrets are correctly named (case-sensitive)
3. Test locally with `python main.py` first
4. Review logs/agent.log for errors

---

**Setup Complete!** Your AI News Agent will now run automatically every day at 8:50 AM Pakistan Time. 🎉

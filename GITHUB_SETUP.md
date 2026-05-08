# GitHub Private Repo Setup

Your code is currently pushed to: `https://github.com/ConductorAILabs/claudecade`

## Make it Private

1. Go to https://github.com/ConductorAILabs/claudecade
2. Click **Settings** (top right)
3. Scroll to **Danger Zone**
4. Click **Change repository visibility**
5. Select **Private**
6. Confirm

Done. The repo is now private and only accessible to people you invite.

## Automatic Builds Configured

You now have two automatic systems:

### 1. Git Hook (Local)
Every time you commit, the zip is automatically rebuilt:
```bash
git add ctype.py  # or any game file
git commit -m "Update game"
# -> builds claudcade.zip automatically
```

### 2. Netlify Build (Deployment)
When you push to GitHub and Netlify deploys, the zip rebuilds automatically.

## Workflow

1. **Change game files** → commit → zip rebuilds locally
2. **Push to GitHub** → Netlify deploys → zip rebuilds on server
3. **Players download** → always get latest zip

No manual `claudecadeupdate` needed.

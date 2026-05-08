# Claudecade Update System

You now have three ways to update the claudecade games:

## 1. Web Button (Easiest)

Click the **[ UPDATE GAMES ]** button on the Claudecade interface. This rebuilds the package on the server.

## 2. Command Line (One-time use)

From the claudegames directory, run:
```bash
./claudecadeupdate
```

Or from anywhere by using the full path:
```bash
~/Desktop/claudegames/claudecadeupdate
```

## 3. Shell Alias (Permanent)

Add this to your `~/.zshrc` or `~/.bashrc`:

```bash
alias claudecadeupdate='~/Desktop/claudegames/claudecadeupdate'
```

Then reload your shell:
```bash
source ~/.zshrc  # or ~/.bashrc
```

Now you can run `claudecadeupdate` from anywhere.

## Workflow

1. **Make changes** to game files (ctype.py, fight.py, claudtra.py, finalclaudesy/, etc.)
2. **Run the update command** to rebuild claudcade.zip
3. **Tell players to re-download** the zip from https://starlit-macaron-113a83.netlify.app/claudcade.zip

The web button does this automatically on your deployed site.

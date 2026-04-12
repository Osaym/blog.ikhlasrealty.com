# Blog Automation

**Fully guided one-command workflow!**

## How to Use

**Just run one command:**

```bash
bash update.command
```

(or double-click `update.command`)

**The script will guide you through everything:**

### Step 1: Download Main Newsletter
The script pauses and shows:
```
📥 Ready to download the newsletter!

Instructions:
  1. Open https://realtytimes.com/cm/tonycamarra in your browser
  2. Solve CAPTCHA if needed
  3. File → Save As → 'Webpage, Complete'
  4. Save it to the 'newsletter_download/' folder

Press RETURN when newsletter is downloaded:
```

### Step 2: Download Articles
After processing the newsletter, the script automatically opens all article URLs in your browser:
```
📥 Opening 9 articles in your browser...

  Opening article 1/9...
  Opening article 2/9...
  ...

✓ All articles opened in browser!

Instructions:
  1. For each browser tab that opened:
     - File → Save As → 'Webpage, Complete'
     - Save to 'article_downloads/' folder
     - Rename to something unique (article1.html, article2.html, etc.)
       Chrome saves them all as '606' - you must rename them
  2. Save all 9 articles

Press RETURN when all articles are downloaded and renamed:
```

**Note:** The script opens all articles automatically! Just go through each tab, save it, and rename it to something unique. The filename doesn't matter - the script identifies articles by reading the article_id from each file's content.

### Step 3: Done!
The script automatically:
- Processes all articles
- Links them locally
- Cleans up temporary folders
- Updates index.html

**No need to remember folder names or steps - just follow the prompts!**

## What It Does

- **Fixes image paths** using BeautifulSoup (handles HTML entities correctly)
- **Organizes images by month** - each month's images go to `/images/monthly/YYYY_M/`
- Copies general images to `/images` (whitebox.gif, background.jpg, etc.)
- Applies text replacements (Tony Camarra → Ikhlas Hussain, etc.)
- Removes Tony Camarra's photo, uses yours instead
- Adds header/footer templates with proper styling (header not blue/clickable)
- **Updates logo link** in monthly pages to point to that month's newsletter
- **Adds "View All Newsletters" button** in top right of monthly pages
- Saves newsletters to `monthly/YYYY_M/index.html` folders (e.g., `monthly/2026_4/index.html`)
- **Automatically opens all article links in your browser** - no manual copying URLs!
- Extracts article links and pauses for you to download them
- Processes all downloaded articles automatically
- Links articles locally in the newsletter (no external realtytimes.com links)
- Cleans up all temporary folders
- Auto-updates `/index.html` with big "Current Newsletter" button + archive list

The script preserves historical monthly images and newsletters.

**One command, fully guided, everything automated!**

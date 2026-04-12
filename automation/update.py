#!/usr/bin/env python3
"""
Simple blog automation for blog.ikhlasrealty.com
Processes manually saved HTML files from realtytimes.com
"""

import re
import shutil
import unicodedata
import urllib.parse
import webbrowser
from pathlib import Path
from bs4 import BeautifulSoup


# Configuration
WORKSPACE_DIR = Path(__file__).parent.parent
MONTHLY_DIR = WORKSPACE_DIR / "monthly"
IMAGES_DIR = WORKSPACE_DIR / "images"
MONTHLY_IMAGES_DIR = IMAGES_DIR / "monthly"
TEMPLATES_DIR = WORKSPACE_DIR / "templates"
NEWSLETTER_DOWNLOAD_DIR = WORKSPACE_DIR / "newsletter_download"
ARTICLE_DOWNLOAD_DIR = WORKSPACE_DIR / "article_downloads"

# Images that go in /images (not /images/monthly)
GENERAL_IMAGES = [
    'whitebox.gif', 'black.gif', 'blackdot.gif', 
    'background.jpg', 'ikhlashussain2.jpeg', 
    'realestateupdate.png', 'equalhousing.gif',
    'mastheadtm.gif'
]


def load_template(filename):
    """Load a template file."""
    template_path = TEMPLATES_DIR / filename
    if template_path.exists():
        return template_path.read_text(encoding='utf-8')
    return ""


def load_replacements():
    """Load replacement rules."""
    replacements = {
        'Tony Camarra': 'Ikhlas Hussain',
        'Tony CamarraREALTOR': 'Ikhlas Hussain - Realtor',
        'TonyCamarra.jpg': 'ikhlasHussain2.jpeg',
        'tonycamarra.jpg': 'ikhlasHussain2.jpeg',
        'TonyCamarra': 'ikhlasHussain2',
        'tonycamarra': 'ikhlashussain',
        'tonyc@camberrealestate.com': 'ikhlashussain@live.com',
        'http://realtytimes.com/images/nletter/tonycamarra_bkgrd.jpg': '/images/background.jpg',
        'tonycamarra_bkgrd.jpg': 'background.jpg',
        'https://realtytimes.com/index.php?option=com_nletter&view=profile&layout=contactme&format=raw&id=606': 'mailto:ikhlashussain@live.com',
        'https://realtytimes.com/index.php?option=com_nletter&amp;view=profile&amp;layout=contactme&amp;format=raw&amp;id=606': 'mailto:ikhlashussain@live.com',
        '<strong>Let me show you.</strong>': '<b>Get in contact.</b>',
        'href="/agentnews/': 'href="https://realtytimes.com/agentnews/',
        'href="/consumeradvice/': 'href="https://realtytimes.com/consumeradvice/',
    }
    
    replacements_path = TEMPLATES_DIR / "replacements.txt"
    if replacements_path.exists():
        for line in replacements_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                parts = line.split(maxsplit=1)
                if len(parts) >= 2:
                    replacements[parts[0]] = parts[1]
    
    return replacements


def slugify_title(title):
    """Convert article title into a clean URL slug."""
    if not title:
        return "article"

    normalized = unicodedata.normalize("NFKD", title)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text.lower()).strip("-")
    cleaned = re.sub(r"-+", "-", cleaned)
    return cleaned or "article"


def extract_article_title_from_html(article_html):
    """Extract a reasonable article title from processed article HTML."""
    soup = BeautifulSoup(article_html, 'html.parser')
    for tag in soup.find_all(['h1', 'h2', 'h3', 'strong']):
        text = " ".join(tag.get_text(" ", strip=True).split())
        if len(text) < 12:
            continue
        if "continued" in text.lower():
            continue
        return text
    return None


def find_latest_local_daily_news_url():
    """Return the newest local daily-news article URL, if available."""
    monthly_folders = []
    for folder in MONTHLY_DIR.iterdir():
        if folder.is_dir():
            match = re.match(r'(\d{4})_(\d+)', folder.name)
            if match:
                monthly_folders.append((int(match.group(1)), int(match.group(2)), folder))

    monthly_folders.sort(key=lambda x: (x[0], x[1]), reverse=True)

    for _, _, folder in monthly_folders:
        articles_dir = folder / "articles"
        if not articles_dir.exists():
            continue

        for article_file in sorted(articles_dir.glob("*.html")):
            stem = article_file.stem.lower()
            if stem.startswith("daily") or "daily-news" in stem or "dailynews" in stem:
                return f"/monthly/{folder.name}/articles/{article_file.name}"

    return None


def localize_article_cross_links(articles_folder, article_map, newsletter_html, folder_name):
    """Localize links inside generated article pages (especially Daily News pages)."""
    if not articles_folder.exists() or not article_map:
        return

    # Build title -> local path map from the localized newsletter HTML.
    title_to_path = {}
    newsletter_soup = BeautifulSoup(newsletter_html, 'html.parser')
    expected_prefix = f"/monthly/{folder_name}/articles/"
    for link in newsletter_soup.find_all('a', href=True):
        href = link.get('href', '').strip()
        if not href.startswith(expected_prefix):
            continue
        text = " ".join(link.get_text(" ", strip=True).split())
        if not text or "continued" in text.lower():
            continue
        title_to_path[text] = href

    for article_file in articles_folder.glob("*.html"):
        article_html = article_file.read_text(encoding='utf-8')
        soup = BeautifulSoup(article_html, 'html.parser')
        changed = False

        for link in soup.find_all('a', href=True):
            href = link.get('href', '').strip()
            if not href:
                continue

            # Primary: rewrite by article_id where available.
            matched_by_id = False
            for article_id, local_path in article_map.items():
                if f"article_id={article_id}" in href:
                    if href != local_path:
                        link['href'] = local_path
                        changed = True
                    matched_by_id = True
                    break
            if matched_by_id:
                continue

            # Fallback: rewrite external links by title match.
            text = " ".join(link.get_text(" ", strip=True).split())
            if text in title_to_path:
                if (
                    "realtytimes.com" in href
                    or href.startswith('/index.php')
                    or href.startswith('index.php')
                    or (href.startswith('/monthly/') and '/articles/' not in href)
                ):
                    if href != title_to_path[text]:
                        link['href'] = title_to_path[text]
                        changed = True

        if changed:
            article_file.write_text(str(soup), encoding='utf-8')


def process_article_file(html_file_path, output_folder, monthly_folder_name):
    """Process an article HTML file."""
    html_file = Path(html_file_path)
    if not html_file.exists():
        return None
    
    # Create monthly images subfolder
    monthly_images_folder = MONTHLY_IMAGES_DIR / monthly_folder_name
    monthly_images_folder.mkdir(parents=True, exist_ok=True)
    
    # Read HTML
    html_content = html_file.read_text(encoding='utf-8')
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find associated _files folder
    files_folder_name = html_file.stem + "_files"
    files_folder = html_file.parent / files_folder_name
    
    # Copy images and update paths
    if files_folder.exists() and files_folder.is_dir():
        for img_file in files_folder.iterdir():
            if img_file.is_file() and not img_file.name.endswith(('.js', '.html')):
                filename = img_file.name
                
                # Determine destination
                if filename.lower() in [img.lower() for img in GENERAL_IMAGES]:
                    dest = IMAGES_DIR / filename
                else:
                    dest = monthly_images_folder / filename
                
                # Copy file
                shutil.copy2(img_file, dest)
        
        # Update all img and script src attributes
        for tag in soup.find_all(['img', 'script']):
            src = tag.get('src', '')
            if src and files_folder_name in src:
                filename = src.split('/')[-1]
                filename = urllib.parse.unquote(filename)
                
                if filename.lower() in [img.lower() for img in GENERAL_IMAGES]:
                    tag['src'] = f"/images/{filename}"
                else:
                    tag['src'] = f"/images/monthly/{monthly_folder_name}/{filename}"
    
    html_content = str(soup)
    
    # Apply text replacements
    replacements = load_replacements()
    for old_text, new_text in replacements.items():
        html_content = html_content.replace(old_text, new_text)

    # Localize "Daily News and Advice" archive link to newest local daily page.
    latest_daily_url = find_latest_local_daily_news_url()
    if latest_daily_url:
        html_content = re.sub(
            r'https?://realtytimes\.com/index\.php\?option=com_nletter(?:&amp;|&)view=profile(?:&amp;|&)format=raw(?:&amp;|&)id=\d+(?:&amp;|&)layout=archives',
            latest_daily_url,
            html_content
        )
    
    # Fix internal article links (e.g., in daily news pages)
    # Pattern: /monthly/article.html -> /monthly/YYYY_M/articles/article.html
    html_content = re.sub(
        r'href="/monthly/([^/"]+\.html)"',
        f'href="/monthly/{monthly_folder_name}/articles/\\1"',
        html_content
    )
    
    # Pattern: monthly/article.html -> /monthly/YYYY_M/articles/article.html
    html_content = re.sub(
        r'href="monthly/([^/"]+\.html)"',
        f'href="/monthly/{monthly_folder_name}/articles/\\1"',
        html_content
    )
    
    # Pattern: ./monthly/article.html -> /monthly/YYYY_M/articles/article.html
    html_content = re.sub(
        r'href="\./monthly/([^/"]+\.html)"',
        f'href="/monthly/{monthly_folder_name}/articles/\\1"',
        html_content
    )

    # Pattern: /article.html -> /monthly/YYYY_M/articles/article.html
    # Skip root pages that should stay at root.
    html_content = re.sub(
        r'href="/(?!index\.html|404\.html)([^/"]+\.html)"',
        f'href="/monthly/{monthly_folder_name}/articles/\\1"',
        html_content
    )
    
    # Extract content section (articles typically have full content)
    r10_start = html_content.find('<!-- R10 C1 -->')
    footer_start = html_content.find('<!-- "Footer" Row -->')
    
    if r10_start != -1 and footer_start != -1 and r10_start < footer_start:
        tr_before_r10 = html_content.rfind('<tr>', 0, r10_start)
        if tr_before_r10 != -1:
            content_body = html_content[tr_before_r10:footer_start]
        else:
            content_body = html_content[r10_start:footer_start]
    else:
        # Use full content if markers not found
        content_body = html_content
    
    # Load templates and create final page
    header = load_template("header.html")
    footer = load_template("footer.html")
    
    # Parse monthly_folder_name to get year and month
    folder_match = re.match(r'(\d{4})_(\d+)', monthly_folder_name)
    if folder_match and header:
        year = folder_match.group(1)
        month_num = int(folder_match.group(2))
        
        # Convert month number to name
        month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December']
        month_name = month_names[month_num] if 1 <= month_num <= 12 else ''
        month_year = f"{month_name} {year}"
        
        # Update date in header
        header = re.sub(
            r'<span class="RTREUHeaderDate"[^>]*>[^<]+</span>',
            f'<span class="RTREUHeaderDate" style="color: white; cursor: default;">{month_year}</span>',
            header
        )
        
        # Update logo link to point to monthly page
        header = re.sub(
            r'<a href="/index\.html">',
            f'<a href="/monthly/{monthly_folder_name}/">',
            header
        )
        
        # Add navigation button to top right
        header = re.sub(
            r'(<td valign="top" width="165">\s*<center><br>)',
            r'\1<a href="/index.html" style="text-decoration: none;"><div style="background: #035ba5; color: white; padding: 8px 16px; border-radius: 8px; font-family: Arial; font-size: 12px; font-weight: bold; display: inline-block; cursor: pointer;">📚 View All Newsletters</div></a><br>',
            header
        )
    
    full_html = header + content_body + footer
    
    return full_html


def process_saved_file(html_file_path, process_articles=True):
    """Process a manually saved HTML file."""
    html_file = Path(html_file_path)
    if not html_file.exists():
        print(f"  ✗ File not found: {html_file_path}")
        return False
    
    print(f"  Processing: {html_file.name}")
    
    # Read HTML
    html_content = html_file.read_text(encoding='utf-8')
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract date first to determine folder name
    date_match = re.search(
        r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})',
        html_content,
        re.IGNORECASE
    )
    
    if date_match:
        year = date_match.group(2)
        month_name = date_match.group(1).lower()
        month_num = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12
        }.get(month_name, 1)
        folder_name = f"{year}_{month_num}"
    else:
        folder_name = "unknown"
    
    # Create monthly images subfolder
    monthly_images_folder = MONTHLY_IMAGES_DIR / folder_name
    monthly_images_folder.mkdir(parents=True, exist_ok=True)
    
    # Find associated _files folder
    files_folder_name = html_file.stem + "_files"
    files_folder = html_file.parent / files_folder_name
    
    # Track article links for user to download
    article_links = set()
    article_titles = {}
    daily_news_archive_url = None
    graph_image_url = None
    
    # Copy images and update paths using BeautifulSoup
    if files_folder.exists() and files_folder.is_dir():
        print(f"  Found images folder: {files_folder_name}")
        
        # Copy all image files
        for img_file in files_folder.iterdir():
            if img_file.is_file() and not img_file.name.endswith(('.js', '.html')):
                filename = img_file.name
                
                # Determine destination
                if filename.lower() in [img.lower() for img in GENERAL_IMAGES]:
                    dest = IMAGES_DIR / filename
                else:
                    dest = monthly_images_folder / filename
                
                # Copy file
                shutil.copy2(img_file, dest)
        
        # Update all img and script src attributes
        for tag in soup.find_all(['img', 'script']):
            src = tag.get('src', '')
            if src and files_folder_name in src:
                # Extract just the filename
                filename = src.split('/')[-1]
                # Decode URL encoding
                filename = urllib.parse.unquote(filename)
                
                # Determine new path
                if filename.lower() in [img.lower() for img in GENERAL_IMAGES]:
                    tag['src'] = f"/images/{filename}"
                else:
                    tag['src'] = f"/images/monthly/{folder_name}/{filename}"

    # Capture externally-referenced dynamic graph image URLs for manual download.
    for img_tag in soup.find_all('img'):
        src = img_tag.get('src', '')
        if 'graph/graph.php' in src or 'newgrap.php' in src:
            graph_image_url = src  # Will be opened in browser for manual save

    # Extract article links to download manually
    for link in soup.find_all('a', href=True):
        href = link['href']
        if 'realtytimes.com' in href and 'article_id=' in href:
            article_links.add(href)
            article_id_match = re.search(r'article_id=(\d+)', href)
            if article_id_match:
                article_id = article_id_match.group(1)
                link_text = " ".join(link.get_text(" ", strip=True).split())
                if link_text and "continued" not in link_text.lower():
                    article_titles[article_id] = link_text

        # Capture RealtyTimes daily-news archive link so it can be localized.
        if 'realtytimes.com/index.php' in href and 'layout=archives' in href:
            daily_news_archive_url = href
    
    # Convert soup back to string for text replacements
    html_content = str(soup)
    
    # Apply text replacements
    replacements = load_replacements()
    for old_text, new_text in replacements.items():
        html_content = html_content.replace(old_text, new_text)
    
    # Extract content section (between R10 C1 and Footer)
    r10_start = html_content.find('<!-- R10 C1 -->')
    footer_start = html_content.find('<!-- "Footer" Row -->')
    
    if r10_start != -1 and footer_start != -1 and r10_start < footer_start:
        tr_before_r10 = html_content.rfind('<tr>', 0, r10_start)
        if tr_before_r10 != -1:
            content_body = html_content[tr_before_r10:footer_start]
        else:
            content_body = html_content[r10_start:footer_start]
    else:
        # Fallback: try to find content row
        soup = BeautifulSoup(html_content, 'html.parser')
        content_body = ""
        for element in soup.descendants:
            if element.name == 'tr':
                element_str = str(element)[:200]
                if 'R10 C1' in element_str:
                    content_body = str(element)
                    break
    
    if not content_body:
        print(f"  ✗ Could not extract content")
        return False
    
    # Load templates and create final page
    header = load_template("header.html")
    footer = load_template("footer.html")
    
    # Extract month/year from content and update header
    date_match = re.search(
        r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})',
        html_content,
        re.IGNORECASE
    )
    
    if date_match and header:
        month_year = f"{date_match.group(1)} {date_match.group(2)}"
        year = date_match.group(2)
        month_name = date_match.group(1).lower()
        month_num = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12
        }.get(month_name, 1)
        folder_name_for_link = f"{year}_{month_num}"
        
        # Replace the date in the header template (handle both with and without style attribute)
        header = re.sub(
            r'<span class="RTREUHeaderDate"[^>]*>[^<]+</span>',
            f'<span class="RTREUHeaderDate" style="color: white; cursor: default;">{month_year}</span>',
            header
        )
        
        # Update logo link to point to this month's page
        header = re.sub(
            r'<a href="/index\.html">',
            f'<a href="/monthly/{folder_name_for_link}/">',
            header
        )
        
        # Add navigation button to top right (replace the empty space)
        header = re.sub(
            r'(<td valign="top" width="165">\s*<center><br>)',
            r'\1<a href="/index.html" style="text-decoration: none;"><div style="background: #035ba5; color: white; padding: 8px 16px; border-radius: 8px; font-family: Arial; font-size: 12px; font-weight: bold; display: inline-block; cursor: pointer;">📚 View All Newsletters</div></a><br>',
            header
        )
    
    full_html = header + content_body + footer
    
    # Generate folder name and save as index.html inside
    if date_match:
        month_name = date_match.group(1)
        year = date_match.group(2)
        # Convert month name to number
        month_num = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12
        }.get(month_name.lower(), 1)
        
        folder_name = f"{year}_{month_num}"
    else:
        folder_name = "unknown"
    
    # Create folder
    output_folder = MONTHLY_DIR / folder_name
    output_folder.mkdir(exist_ok=True)
    
    # Save newsletter (will update later with article links)
    output_path = output_folder / "index.html"
    output_path.write_text(full_html, encoding='utf-8')
    
    print(f"  ✓ Saved: {folder_name}/index.html")
    
    # Return newsletter data for article processing
    return {
        'folder_name': folder_name,
        'output_folder': output_folder,
        'article_links': article_links,
        'article_titles': article_titles,
        'daily_news_archive_url': daily_news_archive_url,
        'graph_image_url': graph_image_url,
        'content_body': content_body,
        'full_html': full_html
    }


def main():
    print("\n" + "=" * 70)
    print("Blog Automation for blog.ikhlasrealty.com")
    print("=" * 70 + "\n")
    
    # Create directories
    MONTHLY_DIR.mkdir(exist_ok=True)
    IMAGES_DIR.mkdir(exist_ok=True)
    MONTHLY_IMAGES_DIR.mkdir(exist_ok=True)
    
    # Step 1: Wait for user to download the newsletter
    print("=" * 70)
    print("Step 1: Download the Main Newsletter")
    print("=" * 70)
    
    # Create newsletter download folder
    NEWSLETTER_DOWNLOAD_DIR.mkdir(exist_ok=True)
    
    print(f"\n📥 Ready to download the newsletter!\n")
    print("Instructions:")
    print("  1. Open https://realtytimes.com/cm/tonycamarra in your browser")
    print("  2. Solve CAPTCHA if needed")
    print("  3. File → Save As → 'Webpage, Complete'")
    print(f"  4. Save it to the '{NEWSLETTER_DOWNLOAD_DIR.name}/' folder\n")
    
    input("Press RETURN when newsletter is downloaded: ")
    
    # Step 2: Look for the newsletter file
    print("\n" + "=" * 70)
    print("Step 2: Processing newsletter...")
    print("=" * 70 + "\n")
    
    html_files = list(NEWSLETTER_DOWNLOAD_DIR.glob("*.html"))
    
    if not html_files:
        print("\n" + "=" * 70)
        print("❌ No HTML files found in newsletter_download/ directory")
        print("=" * 70)
        print("\nPlease make sure you saved the page as 'Webpage, Complete'")
        print("and try again.\n")
        # Clean up
        NEWSLETTER_DOWNLOAD_DIR.rmdir()
        return
    
    
    # Process the newsletter
    newsletter_data = None
    for html_file in html_files:
        result = process_saved_file(html_file, process_articles=False)
        if result:
            newsletter_data = result
            break
    
    if not newsletter_data:
        print("  ✗ Failed to process newsletter")
        # Clean up
        for file in NEWSLETTER_DOWNLOAD_DIR.iterdir():
            if file.is_file():
                file.unlink()
            elif file.is_dir():
                shutil.rmtree(file)
        NEWSLETTER_DOWNLOAD_DIR.rmdir()
        return
    
    # Step 3: Handle article downloads
    article_links = newsletter_data.get('article_links', set())
    daily_news_archive_url = newsletter_data.get('daily_news_archive_url')
    graph_image_url = newsletter_data.get('graph_image_url')

    download_targets = sorted(article_links)
    if daily_news_archive_url and daily_news_archive_url not in download_targets:
        download_targets.append(daily_news_archive_url)

    if download_targets:
        print("\n" + "=" * 70)
        print(f"Found {len(download_targets)} links to download!")
        print("=" * 70)
        print("\n" + "=" * 70)
        print("Step 3: Download the Articles")
        print("=" * 70)
        
        # Create article download folder
        ARTICLE_DOWNLOAD_DIR.mkdir(exist_ok=True)
        
        # Save article links
        links_file = ARTICLE_DOWNLOAD_DIR / "article_links.txt"
        links_file.write_text('\n'.join(download_targets), encoding='utf-8')

        print(f"\n📥 Opening {len(download_targets)} links in your browser...\n")
        
        # Open each article in browser
        import time
        for i, link in enumerate(download_targets, 1):
            print(f"  Opening link {i}/{len(download_targets)}...")
            webbrowser.open(link)
            time.sleep(0.5)  # Small delay to avoid overwhelming the browser
        
        print(f"\n✓ All links opened in browser!")
        print(f"  Article links also saved to: {ARTICLE_DOWNLOAD_DIR.name}/article_links.txt\n")
        print("Instructions:")
        print(f"  1. For each article/daily-news browser tab:")
        print("     - File → Save As → 'Webpage, Complete'")
        print(f"     - Save to '{ARTICLE_DOWNLOAD_DIR.name}/' folder")
        print("     - Rename to something unique (article1.html, article2.html, etc.)")
        print("       Chrome saves them all as '606' - you must rename them")
        if graph_image_url:
            print(f"  2. For the market graph (chart) on the NEWSLETTER tab still open in your browser:")
            print(f"     - Go back to the realtytimes.com/cm/tonycamarra tab")
            print(f"     - Right-click the chart image → Save Image As...")
            print(f"     - Save as 'market-graph.png' in '{ARTICLE_DOWNLOAD_DIR.name}/'")
        print(f"  {'3' if graph_image_url else '2'}. Save all pages/images\n")
        
        input("Press RETURN when all articles are downloaded and renamed: ")
        
        # Step 4: Process articles
        print("\n" + "=" * 70)
        print("Step 4: Processing articles...")
        print("=" * 70 + "\n")
        
        articles_folder = newsletter_data['output_folder'] / "articles"
        articles_folder.mkdir(exist_ok=True)
        
        article_titles = newsletter_data.get('article_titles', {})
        article_map = {}  # Maps article_id to local path
        daily_news_local_path = None
        used_slugs = set()

        # Pick up manually saved graph image (market-graph.*)
        folder_name = newsletter_data['folder_name']
        monthly_images_folder = MONTHLY_IMAGES_DIR / folder_name
        monthly_images_folder.mkdir(parents=True, exist_ok=True)
        graph_local_url = None
        for graph_file in ARTICLE_DOWNLOAD_DIR.glob('market-graph.*'):
            dest = monthly_images_folder / graph_file.name
            shutil.copy2(graph_file, dest)
            graph_local_url = f'/images/monthly/{folder_name}/{graph_file.name}'
            print(f'  ✓ Saved graph image -> images/monthly/{folder_name}/{graph_file.name}')

        article_files = list(ARTICLE_DOWNLOAD_DIR.glob("*.html"))
        
        if article_files:
            for article_file in article_files:
                # Try to match article by reading URL from file
                file_content = article_file.read_text(encoding='utf-8')
                file_content_l = file_content.lower()

                # Daily News archive page can include article_id values from featured stories.
                # Detect and process it first so it doesn't get treated as a normal article.
                is_daily_news_file = (
                    'daily news and advice' in file_content_l
                    or "today's feature stories" in file_content_l
                )

                if is_daily_news_file:
                    article_html = process_article_file(article_file, newsletter_data['output_folder'], newsletter_data['folder_name'])
                    if article_html:
                        slug_base = 'daily-news-and-advice'
                        slug = slug_base
                        suffix = 2
                        while slug in used_slugs:
                            slug = f"{slug_base}-{suffix}"
                            suffix += 1
                        used_slugs.add(slug)

                        article_filename = f"{slug}.html"
                        article_path = articles_folder / article_filename
                        article_path.write_text(article_html, encoding='utf-8')
                        daily_news_local_path = f"/monthly/{newsletter_data['folder_name']}/articles/{article_filename}"
                        print(f"  ✓ Processed daily news -> {article_filename}")
                    continue

                article_id_match = re.search(r'article_id=(\d+)', file_content)
                
                if article_id_match:
                    article_id = article_id_match.group(1)
                    
                    # Check if this article is referenced in the newsletter
                    if any(f'article_id={article_id}' in link for link in article_links):
                        # Process the article
                        article_html = process_article_file(article_file, newsletter_data['output_folder'], newsletter_data['folder_name'])
                        if article_html:
                            title_for_slug = article_titles.get(article_id)
                            if not title_for_slug:
                                title_for_slug = extract_article_title_from_html(article_html)

                            slug_base = slugify_title(title_for_slug or f"article-{article_id}")
                            slug = slug_base
                            suffix = 2
                            while slug in used_slugs:
                                slug = f"{slug_base}-{suffix}"
                                suffix += 1
                            used_slugs.add(slug)

                            article_filename = f"{slug}.html"
                            article_path = articles_folder / article_filename
                            article_path.write_text(article_html, encoding='utf-8')
                            article_map[article_id] = f"/monthly/{newsletter_data['folder_name']}/articles/{article_filename}"
                            print(f"  ✓ Processed article {article_id} -> {article_filename}")
            
            # Step 5: Update newsletter with local article links
            if article_map or daily_news_local_path:
                print("\nStep 5: Updating newsletter with local article links...")
                full_html = newsletter_data['full_html']
                
                for article_id, local_path in article_map.items():
                    # Replace various URL formats
                    full_html = re.sub(
                        rf'https?://realtytimes\.com[^"]*article_id={article_id}[^"]*',
                        local_path,
                        full_html
                    )

                # Re-localize daily archive link after article replacements.
                latest_daily_url = daily_news_local_path or find_latest_local_daily_news_url()
                if latest_daily_url:
                    full_html = re.sub(
                        r'https?://realtytimes\.com/index\.php\?option=com_nletter(?:&amp;|&)view=profile(?:&amp;|&)format=raw(?:&amp;|&)id=\d+(?:&amp;|&)layout=archives',
                        latest_daily_url,
                        full_html
                    )

                # Localize graph image in newsletter and all article files.
                if graph_local_url:
                    full_html = re.sub(
                        r'https?://realtytimes\.com/graph/[^"\']+',
                        graph_local_url,
                        full_html
                    )
                    full_html = re.sub(
                        r'/images/monthly/\d{4}_\d+/(?:newgrap|graph)\.php',
                        graph_local_url,
                        full_html
                    )
                    for article_file in articles_folder.glob('*.html'):
                        art = article_file.read_text(encoding='utf-8')
                        patched = re.sub(
                            r'https?://realtytimes\.com/graph/[^"\']+',
                            graph_local_url,
                            art
                        )
                        patched = re.sub(
                            r'/images/monthly/\d{4}_\d+/(?:newgrap|graph)\.php',
                            graph_local_url,
                            patched
                        )
                        if patched != art:
                            article_file.write_text(patched, encoding='utf-8')
                    print(f'  \u2713 Localized graph image in newsletter and articles')

                # Localize links inside generated article pages (e.g., Daily News story links).
                localize_article_cross_links(
                    articles_folder=articles_folder,
                    article_map=article_map,
                    newsletter_html=full_html,
                    folder_name=newsletter_data['folder_name']
                )
                
                # Save updated newsletter
                output_path = newsletter_data['output_folder'] / "index.html"
                output_path.write_text(full_html, encoding='utf-8')
                print(f"  ✓ Updated newsletter with {len(article_map)} local article links")
        else:
            print("  ⚠ No article files found in article_downloads/")
        
        # Step 6: Clean up
        print("\nStep 6: Cleaning up...")
        # Delete article files from download folder
        for file in ARTICLE_DOWNLOAD_DIR.iterdir():
            if file.is_file():
                file.unlink()
            elif file.is_dir():
                shutil.rmtree(file)
        ARTICLE_DOWNLOAD_DIR.rmdir()
        print("  ✓ Cleaned up article_downloads/")
    
    # Clean up newsletter download folder
    for file in NEWSLETTER_DOWNLOAD_DIR.iterdir():
        if file.is_file():
            file.unlink()
        elif file.is_dir():
            shutil.rmtree(file)
    NEWSLETTER_DOWNLOAD_DIR.rmdir()
    print("  ✓ Cleaned up newsletter_download/")
    
    # Summary
    print("\n" + "=" * 70)
    print("✓ Complete!")
    print("=" * 70)
    
    # Step 7: Update index.html with links to all monthly pages
    print("\nStep 7: Updating index.html...")
    update_index()
    
    print(f"\nFiles saved to: {MONTHLY_DIR}")
    print(f"Images organized by month in: {MONTHLY_IMAGES_DIR}")
    print("\nNext steps:")
    print("  1. Review the files in monthly/")
    print("  2. Use GitHub Desktop to commit and push")
    print("")


def update_index():
    """Update index.html to list all monthly newsletters."""
    # Get all monthly folders sorted by date (newest first)
    monthly_folders = []
    for folder in MONTHLY_DIR.iterdir():
        if folder.is_dir():
            match = re.match(r'(\d{4})_(\d+)', folder.name)
            if match:
                year = int(match.group(1))
                month = int(match.group(2))
                monthly_folders.append((year, month, folder))
    
    if not monthly_folders:
        return
    
    # Sort by year and month (newest first)
    monthly_folders.sort(key=lambda x: (x[0], x[1]), reverse=True)
    
    # Month names
    month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November', 'December']
    
    # Create content section with big current newsletter button
    content = '<tr><td width="752"><center><br><br>\n'
    
    # Current newsletter button (most recent)
    if monthly_folders:
        current_year, current_month, current_folder = monthly_folders[0]
        current_name = f"{month_names[current_month]} {current_year}"
        
        content += '<a href="/monthly/' + current_folder.name + '/" style="text-decoration: none;">\n'
        content += '<div style="background: linear-gradient(135deg, #035ba5 0%, #72b3f2 100%); '
        content += 'color: white; padding: 30px 60px; border-radius: 15px; '
        content += 'font-family: Arial, Helvetica; font-size: 28px; font-weight: bold; '
        content += 'box-shadow: 0 4px 15px rgba(3,91,165,0.3); '
        content += 'display: inline-block; margin: 20px; '
        content += 'transition: transform 0.2s, box-shadow 0.2s;">\n'
        content += f'📰 Current Newsletter - {current_name}\n'
        content += '</div>\n'
        content += '</a>\n'
        content += '<br><br>\n'
    
    # Archive section
    if len(monthly_folders) > 1:
        content += '<h2 style="font-family: Arial, Helvetica; color: #035ba5; margin-top: 40px;">Newsletter Archive</h2>\n'
        content += '<br>\n'
        content += '<table border="0" cellspacing="10" cellpadding="10" width="600">\n'
        
        for year, month, folder in monthly_folders[1:]:
            display_name = f"{month_names[month]} {year}"
            
            content += '<tr>\n'
            content += f'  <td style="font-family: Arial, Helvetica; font-size: 16px;">\n'
            content += f'    <a href="/monthly/{folder.name}/" style="text-decoration: none; color: #035ba5; font-weight: bold;">\n'
            content += f'      📄 {display_name}\n'
            content += f'    </a>\n'
            content += f'  </td>\n'
            content += '</tr>\n'
        
        content += '</table>\n'
    
    content += '<br><br></center></td></tr>\n'
    
    # Load templates
    header = load_template("header.html")
    footer = load_template("footer.html")
    
    # Update header to say "Newsletter Archive" and ensure it's not styled as a link
    header = re.sub(
        r'<span class="RTREUHeaderDate"[^>]*>[^<]+</span>',
        '<span class="RTREUHeaderDate" style="color: white; cursor: default;">Newsletter Archive</span>',
        header
    )
    
    # Create full index page
    index_html = header + content + footer
    
    # Save index.html
    index_path = WORKSPACE_DIR / "index.html"
    index_path.write_text(index_html, encoding='utf-8')
    print(f"  ✓ Updated index.html with {len(monthly_folders)} newsletters")


if __name__ == "__main__":
    main()

# blog.ikhlasrealty.com

Official monthly real estate newsletter for Ikhlas Hussain, Realtor at Camber Real Estate Inc.

## Monthly Update Process

1. Run `bash update.command` (or double-click `update.command`).
2. Follow the prompts to:
	- Save the main newsletter page into `newsletter_download/`
	- Save the opened article pages into `article_downloads/`
3. The script automatically:
	- Processes the newsletter and articles
	- Localizes images and rewrites links
	- Builds `monthly/YYYY_M/index.html` and `monthly/YYYY_M/articles/`
	- Updates root `index.html` archive links
	- Cleans temporary download folders
4. Review changes and push with GitHub Desktop.

## Notes

- The workflow is month-by-month for future updates.
- First run will create and use `automation/.venv` automatically.

## Site Structure

- `monthly/` newsletter folders by month
- `images/` general and monthly image assets
- `templates/` header/footer/replacements
- `automation/` monthly automation scripts

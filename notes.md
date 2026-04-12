# Blog Notes

Source: https://realtytimes.com/cm/tonycamarra

## Monthly Update Workflow

1. Run `bash update.command`.
2. Follow prompts to save the main newsletter into `newsletter_download/`.
3. Save opened article pages into `article_downloads/` as prompted.
4. Review generated files in `monthly/YYYY_M/`.
5. Commit and push with GitHub Desktop.

## LLM Prompt: Monthly "What's New" Summary

Use this prompt each month (paste newsletter front-page content where requested):

```text
You are writing the monthly "What’s New" post for Ikhlas Hussain’s blog.

I will paste raw front-page HTML/text from this month’s newsletter page.

Your job:
1. Extract the month and year.
2. Extract all main article titles for this month.
3. Exclude navigation, "continued", footer/contact text, and duplicate links.
4. Include Daily News and Advice only if it appears as a featured item for the month.
5. Build each article URL using this format:
https://blog.ikhlasrealty.com/monthly/YYYY_M/articles/ARTICLE-SLUG.html
Where:
- YYYY_M is like 2026_4
- ARTICLE-SLUG is lowercase, hyphenated, punctuation removed
6. Write a polished summary in the exact style below.

Output format:
# MONTH YEAR - Ikhlas Hussain’s Blog!

[Blog.IkhlasRealty.com](https://blog.ikhlasrealty.com/) is thrilled to present this month’s batch of insightful articles designed to guide you through the complexities of real estate.

## New Articles This Month:

- [Article Title](Article URL)
  - 1-2 sentence plain-English summary of what readers will learn.

(Repeat for each article)

## Wrap-up
We’re just getting started! Ikhlas Realty is committed to continuous improvement and innovation. We value your feedback and invite you to share your thoughts on these changes and your wishlist for future updates.

Thank you for continuing to include Ikhlas Realty as your go-to source for all things real estate!

Rules:
- Keep tone professional, friendly, and concise.
- Do not invent articles not present in pasted content.
- If a URL slug is ambiguous, choose the most natural slug and keep format consistent.
- Return only the final markdown output, no extra notes.
```

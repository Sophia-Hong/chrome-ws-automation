#!/usr/bin/env python3
"""
Reddit Pain Point Scraper Pipeline.
Uses chrome-ws-automation to monitor subreddits and extract user pain points.

Usage:
    python -m pipelines.reddit_scraper --subreddit tenants --keywords "security deposit,landlord"
    python -m pipelines.reddit_scraper --subreddit legaladvice --keywords "tenant rights" --output results.json
"""

import asyncio
import json
import sys
import os
import re
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))
from client import send_command


async def navigate_and_wait(url: str, delay: float = 2.0):
    """Navigate and wait for page load."""
    await send_command("navigate", {"url": url})
    await asyncio.sleep(delay)


async def get_subreddit_posts(subreddit: str, sort: str = "new", limit: int = 25) -> list[dict]:
    """Scrape posts from a subreddit."""
    url = f"https://www.reddit.com/r/{subreddit}/{sort}/"
    await navigate_and_wait(url, 3.0)
    
    # Get snapshot for context
    snapshot = await send_command("snapshot", {})
    
    # Get all post links
    links_data = await send_command("getLinks", {"filter": f"/r/{subreddit}/comments/"})
    links = links_data.get("result", {}).get("links", [])
    
    posts = []
    seen = set()
    for link in links[:limit]:
        href = link.get("href", "")
        text = link.get("text", "").strip()
        if href in seen or not text or len(text) < 10:
            continue
        seen.add(href)
        posts.append({
            "title": text,
            "url": href,
            "subreddit": subreddit,
        })
    
    return posts


async def extract_post_content(url: str) -> dict:
    """Navigate to a post and extract its content + comments."""
    await navigate_and_wait(url, 3.0)
    
    snapshot = await send_command("snapshot", {})
    result = snapshot.get("result", {})
    
    # Get the post text
    text_data = await send_command("getText", {})
    full_text = text_data.get("result", {}).get("text", "")
    
    return {
        "url": url,
        "title": result.get("title", ""),
        "text": full_text[:20000],
        "scraped_at": datetime.now().isoformat(),
    }


def extract_pain_points(text: str, keywords: list[str]) -> list[dict]:
    """Extract sentences mentioning pain-point keywords."""
    sentences = re.split(r'[.!?\n]+', text)
    pain_points = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 20 or len(sentence) > 500:
            continue
        for kw in keywords:
            if kw.lower() in sentence.lower():
                pain_points.append({
                    "text": sentence,
                    "keyword": kw,
                })
                break
    
    return pain_points


async def run_pipeline(
    subreddit: str,
    keywords: list[str],
    max_posts: int = 10,
    output_file: Optional[str] = None,
) -> dict:
    """Full pipeline: scrape subreddit → extract pain points."""
    print(f"[reddit] Scraping r/{subreddit} for keywords: {keywords}")
    
    posts = await get_subreddit_posts(subreddit, limit=max_posts)
    print(f"[reddit] Found {len(posts)} posts")
    
    all_pain_points = []
    
    for i, post in enumerate(posts):
        print(f"[reddit] ({i+1}/{len(posts)}) {post['title'][:60]}...")
        try:
            content = await extract_post_content(post["url"])
            points = extract_pain_points(content["text"], keywords)
            if points:
                all_pain_points.append({
                    "post": post,
                    "pain_points": points,
                })
                print(f"  → {len(points)} pain points found")
        except Exception as e:
            print(f"  → Error: {e}")
        await asyncio.sleep(1)  # Rate limiting
    
    result = {
        "subreddit": subreddit,
        "keywords": keywords,
        "total_posts_scraped": len(posts),
        "posts_with_pain_points": len(all_pain_points),
        "total_pain_points": sum(len(p["pain_points"]) for p in all_pain_points),
        "data": all_pain_points,
        "scraped_at": datetime.now().isoformat(),
    }
    
    if output_file:
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"[reddit] Results saved to {output_file}")
    
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Reddit Pain Point Scraper")
    parser.add_argument("--subreddit", "-s", required=True)
    parser.add_argument("--keywords", "-k", required=True, help="Comma-separated keywords")
    parser.add_argument("--max-posts", "-n", type=int, default=10)
    parser.add_argument("--output", "-o", default=None)
    args = parser.parse_args()
    
    keywords = [k.strip() for k in args.keywords.split(",")]
    result = asyncio.run(run_pipeline(args.subreddit, keywords, args.max_posts, args.output))
    
    print(f"\n{'='*50}")
    print(f"Subreddit: r/{result['subreddit']}")
    print(f"Posts scraped: {result['total_posts_scraped']}")
    print(f"Posts with pain points: {result['posts_with_pain_points']}")
    print(f"Total pain points: {result['total_pain_points']}")
    
    for item in result["data"]:
        print(f"\n--- {item['post']['title'][:80]} ---")
        for pp in item["pain_points"]:
            print(f"  [{pp['keyword']}] {pp['text'][:120]}")


if __name__ == "__main__":
    main()

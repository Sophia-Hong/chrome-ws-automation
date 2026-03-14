#!/usr/bin/env python3
"""
Content Pipeline — transforms scraped pain points into content assets.

Usage:
    python -m pipelines.content_pipeline --input results.json --type comment-drafts
    python -m pipelines.content_pipeline --input results.json --type video-scripts
"""

import json
import sys
from typing import Optional


def load_pain_points(input_file: str) -> dict:
    with open(input_file) as f:
        return json.load(f)


def generate_comment_drafts(data: dict) -> list[dict]:
    """Generate comment draft templates for each pain point."""
    drafts = []
    for item in data.get("data", []):
        post = item["post"]
        for pp in item["pain_points"]:
            draft = {
                "post_title": post["title"],
                "post_url": post["url"],
                "pain_point": pp["text"],
                "keyword": pp["keyword"],
                "draft_template": (
                    f"I've seen this issue come up a lot. "
                    f"Regarding '{pp['keyword']}' — here's what typically helps:\n\n"
                    f"1. [Specific advice based on pain point]\n"
                    f"2. [Resource or tool recommendation]\n"
                    f"3. [Common mistake to avoid]\n\n"
                    f"Happy to share more details if needed."
                ),
            }
            drafts.append(draft)
    return drafts


def generate_video_outlines(data: dict) -> list[dict]:
    """Group pain points into video script outlines."""
    # Group by keyword
    by_keyword = {}
    for item in data.get("data", []):
        for pp in item["pain_points"]:
            kw = pp["keyword"]
            if kw not in by_keyword:
                by_keyword[kw] = []
            by_keyword[kw].append({
                "text": pp["text"],
                "post": item["post"]["title"],
            })
    
    outlines = []
    for kw, points in by_keyword.items():
        outline = {
            "topic": kw,
            "pain_point_count": len(points),
            "outline": {
                "hook": f"'{kw}' — {len(points)} real stories from Reddit",
                "problem": [p["text"][:100] for p in points[:3]],
                "solution": "[Your expertise / product value prop]",
                "cta": "[Call to action]",
            },
            "source_posts": [p["post"] for p in points],
        }
        outlines.append(outline)
    return outlines


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", required=True)
    parser.add_argument("--type", "-t", choices=["comment-drafts", "video-scripts"], required=True)
    parser.add_argument("--output", "-o", default=None)
    args = parser.parse_args()
    
    data = load_pain_points(args.input)
    
    if args.type == "comment-drafts":
        result = generate_comment_drafts(data)
    else:
        result = generate_video_outlines(data)
    
    output = json.dumps(result, indent=2, ensure_ascii=False)
    
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Saved to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()

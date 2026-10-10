import os
import re
import glob
from typing import Dict, Any, List, Optional
import markdown

BLOG_DIR = os.path.join(os.path.dirname(__file__), "blog_posts")

def parse_post_file(filepath: str) -> Optional[Dict[str, Any]]:
    """Parses a markdown post with frontmatter into a structured dictionary."""
    if not os.path.exists(filepath):
        return None

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract frontmatter between ---
        frontmatter = {}
        body = content
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                raw_fm = parts[1].strip()
                body = parts[2].strip()

                for line in raw_fm.split("\n"):
                    if ":" in line:
                        key, val = line.split(":", 1)
                        key = key.strip()
                        val = val.strip().strip('"').strip("'")
                        frontmatter[key] = val

        # Convert markdown body to clean HTML
        html_body = markdown.markdown(
            body,
            extensions=["extra", "nl2br", "sane_lists"]
        )

        slug = frontmatter.get("slug") or os.path.splitext(os.path.basename(filepath))[0]

        return {
            "slug": slug,
            "title": frontmatter.get("title", "Untitled Article"),
            "title_bn": frontmatter.get("title_bn", ""),
            "category": frontmatter.get("category", "General"),
            "author": frontmatter.get("author", "Sai Digital Editorial"),
            "date": frontmatter.get("date", "2025"),
            "read_time": frontmatter.get("read_time", "5 min read"),
            "image": frontmatter.get("image", "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?auto=format&fit=crop&w=1200&q=80"),
            "excerpt": frontmatter.get("excerpt", ""),
            "keywords": frontmatter.get("keywords", ""),
            "content_html": html_body,
        }
    except Exception as e:
        print(f"Error reading blog post {filepath}: {e}")
        return None

def get_all_posts(category: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns all posts sorted by date, with optional category and search filters."""
    posts = []
    files = glob.glob(os.path.join(BLOG_DIR, "*.md"))
    for f in files:
        p = parse_post_file(f)
        if p:
            posts.append(p)

    # Filter by category
    if category and category.lower() != "all":
        posts = [p for p in posts if p.get("category", "").lower() == category.lower()]

    # Filter by search keyword
    if search:
        s = search.lower().strip()
        posts = [
            p for p in posts
            if s in p.get("title", "").lower()
            or s in p.get("title_bn", "").lower()
            or s in p.get("excerpt", "").lower()
            or s in p.get("category", "").lower()
        ]

    return posts

def get_post_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single blog post by its URL slug."""
    filepath = os.path.join(BLOG_DIR, f"{slug}.md")
    if os.path.exists(filepath):
        return parse_post_file(filepath)

    # Search through files if slug differs from filename
    for p in get_all_posts():
        if p["slug"] == slug:
            return p
    return None

def get_categories() -> List[str]:
    """Returns a list of unique categories."""
    cats = set()
    for p in get_all_posts():
        if p.get("category"):
            cats.add(p["category"])
    return sorted(list(cats))

def get_related_posts(current_slug: str, category: str, limit: int = 3) -> List[Dict[str, Any]]:
    """Finds related posts in the same category or general posts excluding current."""
    all_p = get_all_posts()
    related = [p for p in all_p if p["slug"] != current_slug and p.get("category") == category]
    if len(related) < limit:
        others = [p for p in all_p if p["slug"] != current_slug and p not in related]
        related.extend(others)
    return related[:limit]

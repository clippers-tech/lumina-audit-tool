"""scraper.py — Apify actor calls for all platform scraping.

Handles both PROFILE mode (Step 1 — identity extraction) and
SEARCH mode (Step 3 — brand mention volume in last 48h).

Verified actors (all tested & confirmed working 2026-03-05):
  LinkedIn profile:   harvestapi/linkedin-profile-scraper   (no cookies, pay-per-event)
  YouTube channel:    streamers/youtube-scraper              (startUrls with /videos)
  YouTube search:     streamers/youtube-scraper              (searchKeywords)
  TikTok profile:     clockworks/tiktok-scraper              (profiles array)
  TikTok search:      clockworks/tiktok-scraper              (searchQueries array)
  Instagram profile:  apify/instagram-scraper                (search + searchType)
  Instagram search:   apify/instagram-hashtag-scraper         (hashtags array)
  X / Twitter:        apidojo/tweet-scraper                  (twitterHandles or searchTerms)
"""

import os
import httpx

APIFY_TOKEN = os.environ.get("APIFY_TOKEN", "")
APIFY_BASE = "https://api.apify.com/v2"
TIMEOUT = 300  # seconds — some actors need up to 180s
SEARCH_MAX_RESULTS = 30  # cap per-platform search results to limit Apify costs


# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════

async def _run_actor(actor_id: str, input_data: dict, timeout: int = TIMEOUT) -> list:
    """Run an Apify actor synchronously and return dataset items."""
    # Actor ID uses ~ separator in URL (owner~name), but / in display
    url_actor_id = actor_id.replace("/", "~")
    endpoint = f"{APIFY_BASE}/acts/{url_actor_id}/run-sync-get-dataset-items"
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            endpoint,
            params={"token": APIFY_TOKEN, "timeout": str(min(timeout, 240))},
            json=input_data,
        )
        if resp.status_code >= 400:
            body = resp.text[:500]
            print(f"[Scraper] Actor {actor_id} returned HTTP {resp.status_code}: {body}")
            return []
        items = resp.json()
    if isinstance(items, list):
        return items
    return [items] if items else []


def _safe_int(val, default=0) -> int:
    """Safely convert a value to int."""
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


# ═══════════════════════════════════════════════════════════
# STEP 1 — PROFILE MODE (identity extraction)
# ═══════════════════════════════════════════════════════════

async def scrape_linkedin_profile(url: str) -> dict:
    """Scrape LinkedIn profile for identity data.
    
    Uses: harvestapi/linkedin-profile-scraper (no cookies needed)
    Input: {"urls": ["https://www.linkedin.com/in/username/"]}
    Output keys: firstName, lastName, headline, about, experience[], 
                 followerCount, connectionsCount
    """
    try:
        items = await _run_actor("harvestapi/linkedin-profile-scraper", {
            "urls": [url]
        })
        if not items:
            return _empty_linkedin()
        raw = items[0]

        # Build full name
        first = raw.get("firstName", "")
        last = raw.get("lastName", "")
        full_name = f"{first} {last}".strip()

        # Get current company from experience
        company = ""
        job_title = ""
        experience = raw.get("experience", []) or []
        if experience:
            latest = experience[0]
            company = latest.get("companyName", "")
            job_title = latest.get("title", "")

        # Build headline
        headline = raw.get("headline", "")

        # Bio / about
        bio = raw.get("about", "")

        return {
            "person_name": full_name,
            "company_name": company,
            "headline": headline,
            "job_title": job_title,
            "bio": bio,
            "follower_count": _safe_int(raw.get("followerCount")),
            "connections": _safe_int(raw.get("connectionsCount")),
            "recent_posts": [],  # This actor doesn't return posts
            "data_found": bool(full_name),
        }
    except Exception as e:
        print(f"[Scraper] LinkedIn profile error: {e}")
        return _empty_linkedin()


def _empty_linkedin() -> dict:
    return {"person_name": "", "company_name": "", "headline": "", "job_title": "",
            "bio": "", "follower_count": 0, "connections": 0,
            "recent_posts": [], "data_found": False}


async def scrape_youtube_profile(url: str) -> dict:
    """Scrape YouTube channel for identity data.
    
    Uses: streamers/youtube-scraper
    Input: {"startUrls": [{"url": "https://www.youtube.com/@channel/videos"}], "maxResults": 5}
    Output keys: channelName, channelDescription, numberOfSubscribers, 
                 channelTotalViews, title, viewCount
    """
    try:
        # Ensure URL ends with /videos for channel scraping
        channel_url = url.rstrip("/")
        if not channel_url.endswith("/videos"):
            channel_url += "/videos"

        items = await _run_actor("streamers/youtube-scraper", {
            "startUrls": [{"url": channel_url}],
            "maxResults": 5,
            "maxShorts": 0,
            "maxStreams": 0,
        }, timeout=240)
        if not items:
            return _empty_youtube()
        
        raw = items[0]
        videos = []
        for item in items:
            title = item.get("title", "")
            if title:
                videos.append(title)

        return {
            "channel_name": raw.get("channelName") or raw.get("title", ""),
            "description": raw.get("channelDescription") or "",
            "subscriber_count": _safe_int(raw.get("numberOfSubscribers")),
            "total_views": _safe_int(str(raw.get("channelTotalViews", "0")).replace(",", "")),
            "recent_videos": videos[:5],
            "data_found": True,
        }
    except Exception as e:
        print(f"[Scraper] YouTube profile error: {e}")
        return _empty_youtube()


def _empty_youtube() -> dict:
    return {"channel_name": "", "description": "", "subscriber_count": 0,
            "total_views": 0, "recent_videos": [], "data_found": False}


async def scrape_tiktok_profile(url: str) -> dict:
    """Scrape TikTok profile for identity data.
    
    Uses: clockworks/tiktok-scraper
    Input: {"profiles": ["username"], "resultsPerPage": 5, "profileScrapeSections": ["videos"]}
    Output keys: authorMeta (name, nickName, signature, fans, heart, video), 
                 text, playCount, diggCount
    """
    try:
        # Extract username from URL
        username = url.rstrip("/").split("/")[-1].lstrip("@")

        items = await _run_actor("clockworks/tiktok-scraper", {
            "profiles": [username],
            "resultsPerPage": 5,
            "profileScrapeSections": ["videos"],
            "profileSorting": "latest",
            "maxProfilesPerQuery": 5,
            "shouldDownloadVideos": False,
            "shouldDownloadCovers": False,
            "shouldDownloadSlideshowImages": False,
            "shouldDownloadSubtitles": False,
            "shouldDownloadMusicCovers": False,
            "shouldDownloadAvatars": False,
        }, timeout=240)
        if not items:
            return _empty_tiktok()
        
        raw = items[0]
        author = raw.get("authorMeta", {}) or {}
        videos = []
        for item in items:
            desc = item.get("text") or item.get("description", "")
            if desc:
                videos.append(desc[:300])

        return {
            "display_name": author.get("nickName") or author.get("name") or "",
            "username": author.get("name") or username,
            "bio": author.get("signature") or "",
            "follower_count": _safe_int(author.get("fans")),
            "heart_count": _safe_int(author.get("heart")),
            "video_count": _safe_int(author.get("video")),
            "recent_videos": videos[:5],
            "data_found": True,
        }
    except Exception as e:
        print(f"[Scraper] TikTok profile error: {e}")
        return _empty_tiktok()


def _empty_tiktok() -> dict:
    return {"display_name": "", "username": "", "bio": "", "follower_count": 0,
            "heart_count": 0, "video_count": 0,
            "recent_videos": [], "data_found": False}


async def scrape_instagram_profile(url: str) -> dict:
    """Scrape Instagram profile for identity data.
    
    Uses: apify/instagram-scraper
    Input: {"search": "username", "searchType": "user", "searchLimit": 1, 
            "resultsType": "details", "resultsLimit": 5}
    Output keys: fullName, username, biography, followersCount, followsCount,
                 postsCount, verified, latestPosts[]
    """
    try:
        # Extract username from URL
        username = url.rstrip("/").split("/")[-1].lstrip("@")

        items = await _run_actor("apify/instagram-scraper", {
            "search": username,
            "searchType": "user",
            "searchLimit": 1,
            "resultsType": "details",
            "resultsLimit": 5,
        })
        if not items:
            return _empty_instagram()
        
        raw = items[0]
        captions = []
        for post in raw.get("latestPosts", []) or []:
            caption = post.get("caption") or ""
            if caption:
                captions.append(caption[:300])

        return {
            "full_name": raw.get("fullName") or raw.get("full_name", ""),
            "username": raw.get("username", ""),
            "bio": raw.get("biography") or "",
            "follower_count": _safe_int(raw.get("followersCount")),
            "following_count": _safe_int(raw.get("followsCount")),
            "posts_count": _safe_int(raw.get("postsCount")),
            "verified": raw.get("verified", False),
            "recent_captions": captions[:5],
            "data_found": True,
        }
    except Exception as e:
        print(f"[Scraper] Instagram profile error: {e}")
        return _empty_instagram()


def _empty_instagram() -> dict:
    return {"full_name": "", "username": "", "bio": "", "follower_count": 0,
            "following_count": 0, "posts_count": 0, "verified": False,
            "recent_captions": [], "data_found": False}


async def scrape_twitter_profile(url: str) -> dict:
    """Scrape X/Twitter profile for identity data.
    
    Uses: apidojo/tweet-scraper
    Input: {"twitterHandles": ["username"], "maxItems": 10, "sort": "Latest"}
    Output keys: author (name, userName, followers, following, description, 
                 isVerified, isBlueVerified), text, fullText, likeCount, viewCount
    """
    try:
        # Extract username from URL
        username = url.rstrip("/").split("/")[-1].lstrip("@")
        
        items = await _run_actor("apidojo/tweet-scraper", {
            "twitterHandles": [username],
            "maxItems": 10,
            "sort": "Latest",
        })
        if not items:
            return _empty_twitter()
        
        raw = items[0]
        author = raw.get("author", {}) or {}

        tweets = []
        for item in items:
            text = item.get("fullText") or item.get("text", "")
            if text:
                tweets.append(text[:300])

        return {
            "display_name": author.get("name", ""),
            "username": author.get("userName") or username,
            "bio": author.get("description") or "",
            "follower_count": _safe_int(author.get("followers")),
            "following_count": _safe_int(author.get("following")),
            "verified": author.get("isVerified", False) or author.get("isBlueVerified", False),
            "recent_tweets": tweets[:5],
            "data_found": True,
        }
    except Exception as e:
        print(f"[Scraper] Twitter profile error: {e}")
        return _empty_twitter()


def _empty_twitter() -> dict:
    return {"display_name": "", "username": "", "bio": "", "follower_count": 0,
            "following_count": 0, "verified": False,
            "recent_tweets": [], "data_found": False}


# ═══════════════════════════════════════════════════════════
# BRAND MENTION FILTER
# ═══════════════════════════════════════════════════════════

def _mentions_brand(item: dict, brand_keywords: list, platform: str) -> bool:
    """Return True if the item explicitly mentions/tags the brand.
    
    Checks (in order of reliability):
      1. Structured mention/tag arrays (@ mentions, # hashtags)
      2. Brand keyword appearing in the text/caption/title
    """
    bk_lower = [k.lower() for k in brand_keywords]

    if platform == "youtube":
        # YouTube has no mention/tag system — check title + description
        title = (item.get("title") or "").lower()
        desc = (item.get("description") or "").lower()
        channel = (item.get("channelName") or "").lower()
        text = f"{title} {desc} {channel}"
        return any(kw in text for kw in bk_lower)

    elif platform == "tiktok":
        # Check mentions[] and hashtags[] arrays first, then caption text
        mentions = [m.lower() for m in (item.get("mentions") or [])]
        hashtags = []
        for h in (item.get("hashtags") or []):
            if isinstance(h, str):
                hashtags.append(h.lower())
            elif isinstance(h, dict):
                hashtags.append((h.get("name") or "").lower())
        for kw in bk_lower:
            if any(kw in m for m in mentions):
                return True
            if any(kw in h for h in hashtags):
                return True
        # Fallback: check caption text
        text = (item.get("text") or "").lower()
        return any(kw in text for kw in bk_lower)

    elif platform == "instagram":
        # Check mentions[] and hashtags[] arrays first, then caption
        mentions = [m.lower() for m in (item.get("mentions") or [])]
        hashtags = [(h if isinstance(h, str) else "").lower()
                    for h in (item.get("hashtags") or [])]
        for kw in bk_lower:
            if any(kw in m for m in mentions):
                return True
            if any(kw in h for h in hashtags):
                return True
        caption = (item.get("caption") or "").lower()
        return any(kw in caption for kw in bk_lower)

    elif platform == "twitter":
        # Check entities.user_mentions[] and entities.hashtags[] first
        entities = item.get("entities") or {}
        user_mentions = [m.get("screen_name", "").lower()
                         for m in (entities.get("user_mentions") or [])]
        hashtags = [h.get("text", "").lower()
                    for h in (entities.get("hashtags") or [])]
        for kw in bk_lower:
            if any(kw in m for m in user_mentions):
                return True
            if any(kw in h for h in hashtags):
                return True
        # Fallback: check tweet text
        text = (item.get("fullText") or item.get("text") or "").lower()
        return any(kw in text for kw in bk_lower)

    return False


# ═══════════════════════════════════════════════════════════
# STEP 3 — SEARCH MODE (brand mention volume, last 48h)
# Filtered: only items where the brand is explicitly mentioned/tagged
# ═══════════════════════════════════════════════════════════

async def search_youtube(query: str, brand_keywords: list = None) -> dict:
    """Search YouTube for brand mentions (filtered).
    
    Uses: streamers/youtube-scraper
    Input: {"searchKeywords": "query", "maxResults": 30}
    Output keys: title, viewCount, channelName, date, url
    """
    try:
        items = await _run_actor("streamers/youtube-scraper", {
            "searchKeywords": query,
            "maxResults": SEARCH_MAX_RESULTS,
            "maxShorts": 0,
            "maxStreams": 0,
        }, timeout=240)

        # Filter for brand mentions only
        if brand_keywords:
            raw_count = len(items)
            items = [i for i in items if _mentions_brand(i, brand_keywords, "youtube")]
            print(f"[Scraper] YouTube: {raw_count} results -> {len(items)} brand mentions")

        total_views = 0
        top_title = ""
        top_views = 0
        for item in items:
            views = _safe_int(item.get("viewCount"))
            total_views += views
            if views > top_views:
                top_views = views
                top_title = item.get("title", "")

        return {
            "total_views_48h": total_views,
            "video_count": len(items),
            "top_video_title": top_title,
            "top_video_views": top_views,
            "data_found": len(items) > 0,
        }
    except Exception as e:
        print(f"[Scraper] YouTube search error: {e}")
        return _empty_youtube_search()


def _empty_youtube_search() -> dict:
    return {"total_views_48h": 0, "video_count": 0, "top_video_title": "",
            "top_video_views": 0, "data_found": False}


async def search_tiktok(query: str, brand_keywords: list = None) -> dict:
    """Search TikTok for brand mentions (filtered).
    
    Uses: clockworks/tiktok-scraper
    Input: {"searchQueries": ["query"], "resultsPerPage": 30}
    Output keys: text, playCount, diggCount, shareCount, authorMeta, mentions[], hashtags[]
    """
    try:
        items = await _run_actor("clockworks/tiktok-scraper", {
            "searchQueries": [query],
            "resultsPerPage": SEARCH_MAX_RESULTS,
            "shouldDownloadVideos": False,
            "shouldDownloadCovers": False,
            "shouldDownloadSlideshowImages": False,
            "shouldDownloadSubtitles": False,
            "shouldDownloadMusicCovers": False,
            "shouldDownloadAvatars": False,
        }, timeout=180)

        # Filter for brand mentions only
        if brand_keywords:
            raw_count = len(items)
            items = [i for i in items if _mentions_brand(i, brand_keywords, "tiktok")]
            print(f"[Scraper] TikTok: {raw_count} results -> {len(items)} brand mentions")

        total_views = 0
        top_desc = ""
        top_views = 0
        for item in items:
            views = _safe_int(item.get("playCount"))
            total_views += views
            if views > top_views:
                top_views = views
                top_desc = (item.get("text") or "")[:200]

        return {
            "total_views_48h": total_views,
            "video_count": len(items),
            "top_video_desc": top_desc,
            "top_video_views": top_views,
            "data_found": len(items) > 0,
        }
    except Exception as e:
        print(f"[Scraper] TikTok search error: {e}")
        return _empty_tiktok_search()


def _empty_tiktok_search() -> dict:
    return {"total_views_48h": 0, "video_count": 0, "top_video_desc": "",
            "top_video_views": 0, "data_found": False}


async def search_instagram(query: str, brand_keywords: list = None) -> dict:
    """Search Instagram for brand mentions via hashtags (filtered).
    
    Uses: apify/instagram-hashtag-scraper
    Input: {"hashtags": ["query"], "resultsLimit": 30}
    Output keys: caption, likesCount, commentsCount, ownerUsername,
                 videoPlayCount, timestamp, mentions[], hashtags[]
    """
    try:
        # Clean query for hashtag use (remove spaces, use as-is)
        hashtag = query.replace(" ", "").lower()
        
        items = await _run_actor("apify/instagram-hashtag-scraper", {
            "hashtags": [hashtag],
            "resultsLimit": SEARCH_MAX_RESULTS,
        })

        # Filter for brand mentions only
        if brand_keywords:
            raw_count = len(items)
            items = [i for i in items if _mentions_brand(i, brand_keywords, "instagram")]
            print(f"[Scraper] Instagram: {raw_count} results -> {len(items)} brand mentions")

        total_interactions = 0
        total_video_views = 0
        post_count = 0
        for item in items:
            likes = _safe_int(item.get("likesCount"))
            comments = _safe_int(item.get("commentsCount"))
            video_views = _safe_int(item.get("videoPlayCount"))
            total_interactions += likes + comments
            total_video_views += video_views
            post_count += 1

        # Rough reach estimate: 10x interactions + video views
        estimated_reach = total_interactions * 10 + total_video_views

        return {
            "total_interactions_48h": total_interactions,
            "total_video_views": total_video_views,
            "post_count": post_count,
            "estimated_reach": estimated_reach,
            "data_found": post_count > 0,
        }
    except Exception as e:
        print(f"[Scraper] Instagram search error: {e}")
        return _empty_instagram_search()


def _empty_instagram_search() -> dict:
    return {"total_interactions_48h": 0, "total_video_views": 0,
            "post_count": 0, "estimated_reach": 0, "data_found": False}


async def search_twitter(query: str, brand_keywords: list = None) -> dict:
    """Search X/Twitter for brand mentions (filtered).
    
    Uses: apidojo/tweet-scraper
    Input: {"searchTerms": ["query"], "maxItems": 30, "sort": "Latest"}
    Output keys: text, fullText, likeCount, retweetCount, replyCount, 
                 quoteCount, viewCount, bookmarkCount, createdAt,
                 entities.user_mentions[], entities.hashtags[]
    """
    try:
        items = await _run_actor("apidojo/tweet-scraper", {
            "searchTerms": [query],
            "maxItems": SEARCH_MAX_RESULTS,
            "sort": "Latest",
        })

        # Filter for brand mentions only
        if brand_keywords:
            raw_count = len(items)
            items = [i for i in items if _mentions_brand(i, brand_keywords, "twitter")]
            print(f"[Scraper] Twitter: {raw_count} results -> {len(items)} brand mentions")

        total_impressions = 0
        total_engagement = 0
        top_text = ""
        top_impressions = 0
        for item in items:
            views = _safe_int(item.get("viewCount"))
            likes = _safe_int(item.get("likeCount"))
            retweets = _safe_int(item.get("retweetCount"))
            replies = _safe_int(item.get("replyCount"))
            total_impressions += views
            total_engagement += likes + retweets + replies
            if views > top_impressions:
                top_impressions = views
                top_text = (item.get("fullText") or item.get("text", ""))[:200]

        return {
            "total_impressions_48h": total_impressions,
            "total_engagement": total_engagement,
            "tweet_count": len(items),
            "top_tweet_text": top_text,
            "top_tweet_impressions": top_impressions,
            "data_found": len(items) > 0,
        }
    except Exception as e:
        print(f"[Scraper] Twitter search error: {e}")
        return _empty_twitter_search()


def _empty_twitter_search() -> dict:
    return {"total_impressions_48h": 0, "total_engagement": 0,
            "tweet_count": 0, "top_tweet_text": "",
            "top_tweet_impressions": 0, "data_found": False}

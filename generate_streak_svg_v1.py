#!/usr/bin/env python3
"""Generate the animated contribution heatmap using GitHub's own GraphQL data.

The SVG layout, colors, reveal animation and flash animation are intentionally
kept in the same style as the previous version. Only the data source and
calendar positioning are changed.

Usage: python generate_streak_svg_v1.py [username] [output.svg]
Requires PROFILE_REPO_PAT (or GH_TOKEN) in the environment.
"""
import sys
import json
import os
import datetime
import urllib.request
import urllib.error

USER = sys.argv[1] if len(sys.argv) > 1 else "whokrishverma"
OUT = sys.argv[2] if len(sys.argv) > 2 else "contrib-heatmap.svg"
GRAPHQL_URL = "https://api.github.com/graphql"

QUERY = """
query ContributionCalendar($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          firstDay
          contributionDays {
            date
            weekday
            contributionCount
            contributionLevel
            color
          }
        }
        months {
          firstDay
          name
        }
      }
    }
  }
}
"""


def get_data(user):
    token = os.environ.get("PROFILE_REPO_PAT") or os.environ.get("GH_TOKEN")
    if not token:
        raise RuntimeError(
            "Missing PROFILE_REPO_PAT (or GH_TOKEN). Set it as a GitHub Actions secret."
        )

    body = json.dumps({"query": QUERY, "variables": {"login": user}}).encode("utf-8")
    request = urllib.request.Request(
        GRAPHQL_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json",
            "User-Agent": "profile-art-generator",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub GraphQL request failed (HTTP {exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach GitHub GraphQL API: {exc}") from exc

    if payload.get("errors"):
        messages = "; ".join(item.get("message", "Unknown GraphQL error") for item in payload["errors"])
        raise RuntimeError(f"GitHub GraphQL returned an error: {messages}")

    user_data = (payload.get("data") or {}).get("user")
    if not user_data:
        raise RuntimeError(f"GitHub user '{user}' was not found or is not accessible.")

    calendar = user_data["contributionsCollection"]["contributionCalendar"]
    days = [day for week in calendar["weeks"] for day in week["contributionDays"]]
    if not days:
        raise RuntimeError("GitHub returned an empty contribution calendar.")
    return calendar, days


calendar, contribs = get_data(USER)
total = calendar["totalContributions"]

# ---- layout (preserved) ----
CELL, GAP, RAD, LEFT, TOP = 13, 3, 2.5, 34, 24
FLASH = "#b4ffaa"
GRAY = "#7d8590"
MONTHS = {
    "January": "Jan", "February": "Feb", "March": "Mar", "April": "Apr",
    "May": "May", "June": "Jun", "July": "Jul", "August": "Aug",
    "September": "Sep", "October": "Oct", "November": "Nov", "December": "Dec",
}
COLORS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
LEVELS = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}

weeks = calendar["weeks"]
NW = len(weeks)
W = LEFT + NW * (CELL + GAP) + 6
H = TOP + 7 * (CELL + GAP) + 22

# timing (seconds) -- preserve the existing reveal and flash effect
REVEAL, DUR = 3.6, 0.55
maxorder = max(1, (NW - 1) + 6 * 0.55)

rects, labels = [], []

# Use GitHub's own month start dates, mapped to the exact week column.
week_index_by_date = {}
for wk, week in enumerate(weeks):
    for day in week["contributionDays"]:
        week_index_by_date[day["date"]] = wk

for month in calendar["months"]:
    wk = week_index_by_date.get(month["firstDay"])
    if wk is not None:
        month_name = MONTHS.get(month["name"], month["name"][:3])
        labels.append(
            f'<text class="lbl" x="{LEFT + wk * (CELL + GAP)}" y="{TOP - 8}">{month_name}</text>'
        )

# GitHub's weekday is Sunday=0 through Saturday=6. Use each day's actual
# week and weekday instead of assuming the first returned date is Sunday.
for name, row in [("Mon", 1), ("Wed", 3), ("Fri", 5)]:
    labels.append(f'<text class="lbl" x="2" y="{TOP + row * (CELL + GAP) + CELL - 2}">{name}</text>')

for wk, week in enumerate(weeks):
    for day in week["contributionDays"]:
        row = int(day["weekday"])
        level_name = day["contributionLevel"]
        level = LEVELS.get(level_name)
        if level is None:
            raise RuntimeError(f"Unknown GitHub contribution level: {level_name}")

        # Keep the original dark-theme palette. GraphQL day["color"] can
        # reflect GitHub's light-theme palette, so map the authoritative
        # contributionLevel to our existing dark-theme colors instead.
        color = COLORS[level]
        x = LEFT + wk * (CELL + GAP)
        y = TOP + row * (CELL + GAP)
        delay = round((wk + row * 0.55) / maxorder * REVEAL, 3)
        cls = "c g" if level >= 1 else "c e"
        rects.append(
            f'<rect class="{cls}" x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
            f'rx="{RAD}" fill="{color}" style="animation-delay:{delay}s" '
            f'data-date="{day["date"]}" data-count="{day["contributionCount"]}"/>'
        )

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">
<style>
  text.lbl {{ fill:{GRAY}; font-size:13px; font-weight:600; }}
  text.total {{ fill:##7d859; font-size:15px; font-weight:700; }}
  .c {{ transform-box:fill-box; transform-origin:center; opacity:0; animation:pop {DUR}s ease-out both; }}
  .g {{ animation:pop {DUR}s ease-out both, flash {DUR+0.15}s ease-out both; }}
  @keyframes pop {{ 0%{{opacity:0;transform:scale(.2)}} 60%{{opacity:1;transform:scale(1.1)}} 100%{{opacity:1;transform:scale(1)}} }}
  @keyframes flash {{ 0%{{filter:brightness(2.4)}} 45%{{filter:brightness(2.4)}} 100%{{filter:brightness(1)}} }}
  @media (prefers-reduced-motion: reduce) {{ .c {{ opacity:1 !important; animation:none !important; }} }}
</style>
<rect width="{W}" height="{H}" fill="none"/>
{''.join(labels)}
{''.join(rects)}
<text class="total" x="{LEFT}" y="{H-6}">{total:,} contributions in the last year</text>
</svg>'''

with open(OUT, "w", encoding="utf-8") as output:
    output.write(svg)
print(f"Wrote {OUT}: {len(contribs)} days, {total:,} contributions, {len(svg)//1024} KB")

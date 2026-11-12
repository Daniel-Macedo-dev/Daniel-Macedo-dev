"""Builds images/card.svg: a neofetch-style profile card with live GitHub stats.

Runs in GitHub Actions (GITHUB_TOKEN) or locally (GH_TOKEN). Only the Python
standard library is used, so the workflow needs no extra installs.
"""
import base64
import datetime as dt
import html
import json
import os
import urllib.request
from pathlib import Path

USER = os.environ.get("CARD_USER", "Daniel-Macedo-dev")
ROOT = Path(__file__).resolve().parents[2]
AVATAR = ROOT / "images" / "avatar-card.jpg"
OUT = ROOT / "images" / "card.svg"

# GitHub dark palette (contrast >= 7:1 on the card background)
BG, BORDER = "#161b22", "#30363d"
KEY, VALUE, DOTS, TITLE, MUTED, ACCENT = "#ffa657", "#a5d6ff", "#484f58", "#79c0ff", "#8b949e", "#7ee787"
FONT = "Consolas,'SF Mono',Menlo,'DejaVu Sans Mono','Liberation Mono',monospace"

WIDTH = 62  # characters per text line (title rule, key ... value)
TEXT_X, TEXT_W = 396, 566  # every full line is stretched to exactly TEXT_W px (font-independent)

SECTIONS = [
    ("daniel@macedo", [
        ("Role", "Backend & Full-Stack Developer"),
        ("Location", "São Paulo, Brazil"),
        ("Uptime", "{uptime}"),
        ("Languages.Code", "Java, TypeScript, Python, SQL"),
        ("Languages.Human", "Portuguese, English"),
        ("Hobbies", "Games, Anime, Cyberpunk"),
    ]),
    ("Stack", [
        ("Backend", "Spring Boot, JPA/Hibernate, FastAPI"),
        ("Frontend", "React, Next.js, Vite, Tailwind CSS"),
        ("Desktop", "JavaFX"),
        ("Data", "PostgreSQL, Supabase, Flyway, SQLite"),
        ("Testing", "JUnit 5, Testcontainers, Vitest, Playwright"),
        ("DevOps", "Docker, GitHub Actions, Maven"),
    ]),
    ("Contact", [
        ("Email", "danielmacedosilva11@gmail.com"),
        ("LinkedIn", "in/daniel-macedo-dev"),
    ]),
    ("GitHub Stats", [
        ("Public repos", "{repos}"),
        ("Contributed to", "{contributed} repos"),
        ("Contributions", "{contribs} ({last_year} last year)"),
        ("Stars / Followers", "{stars} / {followers}"),
    ]),
]


def gql(query, variables, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "profile-card"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if body.get("errors"):
        raise RuntimeError(body["errors"])
    return body["data"]


def stats(token):
    base = gql(
        """query($u:String!){ user(login:$u){ createdAt followers{totalCount}
             repositoriesContributedTo(contributionTypes:[COMMIT,PULL_REQUEST,ISSUE,REPOSITORY]){totalCount}
             repositories(ownerAffiliations:OWNER, privacy:PUBLIC, first:100){ totalCount nodes{ stargazerCount } }
             contributionsCollection{ contributionCalendar{ totalContributions } } } }""",
        {"u": USER}, token)["user"]
    created = dt.datetime.fromisoformat(base["createdAt"].replace("Z", "+00:00"))
    now = dt.datetime.now(dt.timezone.utc)
    total, start = 0, created
    while start < now:
        end = min(start + dt.timedelta(days=365), now)
        total += gql(
            """query($u:String!,$f:DateTime!,$t:DateTime!){ user(login:$u){
                 contributionsCollection(from:$f,to:$t){ contributionCalendar{ totalContributions } } } }""",
            {"u": USER, "f": start.isoformat(), "t": end.isoformat()}, token,
        )["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
        start = end
    return {
        "created": created,
        "repos": base["repositories"]["totalCount"],
        "stars": sum(n["stargazerCount"] for n in base["repositories"]["nodes"]),
        "followers": base["followers"]["totalCount"],
        "contributed": base["repositoriesContributedTo"]["totalCount"],
        "contribs": total,
        "last_year": base["contributionsCollection"]["contributionCalendar"]["totalContributions"],
    }


def uptime(created):
    today = dt.date.today()
    c = created.date()
    months = (today.year - c.year) * 12 + today.month - c.month - (today.day < c.day)
    anchor_m = c.month - 1 + months
    anchor = dt.date(c.year + anchor_m // 12, anchor_m % 12 + 1, min(c.day, 28))
    days = (today - anchor).days
    y, m = divmod(months, 12)
    parts = [f"{y} year{'s' * (y != 1)}"] if y else []
    parts += [f"{m} month{'s' * (m != 1)}", f"{days} day{'s' * (days != 1)}"]
    return ", ".join(parts) + " on GitHub"


def esc(s):
    return html.escape(s, quote=False)


def line(key, value):
    dots = WIDTH - len(key) - len(value) - 4
    return (f'<tspan fill="{KEY}">{esc(key)}</tspan><tspan fill="{MUTED}">:</tspan>'
            f'<tspan fill="{DOTS}"> {"." * max(dots, 1)} </tspan><tspan fill="{VALUE}">{esc(value)}</tspan>')


def rule(title):
    if title == SECTIONS[0][0]:
        return f'<tspan fill="{TITLE}" font-weight="700">{esc(title)}</tspan><tspan fill="{DOTS}"> {"—" * (WIDTH - len(title) - 1)}</tspan>'
    return f'<tspan fill="{DOTS}">- </tspan><tspan fill="{TITLE}" font-weight="700">{esc(title)}</tspan><tspan fill="{DOTS}"> {"—" * (WIDTH - len(title) - 3)}</tspan>'


def build(data):
    rows = []
    for i, (title, items) in enumerate(SECTIONS):
        if i:
            rows.append("")
        rows.append(rule(title))
        rows += [line(k, v.format(**data)) for k, v in items]
    quote = (f'<tspan fill="{MUTED}">// </tspan><tspan fill="{ACCENT}" font-style="italic">&quot;The net is vast and infinite.&quot;</tspan>'
             f'<tspan fill="{ACCENT}" class="cursor"> ▋</tspan>')
    rows += ["", None]

    lh, top, x = 22, 50, TEXT_X
    height = top + lh * (len(rows) - 1) + 40
    out = []
    for i, r in enumerate(rows):
        y = top + i * lh
        if r is None:
            out.append(f'  <text x="{x}" y="{y}" class="t">{quote}</text>')
        elif r:
            out.append(f'  <text x="{x}" y="{y}" class="t" textLength="{TEXT_W}" lengthAdjust="spacing">{r}</text>')
    text = "\n".join(out)
    img = base64.b64encode(AVATAR.read_bytes()).decode()
    size = 330
    iy = (height - size) // 2
    return f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1000" height="{height}" viewBox="0 0 1000 {height}" role="img" aria-label="Daniel Macedo, Backend and Full-Stack Developer">
  <title>Daniel Macedo, Backend &amp; Full-Stack Developer</title>
  <defs>
    <clipPath id="av"><rect x="36" y="{iy}" width="{size}" height="{size}" rx="14"/></clipPath>
    <pattern id="scan" width="3" height="3" patternUnits="userSpaceOnUse"><rect width="3" height="1" fill="#000" opacity="0.28"/></pattern>
    <linearGradient id="tint" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#79c0ff" stop-opacity="0.10"/><stop offset="1" stop-color="#d2a8ff" stop-opacity="0.12"/>
    </linearGradient>
    <style>
      .t {{ font-family: {FONT}; font-size: 15.5px; white-space: pre; }}
      .cursor {{ animation: blink 1.1s steps(1) infinite; }}
      @keyframes blink {{ 50% {{ opacity: 0; }} }}
      @media (prefers-reduced-motion: reduce) {{ .cursor {{ animation: none; }} }}
    </style>
  </defs>
  <rect x="1" y="1" width="998" height="{height - 2}" rx="14" fill="{BG}" stroke="{BORDER}" stroke-width="2"/>
  <g clip-path="url(#av)">
    <image x="36" y="{iy}" width="{size}" height="{size}" preserveAspectRatio="xMidYMid slice" href="data:image/jpeg;base64,{img}" xlink:href="data:image/jpeg;base64,{img}"/>
    <rect x="36" y="{iy}" width="{size}" height="{size}" fill="url(#tint)"/>
    <rect x="36" y="{iy}" width="{size}" height="{size}" fill="url(#scan)"/>
  </g>
  <rect x="36" y="{iy}" width="{size}" height="{size}" rx="14" fill="none" stroke="{BORDER}" stroke-width="1.5"/>
{text}
</svg>
"""


def main():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    s = stats(token)
    data = {k: f"{v:,}" if isinstance(v, int) else v for k, v in s.items()}
    data["uptime"] = uptime(s["created"])
    OUT.write_text(build(data), encoding="utf-8", newline="\n")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes): {data}")


if __name__ == "__main__":
    main()

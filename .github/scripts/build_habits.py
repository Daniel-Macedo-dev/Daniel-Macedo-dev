"""Builds images/habits.svg: when Daniel codes (time of day from public commits,
day of week from the contribution calendar). Standard library only."""
import datetime as dt
import html
import json
import os
import urllib.request
from collections import Counter
from pathlib import Path

USER = os.environ.get("CARD_USER", "Daniel-Macedo-dev")
ORGS = ["DeD-TechStack"]
TZ = dt.timezone(dt.timedelta(hours=-3), "BRT")  # São Paulo (no DST since 2019)
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "images" / "habits.svg"

BG, BORDER, TRACK = "#161b22", "#30363d", "#21262d"
TITLE, TEXT, MUTED, KEY, VALUE, ACCENT = "#79c0ff", "#c9d1d9", "#8b949e", "#ffa657", "#a5d6ff", "#7ee787"
MONO = "Consolas,'SF Mono',Menlo,'DejaVu Sans Mono',monospace"


def gql(query, variables, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "profile-habits"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        body = json.load(r)
    if body.get("errors"):
        raise RuntimeError(body["errors"])
    return body["data"]


def repos(token, uid):
    found = []
    for owner, kind in [(USER, "user")] + [(o, "organization") for o in ORGS]:
        cursor = None
        while True:
            d = gql(f"""query($o:String!,$c:String){{ {kind}(login:$o){{ repositories(first:100, after:$c, privacy:PUBLIC, isFork:false){{
                       pageInfo{{hasNextPage endCursor}} nodes{{ nameWithOwner }} }} }} }}""", {"o": owner, "c": cursor}, token)
            page = d[kind]["repositories"]
            found += [n["nameWithOwner"] for n in page["nodes"]]
            if not page["pageInfo"]["hasNextPage"]:
                break
            cursor = page["pageInfo"]["endCursor"]
    return found


def commit_times(token):
    uid = gql("query($u:String!){ user(login:$u){ id } }", {"u": USER}, token)["user"]["id"]
    times = []
    for full in repos(token, uid):
        owner, name = full.split("/")
        cursor = None
        for _ in range(20):  # up to 2,000 commits per repo
            d = gql("""query($o:String!,$n:String!,$a:ID!,$c:String){ repository(owner:$o,name:$n){ defaultBranchRef{ target{
                         ... on Commit{ history(first:100, after:$c, author:{id:$a}){ pageInfo{hasNextPage endCursor} nodes{ committedDate } } } } } } }""",
                    {"o": owner, "n": name, "a": uid, "c": cursor}, token)
            ref = (d["repository"] or {}).get("defaultBranchRef")
            if not ref:
                break
            h = ref["target"]["history"]
            times += [dt.datetime.fromisoformat(n["committedDate"].replace("Z", "+00:00")).astimezone(TZ) for n in h["nodes"]]
            if not h["pageInfo"]["hasNextPage"]:
                break
            cursor = h["pageInfo"]["endCursor"]
    return times


def weekdays(token):
    d = gql("""query($u:String!){ user(login:$u){ contributionsCollection{ contributionCalendar{ weeks{ contributionDays{ weekday contributionCount } } } } } }""",
            {"u": USER}, token)
    c = Counter()
    for w in d["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]:
        for day in w["contributionDays"]:
            c[day["weekday"]] += day["contributionCount"]
    return c  # 0 = Sunday


def esc(s):
    return html.escape(s, quote=False)


def bars(rows, x, y, step, label_w, track_w):
    """One row per item: label, rounded track with a bar, right-aligned percentage."""
    total = sum(v for _, v in rows) or 1
    top = max(v for _, v in rows)
    out = []
    for i, (label, v) in enumerate(rows):
        cy = y + i * step
        w = max(track_w * v / top, 10) if v else 0
        hot = v == top
        bx = x + label_w
        out.append(
            f'<text x="{x}" y="{cy + 5}" font-family="{MONO}" font-size="15" fill="{KEY if hot else TEXT}">{esc(label)}</text>'
            f'<rect x="{bx}" y="{cy - 5}" width="{track_w}" height="10" rx="5" fill="{TRACK}"/>'
            f'<rect x="{bx}" y="{cy - 5}" width="{w:.1f}" height="10" rx="5" fill="{KEY if hot else VALUE}"/>'
            f'<text x="{bx + track_w + 62}" y="{cy + 5}" text-anchor="end" font-family="{MONO}" font-size="15" fill="{KEY if hot else MUTED}">{v / total * 100:.1f}%</text>')
    return "\n  ".join(out)


def rule(x, y, title, width_chars, px):
    return (f'<text x="{x}" y="{y}" font-family="{MONO}" font-size="15" textLength="{px}" lengthAdjust="spacing"><tspan fill="#484f58">- </tspan>'
            f'<tspan fill="{TITLE}" font-weight="700">{esc(title)}</tspan><tspan fill="#484f58"> {"—" * (width_chars - len(title) - 3)}</tspan></text>')


def build(times, wd):
    slots = [("Morning", range(6, 12), "06–12"), ("Daytime", range(12, 18), "12–18"),
             ("Evening", range(18, 24), "18–24"), ("Night", range(0, 6), "00–06")]
    hours = Counter(t.hour for t in times)
    tod = [(f"{name:<8}{span}", sum(hours[h] for h in rng)) for name, rng, span in slots]
    best = max(tod, key=lambda r: r[1])[0].split()[0]
    glyph, persona = {"Morning": ("☀", "an early bird"), "Daytime": ("☀", "a daytime coder"),
                      "Evening": ("☾", "an evening coder"), "Night": ("☾", "a night owl")}[best]
    peak = max(range(24), key=lambda h: hours[h])
    names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    full = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    order = (1, 2, 3, 4, 5, 6, 0)
    week = [(names[i], wd[i]) for i in order]
    top_day = full[max(order, key=lambda i: wd[i])]

    W, step_w = 1000, 26
    y0 = 196
    span = step_w * 6
    step_t = span / 3
    H = y0 + span + 44
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Coding habits: I'm {esc(persona)}, most productive on {top_day}">
  <title>Coding habits</title>
  <rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="14" fill="{BG}" stroke="{BORDER}" stroke-width="2"/>
  <text x="40" y="50" font-family="{MONO}" font-size="15" fill="{MUTED}">~/daniel <tspan fill="{ACCENT}">❯</tspan> <tspan fill="{TEXT}">git log --author=daniel | habits</tspan></text>
  <text x="40" y="92" font-family="{MONO}" font-size="24" font-weight="700" fill="{TITLE}"><tspan fill="{KEY}">{glyph}</tspan> I'm {esc(persona)}</text>
  <text x="40" y="122" font-family="{MONO}" font-size="15" fill="#9da7b3">peak hour <tspan fill="{VALUE}">{peak:02d}:00</tspan> (São Paulo) · busiest day <tspan fill="{VALUE}">{top_day}</tspan> · from <tspan fill="{VALUE}">{len(times):,}</tspan> public commits</text>
  {rule(40, 162, "Time of day", 50, 432)}
  {bars(tod, 40, y0, step_t, 150, 220)}
  {rule(530, 162, "Day of week", 50, 432)}
  {bars(week, 530, y0, step_w, 60, 310)}
</svg>
"""


def main():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    times, wd = commit_times(token), weekdays(token)
    OUT.write_text(build(times, wd), encoding="utf-8", newline="\n")
    print(f"wrote {OUT}: {len(times)} commits, hours={sorted(Counter(t.hour for t in times).items())}, weekdays={dict(wd)}")


if __name__ == "__main__":
    main()

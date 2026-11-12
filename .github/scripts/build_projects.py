"""Builds images/projects/*.svg: featured project cards in the profile card palette."""
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "images" / "projects"

BG, BORDER, CHIP_BG = "#161b22", "#30363d", "#0d1117"
TITLE, TEXT, MUTED, KEY, VALUE = "#79c0ff", "#c9d1d9", "#8b949e", "#ffa657", "#a5d6ff"
SANS = "'Segoe UI',-apple-system,BlinkMacSystemFont,Helvetica,Arial,sans-serif"
MONO = "Consolas,'SF Mono',Menlo,'DejaVu Sans Mono',monospace"

PROJECTS = [
    ("finora", "Finora", "Daniel-Macedo-dev/Finora", "Full-stack",
     ["Personal finance and purchase planning, multi-user,", "with deterministic analysis of your own data."],
     ["Java", "Spring Boot", "PostgreSQL", "React", "TypeScript"]),
    ("breakinv", "BreakInv", "DeD-TechStack/BreakInv", "Desktop",
     ["Local-first desktop app to track, analyze and follow", "an investment portfolio and its performance."],
     ["Java", "JavaFX", "SQLite", "Maven", "JUnit 5"]),
    ("appmaternidade", "AppMaternidade", "DeD-TechStack/AppMaternidade", "Web app",
     ["For parents and caregivers: baby routine and growth,", "shared care and a community organized by topic."],
     ["React", "TypeScript", "Supabase", "PostgreSQL", "Vite"]),
    ("forjai", "FORJAI", "Daniel-Macedo-dev/forjai-site", "Website",
     ["On-demand 3D printing site with portfolio", "and local quote preparation."],
     ["React", "Three.js", "Tailwind CSS", "Vite", "Playwright"]),
]

W, H = 480, 170


def esc(s):
    return html.escape(s, quote=False)


def chips(items, x, y):
    out, cx = [], x
    for it in items:
        w = int(len(it) * 7.4 + 20)
        out.append(f'<rect x="{cx}" y="{y}" width="{w}" height="24" rx="12" fill="{CHIP_BG}" stroke="{BORDER}"/>'
                   f'<text x="{cx + w / 2:.1f}" y="{y + 16.5}" text-anchor="middle" font-family="{MONO}" font-size="12.5" fill="{VALUE}">{esc(it)}</text>')
        cx += w + 8
    return "\n  ".join(out)


def card(name, repo, kind, desc, stack):
    lines = "\n  ".join(
        f'<text x="24" y="{86 + i * 21}" font-family="{SANS}" font-size="14.5" fill="{TEXT}">{esc(t)}</text>'
        for i, t in enumerate(desc))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(name)}: {esc(' '.join(desc))}">
  <title>{esc(name)}</title>
  <rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="12" fill="{BG}" stroke="{BORDER}" stroke-width="2"/>
  <path d="M24 22h3v3h-3zM29 22h3v3h-3zM24 27h3v3h-3z" fill="{MUTED}"/>
  <text x="42" y="31" font-family="{MONO}" font-size="12.5" fill="{MUTED}">{esc(repo)}</text>
  <text x="{W - 24}" y="31" text-anchor="end" font-family="{MONO}" font-size="12.5" fill="{KEY}">{esc(kind)}</text>
  <text x="24" y="61" font-family="{SANS}" font-size="21" font-weight="700" fill="{TITLE}">{esc(name)}</text>
  {lines}
  {chips(stack, 24, H - 44)}
</svg>
"""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for slug, name, repo, kind, desc, stack in PROJECTS:
        (OUT / f"{slug}.svg").write_text(card(name, repo, kind, desc, stack), encoding="utf-8", newline="\n")
    print("wrote", len(PROJECTS), "project cards to", OUT)


if __name__ == "__main__":
    main()

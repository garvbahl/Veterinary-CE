
import re
html = open("midmark.html", encoding="utf-8").read()
blocks = re.split(r'(?=<div class="course")', html)
n = 0
for b in blocks:
    tm = re.search(r'<h3[^>]*>(.*?)</h3>', b)
    if not tm:
        continue
    n += 1
    title = re.sub(r"<[^>]+>", "", tm.group(1)).strip()
    hours = re.search(r'(\d+(?:\.\d+)?)\s*Hours?\s*RACE', b)
    part = re.search(r'Part Number:\s*([^<]+)', b)
    audience = re.search(r'Audience:\s*([^<]+)', b)
    link = re.search(r'href="(https://shop\.midmark\.com[^"]+)"', b)
    desc = re.search(r'accent-3-medium-dark[^>]*>([^<]{40,})', b)
    print("="*50)
    print("TITLE:", title)
    print("HOURS:", hours.group(1) if hours else "?")
    print("PART:", part.group(1).strip() if part else "?")
    print("AUDIENCE:", audience.group(1).strip() if audience else "?")
    print("LINK:", (link.group(1)[:80] if link else "?"))
    print("DESC:", (desc.group(1).strip()[:120] if desc else "?"))
print()
print("TOTAL:", n)



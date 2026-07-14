
import re
html = open("midmark.html", encoding="utf-8").read()

# Find all course blocks by their h3 title + the hours/RACE line + whether they mention online/in-clinic
courses = re.findall(r'<div class="course".*?</h3>', html, re.DOTALL)
titles = re.findall(r'<div class="course".*?<h3[^>]*>(.*?)</h3>', html, re.DOTALL)
print("TOTAL course blocks:", len(titles))
print()
for i, t in enumerate(titles):
    print(f"{i+1}. {t.strip()}")

print()
print("=== Which mention 'online' vs 'in your clinic' ===")
blocks = re.split(r'(?=<div class="course")', html)
for b in blocks:
    tm = re.search(r'<h3[^>]*>(.*?)</h3>', b)
    if not tm:
        continue
    title = tm.group(1).strip()
    is_online = "online course" in b.lower() or "self-paced" in b.lower() or "on-demand" in b.lower()
    is_clinic = "in your clinic" in b.lower() or "in-clinic" in b.lower() or "hands-on" in b.lower()
    tag = "ONLINE" if is_online else ("IN-CLINIC" if is_clinic else "?")
    print(f"[{tag}] {title}")



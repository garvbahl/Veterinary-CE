import re
html = open("midmark.html", encoding="utf-8").read()
# Find links near "online" / "View Online"
for m in re.finditer(r'(View Online[^<]*|dentistry-online|Online Course[^<]*)', html, re.IGNORECASE):
    start = max(0, m.start()-300)
    print("---")
    print(html[start:m.end()+100])
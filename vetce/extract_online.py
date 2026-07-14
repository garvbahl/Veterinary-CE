import re
html = open("midmark.html", encoding="utf-8").read()
m = re.search(r'id="dentistry-online".*?</section>', html, re.DOTALL)
if not m:
    print("NOT FOUND - trying alternate")
    # try finding the online section by heading
    m = re.search(r'Dentistry \(Online\).*?</section>', html, re.DOTALL)
print(m.group(0)[:4500] if m else "STILL NOT FOUND")



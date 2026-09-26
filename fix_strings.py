import re

for file in ["frontend/src/app/(dashboard)/events/page.tsx", "frontend/src/app/(dashboard)/events/[id]/page.tsx"]:
    with open(file, "r") as f:
        content = f.read()
    
    # Replace \/events/ with /events/
    content = content.replace("\/events/?\\\", "/events/?")
    content = content.replace("\/events/\\\", "/events/")
    content = content.replace("\/events/\/revisions\\", "/events//revisions")
    
    # also replace any stray backticks that got escaped wrong if necessary
    
    with open(file, "w") as f:
        f.write(content)


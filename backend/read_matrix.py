with open(r'C:\Users\Shubham Yadav\.gemini\antigravity\brain\0da3836f-79b4-4d21-b474-6e1d98277a9c\phase_4e_architecture_v10.md', 'r') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "Previous State \ Current State" in line:
        for j in range(i, i+15):
            print(lines[j].strip())
        break

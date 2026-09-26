import json

with open('pw_lines.txt', 'w', encoding='utf-8') as out:
    with open(r'C:\Users\Shubham Yadav\.gemini\antigravity\brain\0da3836f-79b4-4d21-b474-6e1d98277a9c\.system_generated\logs\transcript_full.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            if data.get('type') == 'USER_INPUT' and 'password' in data.get('content', '').lower():
                content = data['content']
                for c_line in content.split('\n'):
                    if 'password' in c_line.lower():
                        out.write(f"Step {data['step_index']}: {c_line}\n")

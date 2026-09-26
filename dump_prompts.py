import json

with open('all_user_prompts.txt', 'w', encoding='utf-8') as out:
    with open(r'C:\Users\Shubham Yadav\.gemini\antigravity\brain\0da3836f-79b4-4d21-b474-6e1d98277a9c\.system_generated\logs\transcript_full.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            if data['source'] == 'USER_EXPLICIT':
                out.write(f"====== STEP {data['step_index']} ======\n")
                out.write(data.get('content', '') + '\n')

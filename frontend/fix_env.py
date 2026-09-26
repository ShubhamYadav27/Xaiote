import codecs
content = '''# Xaiote Frontend Environment Variables
# Copy to .env.local for local development

# Backend API base URL
# Local: http://localhost:8000/api/v1
# Production: https://api.xaiote.com/api/v1
NEXT_PUBLIC_API_URL=https://api.xaiote.com/api/v1
'''
with codecs.open('.env.local.example', 'w', 'utf-8') as f:
    f.write(content)
with codecs.open('.env.local', 'w', 'utf-8') as f:
    f.write(content)

import re

with open('src/app/(dashboard)/layout.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Sidebar header
content = content.replace(
    '<div className="relative flex items-center justify-center py-6 px-4 border-b border-white/10 min-h-[72px]">',
    '<div className="relative flex items-center justify-center h-24 px-4 border-b border-white/10 shrink-0">'
)

# Main top header
content = content.replace(
    '<header className="h-16 flex items-center justify-between px-4 lg:px-8 border-b border-white/10 bg-[#080f23]/60 backdrop-blur-md">',
    '<header className="h-24 flex items-center justify-between px-4 lg:px-8 border-b border-white/10 bg-[#080f23]/60 backdrop-blur-md shrink-0">'
)

with open('src/app/(dashboard)/layout.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

import codecs
with codecs.open('src/app/(dashboard)/layout.tsx', 'r', 'utf-8') as f:
    content = f.read()

old_header = '<div className="relative flex items-center justify-center py-6 px-4 border-b border-white/10 min-h-[72px]">'
new_header = '<div className="relative flex items-center justify-center h-16 px-4 border-b border-white/10 shrink-0">'

content = content.replace(old_header, new_header)

with codecs.open('src/app/(dashboard)/layout.tsx', 'w', 'utf-8') as f:
    f.write(content)

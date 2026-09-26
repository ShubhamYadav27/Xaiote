import re

with open('src/app/(dashboard)/layout.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(
    r"title:\s*'Home',\s*items:\s*\[",
    "title: '',\n      items: [",
    content
)

content = re.sub(
    r'\{navSections\.map\(\(section\)\s*=>\s*\(\s*<div key=\{section\.title\}>\s*<p className="px-3 mb-2 text-\[10px\] font-bold text-slate-500 uppercase tracking-widest">\s*\{section\.title\}\s*</p>\s*<div className="space-y-1">',
    r'''{navSections.map((section, index) => (
            <div key={section.title || index}>
              {section.title && (
                <p className="px-3 mb-2 text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                  {section.title}
                </p>
              )}
              <div className="space-y-1">''',
    content
)

with open('src/app/(dashboard)/layout.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

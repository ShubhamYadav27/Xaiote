import re

with open('src/app/(dashboard)/layout.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Change the title for the first section to empty string
content = content.replace("title: 'Home',\n      items: [", "title: '',\n      items: [")

# Conditionally render the p tag, and update the key since title might be empty
old_render = '''{navSections.map((section) => (
              <div key={section.title}>
                <p className="px-3 mb-2 text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                  {section.title}
                </p>
                <div className="space-y-1">'''

new_render = '''{navSections.map((section, index) => (
              <div key={section.title || index}>
                {section.title && (
                  <p className="px-3 mb-2 text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                    {section.title}
                  </p>
                )}
                <div className="space-y-1">'''

content = content.replace(old_render, new_render)

with open('src/app/(dashboard)/layout.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

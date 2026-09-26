import codecs
with codecs.open('src/app/(dashboard)/layout.tsx', 'r', 'utf-8') as f:
    content = f.read()

old_block = '''{navSections.map((section) => (
            <div key={section.title}>
              <p className="px-3 mb-2 text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                {section.title}
              </p>
              <div className="space-y-1">'''

new_block = '''{navSections.map((section, index) => (
            <div key={section.title || index}>
              {section.title && (
                <p className="px-3 mb-2 text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                  {section.title}
                </p>
              )}
              <div className="space-y-1">'''

content = content.replace(old_block, new_block)

with codecs.open('src/app/(dashboard)/layout.tsx', 'w', 'utf-8') as f:
    f.write(content)

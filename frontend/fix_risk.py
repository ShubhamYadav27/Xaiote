import codecs
file_path = 'src/app/(dashboard)/overview/page.tsx'
with codecs.open(file_path, 'r', 'utf-8') as f:
    content = f.read()

content = content.replace(
    '<h2 className="text-3xl font-bold text-white">0</h2>',
    '<h2 className="text-xl font-bold text-slate-500">N/A</h2>'
)
content = content.replace(
    '<span className="text-xs font-medium text-slate-500">None detected</span>',
    '<span className="text-xs font-medium text-slate-600">Awaiting ML Engine</span>'
)
content = content.replace(
    '<p className="text-sm font-medium text-slate-300">All Systems Nominal</p>',
    '<p className="text-sm font-medium text-slate-400">Risk Data Unavailable</p>'
)
content = content.replace(
    '<p className="text-xs text-slate-500 mt-1">No critical risks detected.</p>',
    '<p className="text-xs text-slate-600 mt-1">Production risk engine is not yet connected.</p>'
)
# change green to slate for the empty state UI
content = content.replace('bg-[var(--color-x-green)]/10 border border-[var(--color-x-green)]/20', 'bg-slate-800/50 border border-slate-700')
content = content.replace('bg-[var(--color-x-green)] shadow-[0_0_10px_var(--color-x-green)]', 'bg-slate-500')

with codecs.open(file_path, 'w', 'utf-8') as f:
    f.write(content)

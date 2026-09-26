import re

with open('src/app/(dashboard)/layout.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

old_header = '''<div className="flex items-center justify-between p-6 border-b border-white/10">
          <Link href="/overview" className="flex items-center gap-2">
            <Image
              src="/Logo(icon).png"
              alt="Xaiote"
              width={100}
              height={32}
              className="h-4 w-auto drop-shadow-lg"
            />
          </Link>
          <button
            className="lg:hidden text-slate-400 hover:text-white transition-colors p-1"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="h-5 w-5" />
          </button>
        </div>'''

new_header = '''<div className="relative flex items-center justify-center py-6 px-4 border-b border-white/10 min-h-[72px]">
          <Link href="/overview" className="flex items-center justify-center">
            <Image
              src="/Logo(icon).png"
              alt="Xaiote"
              width={140}
              height={44}
              className="h-6 w-auto drop-shadow-lg"
              priority
            />
          </Link>
          <button
            className="absolute right-4 lg:hidden text-slate-400 hover:text-white transition-colors p-1"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="h-5 w-5" />
          </button>
        </div>'''

content = content.replace(old_header, new_header)

with open('src/app/(dashboard)/layout.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

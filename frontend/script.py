import re

content = open('src/components/marketing/navbar.tsx').read()
content = content.replace('import { useState } from "react";', 'import { useState } from "react";\nimport { useAuth } from "@/components/providers/AuthProvider";')

content = content.replace('const [isOpen, setIsOpen] = useState(false);', 'const [isOpen, setIsOpen] = useState(false);\n  const { user, loading } = useAuth();')

desktop_search = '''            <Link 
              href="/login" 
              className="text-sm font-semibold text-white bg-transparent border border-white/20 rounded-lg px-3.5 py-1.5 hover:bg-slate-800 transition-colors"
            >
              Sign In
            </Link>'''

desktop_replace = '''            {loading ? (
              <div className="w-[71px] h-[34px] border border-transparent"></div>
            ) : user ? (
              <Link 
                href="/overview" 
                className="text-sm font-semibold text-white bg-transparent border border-white/20 rounded-lg px-3.5 py-1.5 hover:bg-slate-800 transition-colors"
              >
                Dashboard
              </Link>
            ) : (
              <Link 
                href="/login" 
                className="text-sm font-semibold text-white bg-transparent border border-white/20 rounded-lg px-3.5 py-1.5 hover:bg-slate-800 transition-colors"
              >
                Sign In
              </Link>
            )}'''

content = content.replace(desktop_search, desktop_replace)

mobile_search = '''<Link href="/login" className="text-base font-semibold text-white border border-white/20 rounded-lg px-4 py-2 text-center hover:bg-slate-800 transition-colors">Sign In</Link>'''

mobile_replace = '''            {loading ? (
              <div className="h-[42px] border border-transparent"></div>
            ) : user ? (
              <Link href="/overview" className="text-base font-semibold text-white border border-white/20 rounded-lg px-4 py-2 text-center hover:bg-slate-800 transition-colors">Dashboard</Link>
            ) : (
              <Link href="/login" className="text-base font-semibold text-white border border-white/20 rounded-lg px-4 py-2 text-center hover:bg-slate-800 transition-colors">Sign In</Link>
            )}'''

content = content.replace(mobile_search, mobile_replace)

open('src/components/marketing/navbar.tsx', 'w').write(content)

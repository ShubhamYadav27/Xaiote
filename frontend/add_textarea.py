import re

with open('src/components/marketing/PilotModal.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# The injection target is just before the submit button wrapper: <div className="pt-2">
textarea_code = '''
            <div>
              <label htmlFor="challenge" className="block text-sm font-medium text-slate-300 mb-1.5">Primary production challenge</label>
              <textarea id="challenge" rows={3} className="w-full px-4 py-2.5 bg-slate-900/50 border border-white/10 text-white rounded-lg focus:ring-1 focus:ring-[var(--color-x-teal)] focus:border-[var(--color-x-teal)] outline-none transition-all placeholder-slate-600 resize-y" placeholder="Tell us about your primary production challenge"></textarea>
            </div>
            
            <div className="pt-2">'''

content = content.replace('<div className="pt-2">', textarea_code)

with open('src/components/marketing/PilotModal.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

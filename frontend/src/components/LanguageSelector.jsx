export default function LanguageSelector({ language, onChange }) {
  const languages = [
    { code: 'kn', label: 'ಕನ್ನಡ' },
    { code: 'hi', label: 'हिन्दी' },
    { code: 'en', label: 'English' },
  ]

  return (
    <div className="flex bg-forest-900/60 rounded-full p-1 text-xs backdrop-blur-xs">
      {languages.map((l) => (
        <button
          key={l.code}
          onClick={() => onChange(l.code)}
          className={`px-3 py-1 rounded-full font-bold transition-all ${
            language === l.code
              ? 'bg-turmeric-400 text-forest-950 shadow-sm'
              : 'text-paddy-100/70 hover:text-white'
          }`}
        >
          {l.label}
        </button>
      ))}
    </div>
  )
}

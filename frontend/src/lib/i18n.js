import en from '../locales/en.json'
import hi from '../locales/hi.json'
import kn from '../locales/kn.json'

export const LOCALES = { en, hi, kn }

export const LANGUAGES = [
  { code: 'kn', label: 'ಕನ್ನಡ', speech: 'kn-IN' },
  { code: 'hi', label: 'हिन्दी', speech: 'hi-IN' },
  { code: 'en', label: 'English', speech: 'en-IN' },
]

export function t(lang, key) {
  const dict = LOCALES[lang] || LOCALES.kn
  return dict[key] ?? LOCALES.en[key] ?? key
}

// speechVoices.js — Finds an installed browser/OS voice matching a given
// BCP-47 language code (e.g. "hi-IN", "kn-IN"). Browsers load voices
// asynchronously, and if no voice matches, they silently fall back to a
// default voice (usually English) instead of erroring — this helper makes
// that failure visible instead of silent.

let cachedVoices = []

function loadVoicesOnce() {
  return new Promise((resolve) => {
    const existing = window.speechSynthesis?.getVoices() || []
    if (existing.length > 0) {
      cachedVoices = existing
      resolve(existing)
      return
    }
    // Voices often aren't ready on first call — wait for the event, with a timeout fallback.
    const handler = () => {
      cachedVoices = window.speechSynthesis.getVoices()
      window.speechSynthesis.removeEventListener('voiceschanged', handler)
      resolve(cachedVoices)
    }
    window.speechSynthesis?.addEventListener('voiceschanged', handler)
    setTimeout(() => {
      cachedVoices = window.speechSynthesis?.getVoices() || []
      resolve(cachedVoices)
    }, 1000)
  })
}

/**
 * Returns { voice, exactMatch } where `voice` is the best available
 * SpeechSynthesisVoice for the requested language, or null if the browser
 * has no voice at all in that language family (e.g. no Kannada voice
 * installed anywhere on the system).
 */
export async function findVoiceForLanguage(bcp47) {
  const voices = await loadVoicesOnce()
  const target = bcp47.toLowerCase().replace('_', '-')
  const targetPrefix = target.split('-')[0] // "hi-IN" -> "hi"

  const exact = voices.find((v) => v.lang.toLowerCase().replace('_', '-') === target)
  if (exact) return { voice: exact, exactMatch: true }

  const sameLanguage = voices.find((v) => v.lang.toLowerCase().startsWith(targetPrefix))
  if (sameLanguage) return { voice: sameLanguage, exactMatch: true }

  return { voice: null, exactMatch: false }
}

export async function listAllVoices() {
  return loadVoicesOnce()
}
import { useState, useEffect, useRef } from 'react'
import { Volume2, VolumeX, Mic, MicOff, MessageSquare } from 'lucide-react'
import { t } from '../lib/i18n'
import { voiceQuery } from '../lib/api'

export default function VoiceAssistant({ advisoryText, diseaseContext, language, autoPlay = false }) {
  const [speaking, setSpeaking] = useState(false)
  const [supported, setSupported] = useState(false)
  const [listening, setListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [voiceReply, setVoiceReply] = useState(null)
  const [loading, setLoading] = useState(false)
  const recognitionRef = useRef(null)

  useEffect(() => {
    setSupported('speechSynthesis' in window)
    // Pre-load voices for browser
    if ('speechSynthesis' in window) {
      window.speechSynthesis.getVoices()
    }
    return () => {
      if ('speechSynthesis' in window) window.speechSynthesis.cancel()
    }
  }, [])

  useEffect(() => {
    if (autoPlay && supported && advisoryText) {
      speakText(advisoryText)
    }
  }, [advisoryText, language])

  const speakText = async (text) => {
    if (!('speechSynthesis' in window) || !text) return

    window.speechSynthesis.cancel()

    // Ensure voices are loaded asynchronously in Chrome/Edge
    let voices = window.speechSynthesis.getVoices()
    if (!voices || voices.length === 0) {
      await new Promise((resolve) => {
        const handler = () => {
          voices = window.speechSynthesis.getVoices()
          window.speechSynthesis.removeEventListener('voiceschanged', handler)
          resolve()
        }
        window.speechSynthesis.addEventListener('voiceschanged', handler)
        setTimeout(resolve, 300)
      })
      voices = window.speechSynthesis.getVoices() || []
    }

    const langMap = { kn: 'kn-IN', hi: 'hi-IN', en: 'en-IN' }
    const targetLangCode = langMap[language] || 'en-IN'
    const targetPrefix = language

    const u = new SpeechSynthesisUtterance(text)
    u.lang = targetLangCode
    u.rate = 0.95
    u.pitch = 1.0

    // Pick best native Indic voice (Hindi / Kannada / English)
    if (voices.length > 0) {
      // 1. Exact match (e.g. 'hi-IN' or 'hi_IN')
      let match = voices.find(
        (v) => v.lang.toLowerCase().replace('_', '-') === targetLangCode.toLowerCase()
      )
      // 2. Prefix match (e.g. 'hi', 'kn')
      if (!match) {
        match = voices.find((v) => v.lang.toLowerCase().startsWith(targetPrefix))
      }
      // 3. Name match (e.g. 'Hindi', 'Kannada', 'Swara', 'Hemant', 'Google')
      if (!match) {
        const nameQuery = language === 'hi' ? 'hindi' : language === 'kn' ? 'kannada' : 'english'
        match = voices.find((v) => v.name.toLowerCase().includes(nameQuery))
      }
      if (match) {
        u.voice = match
      }
    }

    u.onstart = () => setSpeaking(true)
    u.onend = () => setSpeaking(false)
    u.onerror = () => setSpeaking(false)

    if (window.speechSynthesis.paused) {
      window.speechSynthesis.resume()
    }

    setTimeout(() => {
      window.speechSynthesis.speak(u)
    }, 60)
  }

  const stopSpeaking = () => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel()
      setSpeaking(false)
    }
  }

  const handleToggleListen = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      alert('Speech recognition is supported in Google Chrome or Microsoft Edge.')
      return
    }

    if (listening) {
      recognitionRef.current?.stop()
      setListening(false)
      return
    }

    const recognition = new SpeechRecognition()
    recognitionRef.current = recognition
    const langMap = { kn: 'kn-IN', hi: 'hi-IN', en: 'en-IN' }
    recognition.lang = langMap[language] || 'en-IN'
    recognition.interimResults = false

    recognition.onstart = () => setListening(true)
    recognition.onend = () => setListening(false)
    recognition.onerror = () => setListening(false)

    recognition.onresult = async (e) => {
      const text = e.results[0][0].transcript
      setTranscript(text)
      setLoading(true)
      try {
        const res = await voiceQuery({
          transcript: text,
          sourceLanguage: language,
          targetLanguage: language,
          contextDisease: diseaseContext,
        })
        const reply = res.reply_text || res.reply || ''
        setVoiceReply(reply)
        if (reply) speakText(reply)
      } catch (err) {
        console.warn('Voice query error:', err)
      } finally {
        setLoading(false)
      }
    }

    recognition.start()
  }

  const handleChipClick = async (prompt) => {
    setTranscript(prompt)
    setLoading(true)
    try {
      const res = await voiceQuery({
        transcript: prompt,
        sourceLanguage: language,
        targetLanguage: language,
        contextDisease: diseaseContext,
      })
      const reply = res.reply_text || res.reply || ''
      setVoiceReply(reply)
      if (reply) speakText(reply)
    } catch (err) {
      console.warn('Voice chip error:', err)
    } finally {
      setLoading(false)
    }
  }

  const quickPrompts = [
    { key: 'chip_treatment', text: t(language, 'chip_treatment') },
    { key: 'chip_organic', text: t(language, 'chip_organic') },
    { key: 'chip_prevention', text: t(language, 'chip_prevention') },
  ]

  return (
    <div className="rounded-2xl bg-white shadow-card border border-paddy-200 p-4 animate-riseIn no-print">
      <div className="flex items-center justify-between gap-2 mb-3">
        <h3 className="font-display font-semibold text-forest-800 text-sm flex items-center gap-1.5">
          <MessageSquare size={16} className="text-turmeric-500" />
          {t(language, 'voice_assistant_title')}
        </h3>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={speaking ? stopSpeaking : () => speakText(voiceReply || advisoryText)}
          className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-xl text-sm font-bold transition-all shadow-sm cursor-pointer ${
            speaking ? 'bg-turmeric-500 text-forest-950' : 'bg-forest-600 hover:bg-forest-700 text-white'
          }`}
        >
          {speaking ? <VolumeX size={18} /> : <Volume2 size={18} />}
          <span>{speaking ? t(language, 'stop') : t(language, 'listen')}</span>
        </button>

        <button
          onClick={handleToggleListen}
          className={`p-3 rounded-xl border transition-all cursor-pointer ${
            listening
              ? 'bg-laterite-500 text-white border-laterite-600 animate-pulse'
              : 'bg-paddy-100 hover:bg-paddy-200 border-paddy-200 text-forest-700'
          }`}
          title={t(language, 'ask_question')}
        >
          {listening ? <MicOff size={18} /> : <Mic size={18} />}
        </button>
      </div>

      {/* Quick Prompts */}
      <div className="mt-3 pt-3 border-t border-paddy-100">
        <p className="text-[11px] text-forest-500/70 font-semibold mb-1.5">{t(language, 'voice_quick_prompt')}</p>
        <div className="flex flex-wrap gap-1.5">
          {quickPrompts.map((p) => (
            <button
              key={p.key}
              onClick={() => handleChipClick(p.text)}
              disabled={loading}
              className="text-xs bg-paddy-50 hover:bg-paddy-100 text-forest-700 px-2.5 py-1 rounded-full border border-paddy-200 transition-colors cursor-pointer"
            >
              {p.text}
            </button>
          ))}
        </div>
      </div>

      {(transcript || voiceReply || loading) && (
        <div className="mt-3 p-3.5 rounded-xl bg-paddy-50/80 border border-paddy-100 text-xs space-y-2">
          {transcript && (
            <p className="text-forest-700 italic">
              <b>Q:</b> {transcript}
            </p>
          )}
          {loading && <p className="text-forest-500 font-medium">Thinking...</p>}
          {voiceReply && !loading && (
            <p className="text-forest-900 font-medium bg-white p-3 rounded-lg border border-paddy-200 leading-relaxed whitespace-pre-line">
              {voiceReply}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

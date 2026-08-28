import { useEffect, useState, useRef } from 'react'
import { Sprout, AlertCircle } from 'lucide-react'
import CameraCapture from './components/CameraCapture'
import WeatherWidget from './components/WeatherWidget'
import HeatmapViewer from './components/HeatmapViewer'
import AdvisoryCard from './components/AdvisoryCard'
import VoiceAssistant from './components/VoiceAssistant'
import LanguageSelector from './components/LanguageSelector'
import { t } from './lib/i18n'
import { analyzeCrop, fetchWeatherContext } from './lib/api'

export default function App() {
  const [language, setLanguage] = useState('kn')
  const [previewUrl, setPreviewUrl] = useState(null)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [ambientWeather, setAmbientWeather] = useState(null)
  const [coords, setCoords] = useState(null)
  const currentFileRef = useRef(null)

  // Try to get GPS location once (falls back to Bangalore default server-side)
  useEffect(() => {
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => setCoords({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
        () => setCoords(null),
        { timeout: 4000 }
      )
    }
  }, [])

  // Pre-load ambient weather strip before any scan happens
  useEffect(() => {
    fetchWeatherContext(coords ? { lat: coords.lat, lon: coords.lon } : {})
      .then((res) => setAmbientWeather(res.weather))
      .catch(() => {})
  }, [coords])

  const runAnalysis = async (file, targetLang) => {
    setError(null)
    setBusy(true)
    try {
      const res = await analyzeCrop({
        file,
        lat: coords?.lat,
        lon: coords?.lon,
        language: targetLang,
      })
      setResult(res)
    } catch (e) {
      setError(e.message || t(targetLang, 'error_generic'))
    } finally {
      setBusy(false)
    }
  }

  const handleFileSelected = (file) => {
    setError(null)
    setResult(null)
    currentFileRef.current = file
    const url = URL.createObjectURL(file)
    setPreviewUrl(url)
    runAnalysis(file, language)
  }

  const handleLanguageChange = (newLang) => {
    setLanguage(newLang)
    if (currentFileRef.current) {
      runAnalysis(currentFileRef.current, newLang)
    }
  }

  const handleReset = () => {
    currentFileRef.current = null
    setPreviewUrl(null)
    setResult(null)
    setError(null)
  }

  return (
    <div className="min-h-full flex flex-col">
      {/* Header */}
      <header className="bg-forest-700 text-white px-4 pt-5 pb-6 rounded-b-[2rem] shadow-leaf">
        <div className="max-w-md mx-auto flex items-start justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="w-11 h-11 rounded-2xl bg-turmeric-400 flex items-center justify-center shrink-0 shadow-sm">
              <Sprout size={24} className="text-forest-900" />
            </div>
            <div>
              <h1 className="font-display font-extrabold text-lg leading-tight">{t(language, 'app_title')}</h1>
              <p className="text-xs text-paddy-100/75">{t(language, 'app_tagline')}</p>
            </div>
          </div>
          <LanguageSelector language={language} onChange={handleLanguageChange} />
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 max-w-md w-full mx-auto px-4 -mt-3 pb-10 flex flex-col gap-4">
        {/* Weather Strip */}
        <WeatherWidget
          weather={result?.weather || ambientWeather}
          language={language}
          compact={Boolean(result)}
        />

        {/* Camera / Upload card */}
        <div className="rounded-2xl bg-white shadow-card border border-paddy-200 p-4">
          <CameraCapture
            language={language}
            previewUrl={previewUrl}
            onFileSelected={handleFileSelected}
            onReset={handleReset}
            busy={busy}
          />
        </div>

        {/* Error notification */}
        {error && (
          <div className="flex items-start gap-2 rounded-2xl bg-laterite-500/15 border border-laterite-500/30 p-3 text-xs text-laterite-600 animate-riseIn">
            <AlertCircle size={16} className="shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {/* Diagnosis & Advisory Section */}
        {result && (
          <>
            <HeatmapViewer
              originalUrl={previewUrl}
              heatmapUrl={result.gradcam_image_base64?.startsWith('data:') ? result.gradcam_image_base64 : (result.gradcam_image_base64 ? `data:image/png;base64,${result.gradcam_image_base64}` : null)}
              language={language}
            />
            <AdvisoryCard
              advisory={result.advisory}
              classification={result.classification}
              risk={result.environmental_risk || result.risk}
              weather={result.weather || ambientWeather}
              originalUrl={previewUrl}
              heatmapUrl={result.gradcam_image_base64?.startsWith('data:') ? result.gradcam_image_base64 : (result.gradcam_image_base64 ? `data:image/png;base64,${result.gradcam_image_base64}` : null)}
              language={language}
            />
            <VoiceAssistant
              advisoryText={result.voice_summary_text || result.audio_advisory_text || (result.advisory ? `${result.advisory.disease_name}. ${result.advisory.root_cause}. ${result.advisory.treatment_organic}. ${result.advisory.treatment_chemical}` : '')}
              diseaseContext={result.classification?.class_id || result.classification?.predicted_class}
              language={language}
              autoPlay={false}
            />
          </>
        )}
      </main>

      <footer className="text-center text-[11px] text-forest-500/60 pb-6 px-4">
        <p>{t(language, 'footer_note')}</p>
      </footer>
    </div>
  )
}

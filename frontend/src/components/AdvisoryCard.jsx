import { useState } from 'react'
import { 
  Leaf, 
  FlaskConical, 
  ShieldCheck, 
  AlertTriangle, 
  ChevronDown, 
  Printer, 
  Share2
} from 'lucide-react'
import { t } from '../lib/i18n'

const SEVERITY_STYLE = {
  Healthy: { bg: 'bg-emerald-600', text: 'text-white', key: 'severity_healthy' },
  Moderate: { bg: 'bg-amber-500', text: 'text-white', key: 'severity_moderate' },
  Critical: { bg: 'bg-rose-600', text: 'text-white', key: 'severity_critical' },
}

const RISK_CONFIG = {
  Low: { bg: 'bg-emerald-600', text: 'text-white', key: 'risk_low' },
  Moderate: { bg: 'bg-amber-500', text: 'text-white', key: 'risk_moderate' },
  High: { bg: 'bg-orange-600', text: 'text-white', key: 'risk_high' },
  Critical: { bg: 'bg-rose-600', text: 'text-white', key: 'risk_critical' },
}

export default function AdvisoryCard({ 
  advisory, 
  classification, 
  risk, 
  weather, 
  originalUrl, 
  heatmapUrl, 
  language 
}) {
  const [tab, setTab] = useState('organic')
  const sev = SEVERITY_STYLE[advisory.severity] || SEVERITY_STYLE.Moderate
  const confidencePct = Math.round(classification.confidence * 100)

  const tabs = [
    { key: 'organic', label: t(language, 'advisory_organic') || 'Organic Remedy', icon: Leaf, content: advisory.treatment_organic },
    { key: 'chemical', label: t(language, 'advisory_chemical') || 'Chemical Dosage', icon: FlaskConical, content: advisory.treatment_chemical },
    { key: 'prevention', label: t(language, 'advisory_prevention') || 'Prevention', icon: ShieldCheck, content: null },
  ]
  const activeTab = tabs.find((x) => x.key === tab)

  const riskLevelKey = risk?.risk_level || 'Moderate'
  const riskMeta = RISK_CONFIG[riskLevelKey] || RISK_CONFIG.Moderate
  const localizedRiskLevel = t(language, riskMeta.key) || riskLevelKey

  // Print Report Action
  const handlePrint = () => {
    window.print()
  }

  // WhatsApp Share Action
  const handleWhatsAppShare = () => {
    const title = t(language, 'app_title') || 'Smart Crop Advisory'
    const diseaseLabel = t(language, 'diagnosis') || 'Disease'
    const confLabel = t(language, 'confidence') || 'Confidence'
    const organicLabel = t(language, 'advisory_organic') || 'Organic Remedy'
    const chemicalLabel = t(language, 'advisory_chemical') || 'Chemical Dosage'
    const riskLabel = t(language, 'risk_title') || 'Weather Risk'

    const textLines = [
      `🌾 *${title}* — ${t(language, 'report_title') || 'Crop Advisory'}`,
      `━━━━━━━━━━━━━━━━━━`,
      `🌱 *${diseaseLabel}:* ${advisory.disease_name}`,
      advisory.scientific_name !== 'N/A' ? `🔬 *Pathogen:* ${advisory.scientific_name}` : '',
      `🎯 *${confLabel}:* ${confidencePct}% | *Severity:* ${advisory.severity}`,
      risk ? `🌦️ *${riskLabel}:* ${localizedRiskLevel} (${Math.round(risk.risk_score || 0)}/100)` : '',
      ``,
      `📋 *${t(language, 'advisory_root_cause') || 'Cause'}:*`,
      `${advisory.root_cause}`,
      ``,
      `🌿 *${organicLabel}:*`,
      `${advisory.treatment_organic}`,
      ``,
      `🧪 *${chemicalLabel}:*`,
      `${advisory.treatment_chemical}`,
      ``,
      `━━━━━━━━━━━━━━━━━━`,
      `📍 ${weather?.location_name || 'Farm Field'} · ${new Date().toLocaleDateString()}`,
      `Department of CSE, Sir MVIT`,
    ].filter(Boolean)

    const fullMessage = encodeURIComponent(textLines.join('\n'))
    window.open(`https://api.whatsapp.com/send?text=${fullMessage}`, '_blank')
  }

  return (
    <>
      {/* 1. Interactive Web Card View */}
      <div className="rounded-2xl bg-white shadow-card border border-paddy-200 overflow-hidden animate-riseIn">
        {/* Header & Disease Title */}
        <div className="p-4 pb-3">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-bold text-forest-600 uppercase tracking-wide">{t(language, 'diagnosis')}</p>
              <h2 className="font-bold text-xl text-forest-900 leading-snug mt-0.5">{advisory.disease_name}</h2>
              {advisory.scientific_name && advisory.scientific_name !== 'N/A' && (
                <p className="text-xs italic text-forest-600/70 mt-0.5">{t(language, 'scientific_name')}: {advisory.scientific_name}</p>
              )}
            </div>
            <span className={`shrink-0 rounded-full px-3.5 py-1 text-xs font-bold ${sev.bg} ${sev.text} shadow-sm`}>
              {t(language, sev.key) || advisory.severity}
            </span>
          </div>

          {/* Neural Confidence Progress Bar */}
          <div className="flex items-center gap-2 mt-3">
            <div className="flex-1 h-2 rounded-full bg-paddy-100 overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-turmeric-400 to-forest-500 transition-all duration-500"
                style={{ width: `${confidencePct}%` }}
              />
            </div>
            <span className="font-mono text-xs font-semibold text-forest-600 w-24 text-right">
              {confidencePct}% {t(language, 'confidence')}
            </span>
          </div>
        </div>

        {/* Environmental Risk Banner */}
        {risk && (
          <div className="mx-4 mb-3 rounded-xl bg-paddy-50 p-3.5 border border-paddy-200/60">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle size={17} className="text-amber-600 shrink-0" />
                <span className="text-xs sm:text-sm font-bold text-forest-900">{t(language, 'risk_title') || 'Weather Disease Spread Risk'}</span>
              </div>
              <span className={`text-xs font-bold px-3 py-1 rounded-full ${riskMeta.bg} ${riskMeta.text} shadow-sm shrink-0`}>
                {localizedRiskLevel} · {Math.round(risk.risk_score || 0)}/100
              </span>
            </div>
            <RiskDetails language={language} risk={risk} />
          </div>
        )}

        {/* Root cause / Description */}
        <div className="px-4 pb-2">
          <p className="text-xs font-bold text-forest-700 uppercase tracking-wide mb-1">{t(language, 'advisory_root_cause')}</p>
          <p className="text-sm text-forest-800 leading-relaxed bg-paddy-50/60 p-3 rounded-xl border border-paddy-100">{advisory.root_cause}</p>
        </div>

        {/* 3 Clean Treatment Tabs */}
        {advisory.severity !== 'Healthy' && (
          <div className="px-4 pb-4">
            <div className="flex gap-1.5 rounded-xl bg-forest-50 p-1 mt-2 border border-forest-100">
              {tabs.map((tb) => {
                const isActive = tab === tb.key
                return (
                  <button
                    key={tb.key}
                    onClick={() => setTab(tb.key)}
                    className={`flex-1 flex items-center justify-center gap-1.5 py-2 px-2 rounded-lg text-xs font-bold transition-all ${
                      isActive
                        ? 'bg-forest-700 text-white shadow-sm'
                        : 'text-forest-700 hover:text-forest-900 hover:bg-forest-100/70'
                    }`}
                  >
                    <tb.icon size={14} className="shrink-0" />
                    <span className="truncate">{tb.label}</span>
                  </button>
                )
              })}
            </div>

            <div className="mt-3 text-sm text-forest-800 bg-white p-3.5 rounded-xl border border-forest-100 shadow-sm">
              {activeTab?.key === 'prevention' ? (
                <ul className="space-y-1.5">
                  {(advisory.preventive_measures || []).map((step, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-forest-600 font-bold text-xs mt-0.5">•</span>
                      <span className="leading-relaxed">{step}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="whitespace-pre-line leading-relaxed">{activeTab?.content}</p>
              )}
            </div>
          </div>
        )}

        {/* Action Toolbar: Print / Save Report & WhatsApp Share */}
        <div className="p-3.5 bg-forest-50/60 border-t border-forest-100 flex items-center gap-2.5 no-print">
          <button
            onClick={handlePrint}
            className="flex-1 flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl bg-forest-700 hover:bg-forest-800 text-white text-xs font-bold shadow-sm transition-all active:scale-95 cursor-pointer"
          >
            <Printer size={15} />
            <span>{t(language, 'download_report') || 'Print / Save PDF'}</span>
          </button>

          <button
            onClick={handleWhatsAppShare}
            className="flex-1 flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl bg-[#25D366] hover:bg-[#20bd5a] text-white text-xs font-bold shadow-sm transition-all active:scale-95 cursor-pointer"
          >
            <Share2 size={15} />
            <span>{t(language, 'share_whatsapp') || 'Share on WhatsApp'}</span>
          </button>
        </div>
      </div>

      {/* 2. Official Printable Crop Doctor Health Card (Only visible during window.print()) */}
      <div className="hidden print:block p-6 max-w-2xl mx-auto border-2 border-forest-800 rounded-2xl bg-white text-slate-900 font-sans">
        {/* Printable Header */}
        <div className="flex items-center justify-between border-b-2 border-forest-800 pb-4 mb-4">
          <div>
            <h1 className="text-2xl font-black text-forest-900 tracking-tight">Smart Crop Advisory System</h1>
            <p className="text-xs font-bold text-forest-700 uppercase">Crop Doctor Health Prescription · AgroVoice-XAI</p>
            <p className="text-[10px] text-slate-500 mt-0.5">Dept. of Computer Science &amp; Engineering, Sir MVIT, Bengaluru</p>
          </div>
          <div className="text-right text-xs text-slate-600">
            <p><strong>Date:</strong> {new Date().toLocaleDateString()}</p>
            <p><strong>Location:</strong> {weather?.location_name || 'Bengaluru, Karnataka'}</p>
            <p><strong>Weather:</strong> {weather?.temperature_c?.toFixed(1)}°C · {Math.round(weather?.humidity_pct || 0)}% RH</p>
          </div>
        </div>

        {/* Diagnosis & Visual Inspection Strip */}
        <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 mb-4 flex items-center justify-between">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Diagnosis Report</span>
            <h2 className="text-xl font-extrabold text-slate-900">{advisory.disease_name}</h2>
            {advisory.scientific_name !== 'N/A' && (
              <p className="text-xs italic text-slate-600">Pathogen: {advisory.scientific_name}</p>
            )}
          </div>
          <div className="text-right">
            <span className="px-3 py-1 rounded-full text-xs font-bold bg-forest-100 text-forest-900 border border-forest-300">
              Certainty: {confidencePct}%
            </span>
            {risk && (
              <p className="text-xs font-bold text-amber-800 mt-1.5">
                Weather Risk: {localizedRiskLevel} ({Math.round(risk.risk_score || 0)}/100)
              </p>
            )}
          </div>
        </div>

        {/* Photos Grid */}
        {(originalUrl || heatmapUrl) && (
          <div className="grid grid-cols-2 gap-4 mb-4">
            {originalUrl && (
              <div>
                <p className="text-xs font-bold text-slate-700 mb-1">Your Crop Photo:</p>
                <img src={originalUrl} alt="Original Leaf" className="w-full h-44 object-cover rounded-lg border border-slate-300" />
              </div>
            )}
            {heatmapUrl && (
              <div>
                <p className="text-xs font-bold text-amber-800 mb-1">AI Lesion Heatmap (Grad-CAM):</p>
                <img src={heatmapUrl} alt="Grad-CAM Heatmap" className="w-full h-44 object-cover rounded-lg border border-amber-300" />
              </div>
            )}
          </div>
        )}

        {/* Clinical Prescriptions */}
        <div className="space-y-3 text-xs leading-relaxed">
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <h3 className="font-bold text-slate-900 uppercase text-[11px] mb-1">1. Why did this happen? (Cause)</h3>
            <p className="text-slate-700">{advisory.root_cause}</p>
          </div>

          <div className="p-3 bg-emerald-50/50 rounded-lg border border-emerald-200">
            <h3 className="font-bold text-emerald-900 uppercase text-[11px] mb-1">2. Organic &amp; Biological Remedy (ಸಾವಯವ ಮನೆಮದ್ದು)</h3>
            <p className="text-emerald-950 whitespace-pre-line">{advisory.treatment_organic}</p>
          </div>

          <div className="p-3 bg-sky-50/50 rounded-lg border border-sky-200">
            <h3 className="font-bold text-sky-900 uppercase text-[11px] mb-1">3. Medicine Spray &amp; 15L Pump Dosage (ಔಷಧಿ ಸಿಂಪರಣೆ)</h3>
            <p className="text-sky-950 whitespace-pre-line">{advisory.treatment_chemical}</p>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <h3 className="font-bold text-slate-900 uppercase text-[11px] mb-1">4. Preventive Cultural Measures (ಮುನ್ನೆಚ್ಚರಿಕೆ ಕ್ರಮಗಳು)</h3>
            <ul className="list-disc pl-4 space-y-1 text-slate-700">
              {(advisory.preventive_measures || []).map((step, idx) => (
                <li key={idx}>{step}</li>
              ))}
            </ul>
          </div>
        </div>

        {/* Stamp & Footer */}
        <div className="mt-6 pt-4 border-t border-slate-300 flex items-center justify-between text-[10px] text-slate-500">
          <p>✔ Verified by Deep Learning Inference Engine (MobileNetV2 + Grad-CAM + Open-Meteo)</p>
          <p className="font-bold text-slate-700">AgroVoice-XAI · Sir MVIT</p>
        </div>
      </div>
    </>
  )
}

function RiskDetails({ language, risk }) {
  const [open, setOpen] = useState(false)
  if (!risk) return null
  const reasonsList = (risk.triggers && risk.triggers.length > 0) 
    ? risk.triggers 
    : (risk.reasons && risk.reasons.length > 0 ? risk.reasons : [risk.explanation].filter(Boolean))

  if (reasonsList.length === 0) return null

  return (
    <div className="mt-2 text-xs text-forest-600 no-print">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 text-forest-600 hover:text-forest-800 font-semibold cursor-pointer py-0.5"
      >
        <span>{t(language, 'risk_why') || 'Why this risk level?'}</span>
        <ChevronDown size={14} className={`transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <ul className="mt-2 space-y-1.5 pl-2 border-l-2 border-paddy-200">
          {reasonsList.map((r, i) => (
            <li key={i} className="text-forest-700 leading-snug">• {r}</li>
          ))}
        </ul>
      )}
    </div>
  )
}

import { Eye, Sparkles } from 'lucide-react'
import { t } from '../lib/i18n'

export default function HeatmapViewer({ originalUrl, heatmapUrl, language }) {
  if (!originalUrl && !heatmapUrl) return null

  return (
    <div className="rounded-2xl bg-white shadow-card border border-paddy-200 p-4 animate-riseIn">
      <div className="grid grid-cols-2 gap-3">
        <div className="flex flex-col items-center gap-1.5">
          <div className="relative w-full aspect-square rounded-2xl overflow-hidden bg-forest-900/5 shadow-inner border border-paddy-200">
            {originalUrl && (
              <img src={originalUrl} alt={t(language, 'original_photo')} className="w-full h-full object-cover" />
            )}
          </div>
          <span className="flex items-center gap-1 text-xs font-semibold text-forest-600">
            <Eye size={14} />
            {t(language, 'original_photo')}
          </span>
        </div>

        <div className="flex flex-col items-center gap-1.5">
          <div className="relative w-full aspect-square rounded-2xl overflow-hidden bg-forest-900/5 shadow-inner border border-paddy-200">
            {heatmapUrl ? (
              <img src={heatmapUrl} alt={t(language, 'ai_heatmap')} className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-forest-400 text-xs font-mono">
                Grad-CAM
              </div>
            )}
          </div>
          <span className="flex items-center gap-1 text-xs font-semibold text-turmeric-600">
            <Sparkles size={14} />
            {t(language, 'ai_heatmap')}
          </span>
        </div>
      </div>
      <p className="text-[11px] text-forest-500/70 text-center mt-3 font-body">
        {t(language, 'heatmap_hint')}
      </p>
    </div>
  )
}

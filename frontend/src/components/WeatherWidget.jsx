import { Thermometer, Droplets, Wind, CloudRain, MapPin } from 'lucide-react'
import { t } from '../lib/i18n'

export default function WeatherWidget({ weather, language, compact = false }) {
  if (!weather) return null

  const stats = [
    { icon: Thermometer, label: t(language, 'temperature'), value: `${weather.temperature_c.toFixed(1)}°C`, color: 'text-laterite-500' },
    { icon: Droplets, label: t(language, 'humidity'), value: `${Math.round(weather.humidity_pct)}%`, color: 'text-sky-500' },
    { icon: Wind, label: t(language, 'wind'), value: `${Math.round(weather.wind_speed_kmh)} km/h`, color: 'text-forest-500' },
    { icon: CloudRain, label: t(language, 'rain'), value: `${weather.rain_mm.toFixed(1)} mm`, color: 'text-sky-600' },
  ]

  return (
    <div className={`rounded-2xl bg-white shadow-card border border-paddy-200 ${compact ? 'p-3' : 'p-4'}`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-display font-semibold text-forest-700 text-sm tracking-wide flex items-center gap-1.5">
          <MapPin size={16} className="text-turmeric-500" />
          {t(language, 'weather_now')}
        </h3>
        <span className="text-xs text-forest-500/70 font-body">{weather.condition}</span>
      </div>
      <div className="grid grid-cols-4 gap-2">
        {stats.map((s) => (
          <div key={s.label} className="flex flex-col items-center text-center gap-1 rounded-xl bg-paddy-50 py-2.5">
            <s.icon size={18} className={s.color} />
            <span className="font-mono text-sm font-semibold text-forest-800">{s.value}</span>
            <span className="text-[10px] text-forest-500/70 leading-tight">{s.label}</span>
          </div>
        ))}
      </div>
      <p className="text-[11px] text-forest-500/60 mt-2 truncate">{weather.location_name}</p>
    </div>
  )
}

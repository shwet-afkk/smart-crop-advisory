import { useState, useRef, useEffect } from 'react'
import { Camera, ImagePlus, RotateCcw, SwitchCamera, X, AlertCircle, Scan, Zap, ZapOff, Sparkles } from 'lucide-react'
import { t } from '../lib/i18n'

const SAMPLES = [
  { label: 'Tomato Early Blight', file: '/samples/sample_tomato_early_blight.jpg' },
  { label: 'Potato Late Blight', file: '/samples/sample_potato_late_blight.jpg' },
  { label: 'Healthy Pepper', file: '/samples/sample_pepper_healthy.jpg' },
]

export default function CameraCapture({ language, previewUrl, onFileSelected, onReset, busy }) {
  const [isCameraActive, setIsCameraActive] = useState(false)
  const [facingMode, setFacingMode] = useState('environment')
  const [torchAvailable, setTorchAvailable] = useState(false)
  const [torchOn, setTorchOn] = useState(false)
  const [cameraError, setCameraError] = useState(null)
  const [isFlashing, setIsFlashing] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const streamRef = useRef(null)
  const galleryInputRef = useRef(null)
  const fallbackCameraInputRef = useRef(null)

  useEffect(() => {
    return () => {
      stopCameraStream()
    }
  }, [])

  useEffect(() => {
    if (previewUrl) {
      stopCameraStream()
      setIsCameraActive(false)
    }
  }, [previewUrl])

  const startCamera = async (mode = facingMode) => {
    setCameraError(null)
    stopCameraStream()

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      fallbackCameraInputRef.current?.click()
      return
    }

    try {
      const constraints = {
        video: {
          facingMode: { ideal: mode },
          width: { ideal: 1920, min: 640 },
          height: { ideal: 1080, min: 480 },
        },
        audio: false,
      }
      const stream = await navigator.mediaDevices.getUserMedia(constraints)
      streamRef.current = stream
      setIsCameraActive(true)

      const track = stream.getVideoTracks()[0]
      if (track && track.getCapabilities) {
        const capabilities = track.getCapabilities()
        setTorchAvailable(Boolean(capabilities.torch))
      } else {
        setTorchAvailable(false)
      }

      if (videoRef.current) {
        videoRef.current.srcObject = stream
        videoRef.current.play().catch(() => {})
      }
    } catch (err) {
      console.warn('getUserMedia error:', err)
      setCameraError(t(language, 'camera_permission_denied'))
      setIsCameraActive(false)
      fallbackCameraInputRef.current?.click()
    }
  }

  const stopCameraStream = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop())
      streamRef.current = null
      setTorchOn(false)
    }
  }

  const handleCloseCamera = () => {
    stopCameraStream()
    setIsCameraActive(false)
    setCameraError(null)
  }

  const switchCameraFacing = () => {
    const nextMode = facingMode === 'environment' ? 'user' : 'environment'
    setFacingMode(nextMode)
    startCamera(nextMode)
  }

  const toggleTorch = async () => {
    if (!streamRef.current) return
    const track = streamRef.current.getVideoTracks()[0]
    if (track && track.applyConstraints) {
      try {
        const nextState = !torchOn
        await track.applyConstraints({
          advanced: [{ torch: nextState }],
        })
        setTorchOn(nextState)
      } catch (e) {
        console.warn('Torch constraint error:', e)
      }
    }
  }

  const capturePhoto = () => {
    if (!videoRef.current || !canvasRef.current) return
    const video = videoRef.current
    const canvas = canvasRef.current

    setIsFlashing(true)
    setTimeout(() => setIsFlashing(false), 200)

    canvas.width = video.videoWidth || 1280
    canvas.height = video.videoHeight || 720
    const ctx = canvas.getContext('2d')
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)

    canvas.toBlob(
      (blob) => {
        if (blob) {
          const file = new File([blob], `leaf_${Date.now()}.jpg`, { type: 'image/jpeg' })
          stopCameraStream()
          setIsCameraActive(false)
          onFileSelected(file)
        }
      },
      'image/jpeg',
      0.95
    )
  }

  const handleFileChange = (e) => {
    const file = e.target.files?.[0]
    if (file) {
      stopCameraStream()
      setIsCameraActive(false)
      onFileSelected(file)
    }
    e.target.value = ''
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files?.[0]
    if (file && file.type.startsWith('image/')) {
      onFileSelected(file)
    }
  }

  const handleSampleClick = async (sample) => {
    try {
      const res = await fetch(sample.file)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const blob = await res.blob()
      const file = new File([blob], sample.label.toLowerCase().replace(/\s+/g, '_') + '.jpg', {
        type: 'image/jpeg',
      })
      stopCameraStream()
      setIsCameraActive(false)
      onFileSelected(file)
    } catch (err) {
      console.warn('Sample image load fallback triggered:', err)
      const canvas = document.createElement('canvas')
      canvas.width = 512
      canvas.height = 512
      const ctx = canvas.getContext('2d')
      ctx.fillStyle = '#f0f5f0'
      ctx.fillRect(0, 0, 512, 512)
      ctx.fillStyle = sample.label.includes('Healthy') ? '#2e8b57' : '#4a7023'
      ctx.beginPath()
      ctx.ellipse(256, 256, 160, 210, 0, 0, Math.PI * 2)
      ctx.fill()
      if (!sample.label.includes('Healthy')) {
        ctx.fillStyle = '#4a2f13'
        ctx.beginPath()
        ctx.arc(220, 200, 30, 0, Math.PI * 2)
        ctx.fill()
        ctx.beginPath()
        ctx.arc(310, 280, 40, 0, Math.PI * 2)
        ctx.fill()
      }
      canvas.toBlob(
        (blob) => {
          if (blob) {
            const file = new File([blob], sample.label.toLowerCase().replace(/\s+/g, '_') + '.jpg', {
              type: 'image/jpeg',
            })
            stopCameraStream()
            setIsCameraActive(false)
            onFileSelected(file)
          }
        },
        'image/jpeg',
        0.92
      )
    }
  }

  // 1. Preview & Analyzing Mode
  if (previewUrl) {
    return (
      <div className="flex flex-col items-center gap-3 animate-riseIn">
        <div className="relative w-full max-w-xs aspect-square rounded-3xl overflow-hidden shadow-leaf border-4 border-white">
          <img src={previewUrl} alt="Captured leaf" className="w-full h-full object-cover" />
          {busy && (
            <div className="absolute inset-0 bg-forest-900/60 backdrop-blur-xs flex flex-col items-center justify-center gap-3 text-white text-center px-4">
              <div className="w-12 h-12 rounded-full border-4 border-white/30 border-t-turmeric-400 animate-spin" />
              <p className="font-display font-bold text-base tracking-wide">{t(language, 'analyzing')}</p>
              <p className="text-xs text-paddy-100/90">{t(language, 'analyzing_sub')}</p>
            </div>
          )}
        </div>
        {!busy && (
          <button
            onClick={() => {
              onReset()
              handleCloseCamera()
            }}
            className="inline-flex items-center gap-2 rounded-full bg-forest-600/10 hover:bg-forest-600/20 text-forest-700 font-bold text-sm px-5 py-2.5 transition-colors active:scale-95 shadow-sm"
          >
            <RotateCcw size={16} />
            {t(language, 'retake')}
          </button>
        )}
      </div>
    )
  }

  // 2. Active Live In-App Camera Viewfinder Mode
  if (isCameraActive) {
    return (
      <div className="w-full max-w-xs flex flex-col items-center gap-3 animate-riseIn mx-auto">
        <div className="relative w-full aspect-square rounded-3xl overflow-hidden shadow-leaf bg-black border-4 border-turmeric-400">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="w-full h-full object-cover"
          />

          {isFlashing && <div className="absolute inset-0 bg-white z-30 transition-opacity duration-200" />}

          {/* Leaf Alignment Viewfinder Overlay */}
          <div className="absolute inset-0 pointer-events-none flex flex-col items-center justify-between p-6 z-20">
            <div className="w-full flex justify-between">
              <div className="w-8 h-8 border-t-4 border-l-4 border-turmeric-400 rounded-tl-xl shadow-sm" />
              <div className="w-8 h-8 border-t-4 border-r-4 border-turmeric-400 rounded-tr-xl shadow-sm" />
            </div>

            <div className="bg-forest-900/80 backdrop-blur-md px-3.5 py-1.5 rounded-full border border-turmeric-400/50 flex items-center gap-1.5 shadow-lg">
              <Scan size={14} className="text-turmeric-400 animate-spin" />
              <span className="text-[11px] font-bold text-paddy-100 tracking-wide">
                {t(language, 'align_leaf_hint')}
              </span>
            </div>

            <div className="w-full flex justify-between">
              <div className="w-8 h-8 border-b-4 border-l-4 border-turmeric-400 rounded-bl-xl shadow-sm" />
              <div className="w-8 h-8 border-b-4 border-r-4 border-turmeric-400 rounded-br-xl shadow-sm" />
            </div>
          </div>

          {/* Controls: Torch, Switch Camera & Close */}
          <div className="absolute top-3 right-3 flex items-center gap-2 z-20">
            {torchAvailable && (
              <button
                onClick={toggleTorch}
                aria-label="Toggle Torch"
                className={`w-9 h-9 rounded-full flex items-center justify-center backdrop-blur-md border border-white/20 active:scale-95 transition-all ${
                  torchOn ? 'bg-turmeric-400 text-forest-950' : 'bg-forest-900/70 text-white hover:bg-forest-900'
                }`}
              >
                {torchOn ? <Zap size={18} /> : <ZapOff size={18} />}
              </button>
            )}

            <button
              onClick={switchCameraFacing}
              aria-label={t(language, 'switch_camera')}
              className="w-9 h-9 rounded-full bg-forest-900/70 hover:bg-forest-900 text-white flex items-center justify-center backdrop-blur-md border border-white/20 active:scale-95 transition-transform"
            >
              <SwitchCamera size={18} />
            </button>

            <button
              onClick={handleCloseCamera}
              aria-label={t(language, 'close_camera')}
              className="w-9 h-9 rounded-full bg-forest-900/70 hover:bg-forest-900 text-white flex items-center justify-center backdrop-blur-md border border-white/20 active:scale-95 transition-transform"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Shutter Capture Button */}
        <button
          onClick={capturePhoto}
          className="w-full py-3.5 px-6 rounded-2xl bg-gradient-to-r from-turmeric-400 via-turmeric-500 to-turmeric-400 hover:from-turmeric-300 hover:to-turmeric-400 text-forest-950 font-bold text-sm flex items-center justify-center gap-2.5 shadow-lg shadow-turmeric-500/30 active:scale-95 transition-all"
        >
          <Camera size={22} className="stroke-[2.5]" />
          <span>{t(language, 'capture_photo')}</span>
        </button>

        <canvas ref={canvasRef} className="hidden" />
      </div>
    )
  }

  // 3. Default Idle Mode with Big Camera Button
  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`flex flex-col items-center gap-4 transition-all ${
        isDragging ? 'scale-105 border-2 border-dashed border-turmeric-400 rounded-3xl p-4 bg-turmeric-400/10' : ''
      }`}
    >
      {cameraError && (
        <div className="max-w-xs flex items-start gap-2 bg-laterite-500/15 border border-laterite-500/30 text-laterite-700 px-3.5 py-2.5 rounded-xl text-xs">
          <AlertCircle size={16} className="shrink-0 mt-0.5" />
          <span>{cameraError}</span>
        </div>
      )}

      {/* Big Yellow/Gold Camera Button with Pulsing Rings */}
      <div className="relative flex items-center justify-center my-2">
        <span className="absolute inline-flex h-full w-full rounded-full bg-turmeric-400/50 animate-pulseRing" />
        <span className="absolute inline-flex h-full w-full rounded-full bg-turmeric-400/40 animate-pulseRing [animation-delay:0.6s]" />
        <button
          onClick={() => startCamera('environment')}
          aria-label={t(language, 'tap_to_scan')}
          className="relative z-10 w-36 h-36 rounded-full bg-gradient-to-br from-turmeric-400 via-turmeric-500 to-turmeric-600 shadow-leaf flex flex-col items-center justify-center text-forest-950 active:scale-95 transition-transform hover:shadow-xl group cursor-pointer"
        >
          <Camera size={50} strokeWidth={2} className="group-hover:scale-110 transition-transform" />
          <span className="text-[11px] font-extrabold uppercase tracking-wider mt-1 text-forest-900/85">
            {t(language, 'use_camera')}
          </span>
        </button>
      </div>

      <div className="text-center">
        <p className="font-display font-bold text-lg text-forest-800">{t(language, 'tap_to_scan')}</p>
        <p className="text-xs text-forest-600/80 mt-0.5 max-w-xs">{t(language, 'camera_hint')}</p>
      </div>

      {/* Secondary Gallery Button */}
      <button
        onClick={() => galleryInputRef.current?.click()}
        className="inline-flex items-center gap-2 rounded-full border-2 border-forest-600/30 px-5 py-2.5 text-forest-700 font-bold text-xs hover:bg-forest-600/10 transition-colors shadow-sm active:scale-95 cursor-pointer bg-white"
      >
        <ImagePlus size={16} />
        {t(language, 'upload_gallery')}
      </button>

      {/* Quick Test Samples */}
      <div className="w-full max-w-xs pt-2">
        <p className="text-xs font-semibold text-forest-600/70 mb-2 flex items-center justify-center gap-1">
          <Sparkles size={13} className="text-turmeric-500" />
          <span>Quick test samples:</span>
        </p>
        <div className="grid grid-cols-3 gap-1.5">
          {SAMPLES.map((s) => (
            <button
              key={s.label}
              disabled={busy}
              onClick={() => handleSampleClick(s)}
              className="px-2 py-1.5 rounded-xl bg-white hover:bg-forest-50 border border-forest-200 text-[11px] font-medium text-forest-800 truncate text-center transition-all shadow-xs"
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* Hidden file inputs */}
      <input
        ref={fallbackCameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={handleFileChange}
      />
      <input
        ref={galleryInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleFileChange}
      />
    </div>
  )
}

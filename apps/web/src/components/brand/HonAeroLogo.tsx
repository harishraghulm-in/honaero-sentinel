import React from 'react';

interface HonAeroLogoProps {
  size?: 'sm' | 'md' | 'lg';
  showSubtitle?: boolean;
  className?: string;
  iconOnly?: boolean;
}

export const HonAeroLogo: React.FC<HonAeroLogoProps> = ({
  size = 'md',
  showSubtitle = true,
  className = '',
  iconOnly = false,
}) => {
  const iconDimensions = {
    sm: { w: 28, h: 28 },
    md: { w: 38, h: 38 },
    lg: { w: 52, h: 52 },
  }[size];

  return (
    <div className={`flex items-center gap-3 select-none ${className}`}>
      {/* AEROSPACE EMBLEM: Supersonic Delta Aircraft + Verification Shield + Cyan Reticle */}
      <div 
        className="relative shrink-0 flex items-center justify-center"
        style={{ width: iconDimensions.w, height: iconDimensions.h }}
      >
        <svg
          viewBox="0 0 100 100"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="w-full h-full drop-shadow-[0_0_12px_rgba(0,229,255,0.35)]"
        >
          <defs>
            {/* Metallic Titanium Silver Gradient */}
            <linearGradient id="metallicTitanium" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#FFFFFF" />
              <stop offset="35%" stopColor="#D8E2EC" />
              <stop offset="70%" stopColor="#94A3B8" />
              <stop offset="100%" stopColor="#475569" />
            </linearGradient>

            {/* Cyan Technical Laser Accent Gradient */}
            <linearGradient id="cyanAccent" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#00E5FF" />
              <stop offset="60%" stopColor="#00B4D8" />
              <stop offset="100%" stopColor="#0077B6" />
            </linearGradient>

            {/* Outer Verification Hex-Shield Ring */}
            <linearGradient id="shieldStroke" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#00E5FF" stopOpacity="0.8" />
              <stop offset="50%" stopColor="#64748B" stopOpacity="0.4" />
              <stop offset="100%" stopColor="#00E5FF" stopOpacity="0.8" />
            </linearGradient>
          </defs>

          {/* Outer Technical Verification Shield & Coordinate Ring */}
          <circle cx="50" cy="50" r="46" stroke="url(#shieldStroke)" strokeWidth="1.5" strokeDasharray="3 3" />
          <polygon
            points="50,6 88,24 88,68 50,92 12,68 12,24"
            stroke="url(#shieldStroke)"
            strokeWidth="2"
            fill="#0F172A"
            fillOpacity="0.8"
          />

          {/* Technical Crosshairs & Precision Verification Ticks */}
          <line x1="50" y1="10" x2="50" y2="18" stroke="#00E5FF" strokeWidth="2" />
          <line x1="50" y1="82" x2="50" y2="90" stroke="#00E5FF" strokeWidth="2" />
          <line x1="16" y1="50" x2="24" y2="50" stroke="#00E5FF" strokeWidth="2" />
          <line x1="76" y1="50" x2="84" y2="50" stroke="#00E5FF" strokeWidth="2" />

          {/* Concentric Precision HUD Targeting Ring */}
          <circle cx="50" cy="50" r="28" stroke="#00E5FF" strokeWidth="1" strokeOpacity="0.3" strokeDasharray="6 4" />

          {/* Supersonic Delta Aircraft Silhouette (Metallic Silver with Cyan Leading Edge) */}
          {/* Main Fuselage & Delta Wings */}
          <path
            d="M50 16 L61 46 L82 66 L65 67 L56 61 L50 82 L44 61 L35 67 L18 66 L39 46 Z"
            fill="url(#metallicTitanium)"
            stroke="#CBD5E1"
            strokeWidth="1.2"
          />

          {/* Aerodynamic Centerline & Cockpit Canopy (Cyan Core) */}
          <path
            d="M50 22 L53 38 L50 48 L47 38 Z"
            fill="#00E5FF"
            opacity="0.9"
          />

          {/* Wing Leading Edge Cyan Energy Streams */}
          <path
            d="M50 18 L62 48 L80 65"
            stroke="#00E5FF"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
          <path
            d="M50 18 L38 48 L20 65"
            stroke="#00E5FF"
            strokeWidth="1.5"
            strokeLinecap="round"
          />

          {/* Technical Verification Symbol: Precision Centered Diamond Reticle */}
          <rect
            x="48"
            y="48"
            width="4"
            height="4"
            transform="rotate(45 50 50)"
            fill="#00E5FF"
          />

          {/* Wingtip Telemetry Dots */}
          <circle cx="81" cy="66" r="2" fill="#00E5FF" />
          <circle cx="19" cy="66" r="2" fill="#00E5FF" />
          <circle cx="50" cy="82" r="2" fill="#00E5FF" />
        </svg>
      </div>

      {/* BRAND TYPOGRAPHY: Metallic Silver Wordmark + Cyan Technical Subtitle */}
      {!iconOnly && (
        <div className="flex flex-col justify-center font-heading">
          <div className="flex items-baseline gap-1.5 leading-none">
            <span className="text-base font-extrabold tracking-[0.16em] text-white">
              HON<span className="text-[#00E5FF]">AERO</span>
            </span>
            <span className="text-base font-bold tracking-[0.22em] text-[#CBD5E1] uppercase">
              SENTINEL
            </span>
          </div>
          {showSubtitle && (
            <span className="text-[10px] font-medium tracking-[0.18em] text-[#8B949E] uppercase mt-0.5 whitespace-nowrap font-sans">
              Smart Verification Studio
            </span>
          )}
        </div>
      )}
    </div>
  );
};

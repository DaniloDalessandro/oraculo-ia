import { LoginForm } from "@/components/login-form"

export default function LoginPage() {
  return (
    <div className="min-h-svh flex">
      {/* Left — dark hero band */}
      <div className="hidden lg:flex lg:w-1/2 bg-black flex-col justify-between p-12 relative overflow-hidden">
        {/* Grid pattern */}
        <div
          className="absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage:
              "linear-gradient(rgba(255,255,255,1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,1) 1px, transparent 1px)",
            backgroundSize: "48px 48px",
          }}
        />
        {/* Blue accent line top */}
        <div className="absolute top-0 left-0 right-0 h-0.5 bg-[#0070d1]" />

        {/* Logo */}
        <div className="relative z-10">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-[#0070d1] flex items-center justify-center">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <circle cx="8" cy="8" r="6" stroke="white" strokeWidth="1.5" />
                <circle cx="8" cy="8" r="2" fill="white" />
              </svg>
            </div>
            <span className="text-white font-semibold tracking-wide">Oráculo</span>
          </div>
        </div>

        {/* Center headline */}
        <div className="relative z-10 space-y-6">
          <div className="space-y-3">
            <p className="text-[#0070d1] text-sm font-medium tracking-widest uppercase">
              Porto de Itaguaí
            </p>
            <h1
              className="text-white leading-tight"
              style={{ fontSize: "44px", fontWeight: 300, letterSpacing: "0.1px" }}
            >
              Inteligência<br />de dados<br />portuários
            </h1>
          </div>
          <p className="text-white/50 text-base leading-relaxed max-w-xs">
            Consulte atracações, cargas, berços e indicadores operacionais em linguagem natural.
          </p>
        </div>

        {/* Bottom stats */}
        <div className="relative z-10 flex gap-8">
          {[
            { value: "ITA", label: "Agente IA" },
            { value: "SQL", label: "Geração automática" },
            { value: "24/7", label: "Disponível" },
          ].map((s) => (
            <div key={s.label}>
              <div className="text-white font-semibold text-lg">{s.value}</div>
              <div className="text-white/40 text-xs mt-0.5">{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Right — form */}
      <div className="flex-1 flex items-center justify-center bg-[#0a0a0a] px-6 py-12">
        <div className="w-full max-w-sm">
          <LoginForm />
        </div>
      </div>
    </div>
  )
}

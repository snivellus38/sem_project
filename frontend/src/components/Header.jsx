/**
 * Header.jsx — Top bar with project title and connection indicator.
 */

export default function Header({ wsStatus }) {
  const dotColor =
    wsStatus === 'connected' ? '#4ade80' :
    wsStatus === 'connecting' ? '#fbbf24' : '#f87171';

  return (
    <header className="flex items-center justify-between px-4 py-2 glass"
      style={{ borderRadius: '0 0 16px 16px', borderTop: 'none' }}
    >
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-sky-400 to-emerald-400 flex items-center justify-center text-white font-bold text-sm shadow-lg">
          A
        </div>
        <div>
          <h1 className="text-sm font-bold text-white tracking-wide">AuraSense</h1>
          <p className="text-[10px] text-slate-400">Digital Twin · Fluidized Bed Dryer</p>
        </div>
      </div>

      <div className="flex items-center gap-2 text-xs text-slate-400">
        <span
          className="w-2 h-2 rounded-full"
          style={{ background: dotColor, boxShadow: `0 0 6px ${dotColor}` }}
        />
        {wsStatus === 'connected' ? 'Connected' : wsStatus === 'connecting' ? 'Connecting…' : 'Offline'}
      </div>
    </header>
  );
}

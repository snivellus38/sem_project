/**
 * Dashboard.jsx — Metric gauges + charts + quality card.
 *
 * Right-side panel showing all telemetry data in real time.
 */

import Gauge from './Gauge';
import { MoistureChart, TemperatureChart, QualityChart } from './Charts';
import QualityCard from './QualityCard';

export default function Dashboard({ state, history }) {
  const moisture = state?.moisture != null ? +(state.moisture * 100).toFixed(1) : 0;
  const bedTemp = state?.bed_temp ?? 0;
  const inletTemp = state?.inlet_temp ?? 0;
  const airflow = state?.airflow != null ? +(state.airflow * 100).toFixed(0) : 0;

  return (
    <div className="flex flex-col gap-3 overflow-y-auto pr-1 h-full">
      {/* Top row — Gauges */}
      <div className="flex flex-wrap gap-2 justify-center">
        <Gauge
          label="Moisture"
          value={moisture}
          unit="%"
          min={0} max={75}
          color="#38bdf8"
        />
        <Gauge
          label="Bed Temp"
          value={bedTemp}
          unit="°C"
          min={20} max={140}
          color={bedTemp > 100 ? '#ef4444' : '#f97316'}
        />
        <Gauge
          label="Inlet Temp"
          value={inletTemp}
          unit="°C"
          min={20} max={140}
          color="#f97316"
        />
        <Gauge
          label="Airflow"
          value={airflow}
          unit="%"
          min={0} max={100}
          color="#60a5fa"
        />
      </div>

      {/* Quality card */}
      <QualityCard state={state} />

      {/* Charts */}
      <MoistureChart history={history} />
      <TemperatureChart history={history} />
      <QualityChart history={history} />

      {/* Sensor pills (if available) */}
      {state?.sensors?.enose && (
        <div className="glass-sm p-3">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
            E-Nose (MOS voltages)
          </h3>
          <div className="flex flex-wrap gap-1">
            {state.sensors.enose.voltages.map((v, i) => (
              <span
                key={i}
                className="text-[10px] bg-white/5 px-1.5 py-0.5 rounded"
                style={{
                  borderLeft: `2px solid hsl(${(i * 45) % 360}, 70%, 60%)`,
                }}
              >
                CH{i}: {v.toFixed(2)}V
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

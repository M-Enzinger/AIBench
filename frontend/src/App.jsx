import React, { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import './App.css'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000'
})

const defaultSpec = JSON.stringify(
  {
    metadata: { name: 'Lottery choices', version: '1.0.0', description: 'Example scenario JSON' },
    instructions: { system: 'You are a rational agent participating in a lottery study.' },
    tasks: [
      { id: 'q1', type: 'choice', payload: 'Choose between A and B', output_key: 'q1_choice' },
      { id: 'q2', type: 'numeric', payload: 'Estimate expected value', output_key: 'q2_estimate' }
    ],
    response_schema: { type: 'object', properties: { answers: { type: 'object' } }, required: ['answers'] },
    metrics: [
      { id: 'consistency', description: 'Share of consistent lottery preferences' }
    ]
  },
  null,
  2
)

function App() {
  const [scenarios, setScenarios] = useState([])
  const [experiments, setExperiments] = useState([])
  const [runs, setRuns] = useState([])
  const [activeExperiment, setActiveExperiment] = useState(null)

  const [scenarioForm, setScenarioForm] = useState({ name: '', version: '1.0.0', description: '', specification: defaultSpec })
  const [experimentForm, setExperimentForm] = useState({
    name: '',
    scenario_id: '',
    human_enabled: false,
    human_participants: 10,
    parallel_requests: 4,
    run_count: 20,
    temperature: '0.7',
    settings: '{"repair_invalid_json": true}'
  })
  const [aiSources, setAiSources] = useState([
    { label: 'OpenAI: gpt-4o-mini', provider: 'openai', model: 'gpt-4o-mini', runs: 20, temperature: 0.7 }
  ])

  useEffect(() => {
    fetchScenarios()
    fetchExperiments()
  }, [])

  const totals = useMemo(() => {
    const runTotal = experiments.reduce((sum, exp) => {
      const aiTotal = (exp.ai_sources || []).reduce((inner, src) => inner + Number(src.runs || 0), 0) || Number(exp.run_count || 0)
      const humanTotal = exp.human_enabled ? Number(exp.human_participants || 0) : 0
      return sum + aiTotal + humanTotal
    }, 0)
    return { scenarioCount: scenarios.length, experimentCount: experiments.length, runTotal }
  }, [scenarios, experiments])

  async function fetchScenarios() {
    const { data } = await api.get('/scenarios/')
    setScenarios(data)
  }

  async function fetchExperiments() {
    const { data } = await api.get('/experiments/')
    setExperiments(data)
  }

  async function createScenario() {
    await api.post('/scenarios/', scenarioForm)
    setScenarioForm({ name: '', version: '1.0.0', description: '', specification: defaultSpec })
    fetchScenarios()
  }

  function addSource() {
    setAiSources((prev) => [...prev, { label: 'New model', provider: 'openai', model: 'gpt-4o-mini', runs: 10, temperature: 0.7 }])
  }

  function updateSource(index, key, value) {
    setAiSources((prev) => prev.map((src, idx) => (idx === index ? { ...src, [key]: value } : src)))
  }

  function removeSource(index) {
    setAiSources((prev) => prev.filter((_, idx) => idx !== index))
  }

  async function createExperiment() {
    const payload = {
      ...experimentForm,
      scenario_id: Number(experimentForm.scenario_id),
      human_participants: Number(experimentForm.human_participants),
      run_count: Number(experimentForm.run_count),
      parallel_requests: Number(experimentForm.parallel_requests),
      model_provider: aiSources[0]?.provider || 'openai',
      model_name: aiSources[0]?.model || 'gpt-4o-mini',
      ai_sources: aiSources.map((s) => ({ ...s, runs: Number(s.runs) || 0 })),
      ai_enabled: aiSources.length > 0
    }

    await api.post('/experiments/', payload)
    setExperimentForm({ ...experimentForm, name: '' })
    fetchExperiments()
  }

  async function viewRuns(expId) {
    setActiveExperiment(expId)
    const { data } = await api.get(`/experiments/${expId}/runs`)
    setRuns(data)
  }

  return (
    <div className="app-shell">
      <div className="header">
        <div className="title-stack">
          <h1>LLM Experiment Orchestrator</h1>
          <p>Define structured decision tasks, run AI/human cohorts, and inspect machine-readable outcomes.</p>
        </div>
        <div className="tag-grid">
          <span className="badge">Dockerized – port 2222</span>
          <span className="badge neutral">No login required</span>
        </div>
      </div>

      <div className="hero">
        <div>
          <h2 style={{ margin: '0 0 4px 0' }}>Scenario-driven analytics</h2>
          <p className="muted" style={{ margin: 0 }}>
            Bulk-run multiple LLM providers and human cohorts with strict JSON validation and reproducible experiment records.
          </p>
        </div>
        <div className="cta">
          <button className="button" onClick={createScenario}>Save scenario</button>
          <button className="button secondary" onClick={createExperiment}>Launch experiment</button>
        </div>
      </div>

      <div className="grid three" style={{ marginTop: 18 }}>
        <div className="card">
          <div className="small-label">Scenarios</div>
          <div style={{ fontSize: 26, fontWeight: 700 }}>{totals.scenarioCount}</div>
          <p className="muted">Versioned JSON specifications</p>
        </div>
        <div className="card">
          <div className="small-label">Experiments</div>
          <div style={{ fontSize: 26, fontWeight: 700 }}>{totals.experimentCount}</div>
          <p className="muted">Tracked with prompts, outputs, and sources</p>
        </div>
        <div className="card">
          <div className="small-label">Runs stored</div>
          <div style={{ fontSize: 26, fontWeight: 700 }}>{totals.runTotal}</div>
          <p className="muted">Human + AI responses, ready for analysis</p>
        </div>
      </div>

      <div className="grid two" style={{ marginTop: 18 }}>
        <div className="card">
          <h3>Create scenario</h3>
          <label className="label">Name</label>
          <input className="input" value={scenarioForm.name} onChange={(e) => setScenarioForm({ ...scenarioForm, name: e.target.value })} placeholder="Risk attitudes study" />
          <label className="label">Version</label>
          <input className="input" value={scenarioForm.version} onChange={(e) => setScenarioForm({ ...scenarioForm, version: e.target.value })} />
          <label className="label">Description</label>
          <input className="input" value={scenarioForm.description} onChange={(e) => setScenarioForm({ ...scenarioForm, description: e.target.value })} placeholder="JSON specification for lottery choices" />
          <label className="label">Specification (JSON)</label>
          <textarea className="textarea" value={scenarioForm.specification} onChange={(e) => setScenarioForm({ ...scenarioForm, specification: e.target.value })} />
          <div className="inline-actions">
            <button className="button" onClick={createScenario}>Save scenario</button>
            <span className="muted">Validates and stores versioned blueprint.</span>
          </div>
        </div>

        <div className="card">
          <h3>Configure experiment</h3>
          <label className="label">Experiment name</label>
          <input className="input" value={experimentForm.name} onChange={(e) => setExperimentForm({ ...experimentForm, name: e.target.value })} placeholder="Risk aversion benchmark" />
          <label className="label">Scenario</label>
          <select className="select" value={experimentForm.scenario_id} onChange={(e) => setExperimentForm({ ...experimentForm, scenario_id: e.target.value })}>
            <option value="">Select scenario</option>
            {scenarios.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} v{s.version}
              </option>
            ))}
          </select>
          <div className="grid three">
            <div>
              <label className="label">Default run count per source</label>
              <input className="input" type="number" value={experimentForm.run_count} onChange={(e) => setExperimentForm({ ...experimentForm, run_count: e.target.value })} />
            </div>
            <div>
              <label className="label">Parallel requests</label>
              <input className="input" type="number" value={experimentForm.parallel_requests} onChange={(e) => setExperimentForm({ ...experimentForm, parallel_requests: e.target.value })} />
            </div>
            <div>
              <label className="label">Temperature</label>
              <input className="input" value={experimentForm.temperature} onChange={(e) => setExperimentForm({ ...experimentForm, temperature: e.target.value })} />
            </div>
          </div>

          <hr className="divider" />
          <div className="section-title">
            <h4 style={{ margin: 0 }}>AI sources</h4>
            <button className="button secondary" type="button" onClick={addSource}>Add source</button>
          </div>
          <div className="list-rows">
            {aiSources.length === 0 && <div className="empty">Add at least one AI provider/model to run automated cohorts.</div>}
            {aiSources.map((source, idx) => (
              <div key={idx} className="source-card">
                <div className="inline-actions" style={{ justifyContent: 'space-between' }}>
                  <h4>{source.label || `Source ${idx + 1}`}</h4>
                  <button className="button secondary" type="button" onClick={() => removeSource(idx)}>Remove</button>
                </div>
                <label className="label">Label</label>
                <input className="input" value={source.label} onChange={(e) => updateSource(idx, 'label', e.target.value)} placeholder="OpenAI vs Gemini vs Human" />
                <div className="grid three">
                  <div>
                    <label className="label">Provider</label>
                    <input className="input" value={source.provider} onChange={(e) => updateSource(idx, 'provider', e.target.value)} placeholder="openai | anthropic | gemini | grok" />
                  </div>
                  <div>
                    <label className="label">Model</label>
                    <input className="input" value={source.model} onChange={(e) => updateSource(idx, 'model', e.target.value)} placeholder="gpt-4o-mini" />
                  </div>
                  <div>
                    <label className="label">Runs</label>
                    <input className="input" type="number" value={source.runs} onChange={(e) => updateSource(idx, 'runs', e.target.value)} />
                  </div>
                </div>
                <label className="label">Temperature (optional)</label>
                <input className="input" value={source.temperature ?? ''} onChange={(e) => updateSource(idx, 'temperature', e.target.value)} placeholder="0.7" />
              </div>
            ))}
          </div>

          <hr className="divider" />
          <div className="section-title">
            <h4 style={{ margin: 0 }}>Human cohort</h4>
            <label className="inline-actions" style={{ gap: 8 }}>
              <input type="checkbox" checked={experimentForm.human_enabled} onChange={(e) => setExperimentForm({ ...experimentForm, human_enabled: e.target.checked })} />
              <span className="muted">Enable participant-facing form</span>
            </label>
          </div>
          <div className="grid two">
            <div>
              <label className="label">Participants</label>
              <input className="input" type="number" value={experimentForm.human_participants} onChange={(e) => setExperimentForm({ ...experimentForm, human_participants: e.target.value })} />
            </div>
            <div>
              <label className="label">Additional settings (JSON)</label>
              <textarea className="textarea" style={{ minHeight: 90 }} value={experimentForm.settings} onChange={(e) => setExperimentForm({ ...experimentForm, settings: e.target.value })} />
            </div>
          </div>

          <div className="inline-actions">
            <button className="button" onClick={createExperiment} disabled={!experimentForm.scenario_id}>Launch experiment</button>
            <span className="muted">Runs are recorded with prompts, raw outputs, and parsed JSON.</span>
          </div>
        </div>
      </div>

      <div className="section-title" style={{ marginTop: 28 }}>
        <h3 style={{ margin: 0 }}>Saved scenarios</h3>
        <span className="muted">Inspect the JSON grammar that governs prompting and evaluation.</span>
      </div>
      <div className="grid three">
        {scenarios.map((s) => (
          <div key={s.id} className="card">
            <div className="inline-actions" style={{ justifyContent: 'space-between' }}>
              <div>
                <h4 style={{ margin: 0 }}>{s.name}</h4>
                <span className="muted">v{s.version}</span>
              </div>
              <span className="badge neutral">ID {s.id}</span>
            </div>
            <p className="muted">{s.description || 'No description provided.'}</p>
            <pre style={{ maxHeight: 200, overflow: 'auto', background: '#0b1020', padding: 12, borderRadius: 10, border: '1px solid var(--border)' }}>
              {(() => {
                try {
                  return JSON.stringify(JSON.parse(s.specification || '{}'), null, 2)
                } catch (e) {
                  return s.specification || '{}'
                }
              })()}
            </pre>
          </div>
        ))}
        {scenarios.length === 0 && <div className="empty">No scenarios yet. Save one above to seed experiments.</div>}
      </div>

      <div className="section-title" style={{ marginTop: 28 }}>
        <h3 style={{ margin: 0 }}>Experiments</h3>
        <span className="muted">Monitor cohorts, providers, and human participation.</span>
      </div>
      <div className="grid three">
        {experiments.map((exp) => (
          <div key={exp.id} className="card">
            <div className="inline-actions" style={{ justifyContent: 'space-between' }}>
              <div>
                <h4 style={{ margin: 0 }}>{exp.name}</h4>
                <div className="muted">Linked scenario #{exp.scenario_id}</div>
              </div>
              <span className="badge">{exp.model_provider} · {exp.model_name}</span>
            </div>
            <div className="tag-grid" style={{ margin: '8px 0' }}>
              <span className="badge neutral">Parallel {exp.parallel_requests}x</span>
              <span className="badge neutral">Human cohort {exp.human_enabled ? `${exp.human_participants}` : 'off'}</span>
            </div>
            <div className="muted" style={{ marginBottom: 10 }}>
              AI sources: {(exp.ai_sources || []).map((s) => s.label || `${s.provider}:${s.model}`).join(', ') || `${exp.model_provider}:${exp.model_name}`}
            </div>
            <button className="button secondary" onClick={() => viewRuns(exp.id)}>Open runs</button>
          </div>
        ))}
        {experiments.length === 0 && <div className="empty">Launch your first experiment to see cohort-level run records.</div>}
      </div>

      {activeExperiment && (
        <div style={{ marginTop: 32 }}>
          <div className="section-title">
            <h3 style={{ margin: 0 }}>Runs for experiment #{activeExperiment}</h3>
            <button className="button secondary" onClick={() => viewRuns(activeExperiment)}>Refresh</button>
          </div>
          <table className="run-table">
            <thead>
              <tr>
                <th>Source</th>
                <th>Status</th>
                <th>Parsed response</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.id}>
                  <td>{r.source_label}</td>
                  <td><span className="status-chip">{r.status}</span></td>
                  <td>
                    <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{r.parsed_response}</pre>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default App

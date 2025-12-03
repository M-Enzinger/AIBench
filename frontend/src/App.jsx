import React, { useEffect, useState } from 'react'
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000'
})

function App() {
  const [token, setToken] = useState('')
  const [scenarios, setScenarios] = useState([])
  const [experiments, setExperiments] = useState([])
  const [runs, setRuns] = useState([])
  const [scenarioForm, setScenarioForm] = useState({ name: '', version: '1.0', description: '', specification: '{"metadata": {"name": "example"}}' })
  const [experimentForm, setExperimentForm] = useState({ name: '', scenario_id: '', model_provider: 'openai', model_name: 'gpt-4o-mini', run_count: 5, temperature: '0.7', human_enabled: false, ai_enabled: true, parallel_requests: 1, settings: '{}' })
  const [authForm, setAuthForm] = useState({ email: 'admin@aibench.local', password: 'admin' })
  const [activeExperiment, setActiveExperiment] = useState(null)

  useEffect(() => {
    fetchScenarios()
    fetchExperiments()
  }, [])

  const authHeaders = token ? { Authorization: `Bearer ${token}` } : {}

  async function login() {
    const { data } = await api.post('/auth/login', authForm)
    setToken(data.access_token)
  }

  async function fetchScenarios() {
    const { data } = await api.get('/scenarios/')
    setScenarios(data)
  }

  async function fetchExperiments() {
    const { data } = await api.get('/experiments/')
    setExperiments(data)
  }

  async function createScenario() {
    await api.post('/scenarios/', scenarioForm, { headers: authHeaders })
    setScenarioForm({ name: '', version: '1.0', description: '', specification: '{"metadata": {"name": "example"}}' })
    fetchScenarios()
  }

  async function createExperiment() {
    await api.post('/experiments/', { ...experimentForm, scenario_id: Number(experimentForm.scenario_id), run_count: Number(experimentForm.run_count), parallel_requests: Number(experimentForm.parallel_requests) }, { headers: authHeaders })
    setExperimentForm({ ...experimentForm, name: '', scenario_id: '' })
    fetchExperiments()
  }

  async function viewRuns(expId) {
    setActiveExperiment(expId)
    const { data } = await api.get(`/experiments/${expId}/runs`)
    setRuns(data)
  }

  return (
    <div style={{ fontFamily: 'Inter, sans-serif', padding: '1.5rem', background: '#0b1220', color: '#e7ecf3', minHeight: '100vh' }}>
      <h1 style={{ marginBottom: '1rem' }}>AIBench Experiment Dashboard</h1>
      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
        <div style={{ background: '#11182a', padding: '1rem', borderRadius: '12px', border: '1px solid #23304b' }}>
          <h2>Authentication</h2>
          <input value={authForm.email} onChange={(e) => setAuthForm({ ...authForm, email: e.target.value })} placeholder="email" style={{ width: '100%', marginBottom: '0.5rem' }} />
          <input value={authForm.password} type="password" onChange={(e) => setAuthForm({ ...authForm, password: e.target.value })} placeholder="password" style={{ width: '100%', marginBottom: '0.5rem' }} />
          <button onClick={login} style={{ width: '100%' }}>Login</button>
          {token && <p style={{ fontSize: '0.85rem', marginTop: '0.5rem' }}>Token ready. Protected actions enabled.</p>}
        </div>

        <div style={{ background: '#11182a', padding: '1rem', borderRadius: '12px', border: '1px solid #23304b' }}>
          <h2>New Scenario</h2>
          <input value={scenarioForm.name} onChange={(e) => setScenarioForm({ ...scenarioForm, name: e.target.value })} placeholder="Name" style={{ width: '100%', marginBottom: '0.5rem' }} />
          <input value={scenarioForm.version} onChange={(e) => setScenarioForm({ ...scenarioForm, version: e.target.value })} placeholder="Version" style={{ width: '100%', marginBottom: '0.5rem' }} />
          <textarea value={scenarioForm.description} onChange={(e) => setScenarioForm({ ...scenarioForm, description: e.target.value })} placeholder="Description" style={{ width: '100%', marginBottom: '0.5rem' }} />
          <textarea value={scenarioForm.specification} onChange={(e) => setScenarioForm({ ...scenarioForm, specification: e.target.value })} placeholder="Scenario JSON" style={{ width: '100%', height: '120px', marginBottom: '0.5rem' }} />
          <button onClick={createScenario} disabled={!token} style={{ width: '100%' }}>Save Scenario</button>
          {!token && <small>Login to create scenarios.</small>}
        </div>

        <div style={{ background: '#11182a', padding: '1rem', borderRadius: '12px', border: '1px solid #23304b' }}>
          <h2>New Experiment</h2>
          <input value={experimentForm.name} onChange={(e) => setExperimentForm({ ...experimentForm, name: e.target.value })} placeholder="Name" style={{ width: '100%', marginBottom: '0.5rem' }} />
          <select value={experimentForm.scenario_id} onChange={(e) => setExperimentForm({ ...experimentForm, scenario_id: e.target.value })} style={{ width: '100%', marginBottom: '0.5rem' }}>
            <option value="">Select scenario</option>
            {scenarios.map((s) => <option key={s.id} value={s.id}>{s.name} v{s.version}</option>)}
          </select>
          <input value={experimentForm.model_provider} onChange={(e) => setExperimentForm({ ...experimentForm, model_provider: e.target.value })} placeholder="Provider (openai, anthropic, gemini, grok)" style={{ width: '100%', marginBottom: '0.5rem' }} />
          <input value={experimentForm.model_name} onChange={(e) => setExperimentForm({ ...experimentForm, model_name: e.target.value })} placeholder="Model name" style={{ width: '100%', marginBottom: '0.5rem' }} />
          <input type="number" value={experimentForm.run_count} onChange={(e) => setExperimentForm({ ...experimentForm, run_count: e.target.value })} placeholder="Run count" style={{ width: '100%', marginBottom: '0.5rem' }} />
          <input value={experimentForm.temperature} onChange={(e) => setExperimentForm({ ...experimentForm, temperature: e.target.value })} placeholder="Temperature" style={{ width: '100%', marginBottom: '0.5rem' }} />
          <label style={{ display: 'block', marginBottom: '0.5rem' }}>
            <input type="checkbox" checked={experimentForm.human_enabled} onChange={(e) => setExperimentForm({ ...experimentForm, human_enabled: e.target.checked })} /> Include human cohort
          </label>
          <label style={{ display: 'block', marginBottom: '0.5rem' }}>
            <input type="checkbox" checked={experimentForm.ai_enabled} onChange={(e) => setExperimentForm({ ...experimentForm, ai_enabled: e.target.checked })} /> Run AI sources
          </label>
          <input type="number" value={experimentForm.parallel_requests} onChange={(e) => setExperimentForm({ ...experimentForm, parallel_requests: e.target.value })} placeholder="Parallel requests" style={{ width: '100%', marginBottom: '0.5rem' }} />
          <textarea value={experimentForm.settings} onChange={(e) => setExperimentForm({ ...experimentForm, settings: e.target.value })} placeholder="Additional settings JSON" style={{ width: '100%', height: '80px', marginBottom: '0.5rem' }} />
          <button onClick={createExperiment} disabled={!token || !experimentForm.scenario_id} style={{ width: '100%' }}>Start Experiment</button>
          {!token && <small>Login to start experiments.</small>}
        </div>
      </section>

      <section style={{ marginTop: '1.5rem' }}>
        <h2>Scenarios</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '0.75rem' }}>
          {scenarios.map((s) => (
            <div key={s.id} style={{ background: '#11182a', padding: '1rem', borderRadius: '12px', border: '1px solid #23304b' }}>
              <h3>{s.name} v{s.version}</h3>
              <p style={{ fontSize: '0.9rem' }}>{s.description}</p>
              <pre style={{ background: '#0b1020', padding: '0.5rem', borderRadius: '8px', maxHeight: '180px', overflow: 'auto' }}>{s.specification}</pre>
            </div>
          ))}
        </div>
      </section>

      <section style={{ marginTop: '1.5rem' }}>
        <h2>Experiments</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.75rem' }}>
          {experiments.map((exp) => (
            <div key={exp.id} style={{ background: '#11182a', padding: '1rem', borderRadius: '12px', border: '1px solid #23304b' }}>
              <h3>{exp.name}</h3>
              <p style={{ fontSize: '0.9rem' }}>Model: {exp.model_provider} / {exp.model_name}</p>
              <p>Runs: {exp.run_count} | Human: {exp.human_enabled ? 'yes' : 'no'} | AI: {exp.ai_enabled ? 'yes' : 'no'}</p>
              <button onClick={() => viewRuns(exp.id)}>View Runs</button>
            </div>
          ))}
        </div>
      </section>

      {activeExperiment && (
        <section style={{ marginTop: '1.5rem' }}>
          <h2>Runs for experiment #{activeExperiment}</h2>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ borderBottom: '1px solid #23304b', padding: '0.5rem', textAlign: 'left' }}>Source</th>
                <th style={{ borderBottom: '1px solid #23304b', padding: '0.5rem', textAlign: 'left' }}>Status</th>
                <th style={{ borderBottom: '1px solid #23304b', padding: '0.5rem', textAlign: 'left' }}>Parsed response</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.id}>
                  <td style={{ padding: '0.5rem', borderBottom: '1px solid #23304b' }}>{r.source_label}</td>
                  <td style={{ padding: '0.5rem', borderBottom: '1px solid #23304b' }}>{r.status}</td>
                  <td style={{ padding: '0.5rem', borderBottom: '1px solid #23304b' }}><pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{r.parsed_response}</pre></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  )
}

export default App

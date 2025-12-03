import axios from 'axios'
import { useEffect, useMemo, useState } from 'react'

const providerOptions = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'gemini', label: 'Google Gemini' },
  { value: 'grok', label: 'Grok (xAI)' },
]

type AnswerType = 'free_text' | 'true_false' | 'single_choice' | 'ranking'

type Exercise = {
  id: number
  question_text: string
  answer_type: AnswerType
  options: { id: number; text: string; position: number }[]
}

type ExperimentRow = {
  id: number
  name: string
  description: string
  provider: string
  model: string
  temperature: number
  runs: number
  status: string
  created_at: string
  completed_runs: number
}

type ExperimentExercise = {
  exercise_id: number
  question_text: string
  answer_type: AnswerType
  options: { id: number; text: string; position: number }[]
  completed_items: number
}

type BatchItem = {
  id: number
  run_index: number
  parse_success: boolean
  answer: any
}

const emptyExercise: Exercise = {
  id: 0,
  question_text: '',
  answer_type: 'free_text',
  options: [],
}

const App = () => {
  const [activeTab, setActiveTab] = useState<'home' | 'settings' | 'exercises' | 'experiments'>('home')
  const [settings, setSettings] = useState({ openai_key: '', anthropic_key: '', gemini_key: '', grok_key: '' })
  const [exercises, setExercises] = useState<Exercise[]>([])
  const [selectedExerciseId, setSelectedExerciseId] = useState<number | null>(null)
  const [editorData, setEditorData] = useState<Exercise>(emptyExercise)
  const [experiments, setExperiments] = useState<ExperimentRow[]>([])
  const [expError, setExpError] = useState('')
  const [selectedExperimentId, setSelectedExperimentId] = useState<number | null>(null)
  const [experimentExercises, setExperimentExercises] = useState<ExperimentExercise[]>([])
  const [selectedExperimentExerciseId, setSelectedExperimentExerciseId] = useState<number | null>(null)
  const [batchItems, setBatchItems] = useState<BatchItem[]>([])
  const [newExperiment, setNewExperiment] = useState({
    name: '',
    description: '',
    provider: 'openai',
    model: '',
    temperature: 0,
    runs: 1,
    exercise_ids: [] as number[],
  })

  const loadSettings = async () => {
    const res = await axios.get('/api/settings')
    setSettings(res.data)
  }

  const loadExercises = async () => {
    const res = await axios.get('/api/exercises')
    setExercises(res.data)
  }

  const loadExperiments = async () => {
    const res = await axios.get('/api/experiments')
    setExperiments(res.data)
  }

  useEffect(() => {
    loadSettings()
    loadExercises()
    loadExperiments()
    const timer = setInterval(loadExperiments, 4000)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    if (selectedExperimentId) {
      axios.get(`/api/experiments/${selectedExperimentId}/exercises`).then((res) => {
        setExperimentExercises(res.data)
      })
    } else {
      setExperimentExercises([])
    }
    setSelectedExperimentExerciseId(null)
    setBatchItems([])
  }, [selectedExperimentId])

  useEffect(() => {
    if (selectedExperimentId && selectedExperimentExerciseId) {
      axios
        .get(`/api/experiments/${selectedExperimentId}/exercises/${selectedExperimentExerciseId}/batch_items`)
        .then((res) => setBatchItems(res.data))
    } else {
      setBatchItems([])
    }
  }, [selectedExperimentId, selectedExperimentExerciseId])

  const saveSettings = async () => {
    await axios.post('/api/settings', settings)
    await loadSettings()
  }

  const startNewExercise = () => {
    setSelectedExerciseId(null)
    setEditorData({ ...emptyExercise })
  }

  const saveExercise = async () => {
    if (selectedExerciseId) {
      await axios.put(`/api/exercises/${selectedExerciseId}`, editorData)
    } else {
      const res = await axios.post('/api/exercises', editorData)
      setSelectedExerciseId(res.data.id)
    }
    await loadExercises()
  }

  const deleteExercise = async () => {
    if (!selectedExerciseId) return
    await axios.delete(`/api/exercises/${selectedExerciseId}`)
    startNewExercise()
    await loadExercises()
  }

  const duplicateExercise = async () => {
    if (!selectedExerciseId) return
    const res = await axios.post(`/api/exercises/${selectedExerciseId}/duplicate`)
    setSelectedExerciseId(res.data.id)
    await loadExercises()
  }

  const toggleExerciseSelection = (id: number) => {
    setNewExperiment((prev) => {
      const exists = prev.exercise_ids.includes(id)
      const updated = exists ? prev.exercise_ids.filter((x) => x !== id) : [...prev.exercise_ids, id]
      return { ...prev, exercise_ids: updated }
    })
  }

  const startExperiment = async () => {
    try {
      setExpError('')
      await axios.post('/api/experiments', newExperiment)
      setNewExperiment({ name: '', description: '', provider: 'openai', model: '', temperature: 0, runs: 1, exercise_ids: [] })
      await loadExperiments()
    } catch (err: any) {
      setExpError(err.response?.data?.detail || 'Failed to start experiment')
    }
  }

  const exportCsv = (rows: any[], filename: string) => {
    if (!rows.length) return
    const headers = Object.keys(rows[0])
    const csv = [headers.join(','), ...rows.map((r) => headers.map((h) => JSON.stringify(r[h] ?? '')).join(','))].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.click()
  }

  const selectedExercise = useMemo(() => exercises.find((ex) => ex.id === selectedExerciseId), [exercises, selectedExerciseId])

  useEffect(() => {
    if (selectedExercise) {
      setEditorData({
        id: selectedExercise.id,
        question_text: selectedExercise.question_text,
        answer_type: selectedExercise.answer_type,
        options: selectedExercise.options || [],
      })
    }
  }, [selectedExercise])

  const visibleExercises = experiments

  return (
    <div className="app-shell">
      <header>
        <div>
          <h1>AIBench</h1>
          <small>Configure API keys, design exercises, launch experiments, and review structured AI answers.</small>
        </div>
        <nav>
          <button className={activeTab === 'home' ? 'active' : ''} onClick={() => setActiveTab('home')}>
            Home
          </button>
          <button className={activeTab === 'settings' ? 'active' : ''} onClick={() => setActiveTab('settings')}>
            Settings
          </button>
          <button className={activeTab === 'exercises' ? 'active' : ''} onClick={() => setActiveTab('exercises')}>
            Exercises
          </button>
          <button className={activeTab === 'experiments' ? 'active' : ''} onClick={() => setActiveTab('experiments')}>
            Experiments
          </button>
        </nav>
      </header>

      {activeTab === 'home' && (
        <section>
          <h2>Welcome to AIBench</h2>
          <p>
            Use this workspace to configure provider API keys, build exercises with structured answer expectations, bundle them
            into experiments, and collect AI-generated responses in a transparent, typed format.
          </p>
          <ol>
            <li>Save provider API keys in Settings.</li>
            <li>Create exercises with the desired answer formats.</li>
            <li>Assemble experiments, choose provider/model/temperature, and set run counts.</li>
            <li>Monitor run progress, inspect results per exercise, and export any table as CSV.</li>
          </ol>
        </section>
      )}

      {activeTab === 'settings' && (
        <section>
          <h2>API Keys</h2>
          <label>OpenAI API Key</label>
          <input value={settings.openai_key || ''} onChange={(e) => setSettings({ ...settings, openai_key: e.target.value })} />
          <label>Anthropic API Key</label>
          <input value={settings.anthropic_key || ''} onChange={(e) => setSettings({ ...settings, anthropic_key: e.target.value })} />
          <label>Google Gemini API Key</label>
          <input value={settings.gemini_key || ''} onChange={(e) => setSettings({ ...settings, gemini_key: e.target.value })} />
          <label>Grok (xAI) API Key</label>
          <input value={settings.grok_key || ''} onChange={(e) => setSettings({ ...settings, grok_key: e.target.value })} />
          <button className="primary" onClick={saveSettings}>Save Keys</button>
        </section>
      )}

      {activeTab === 'exercises' && (
        <div className="flex-row">
          <div className="sidebar">
            <section>
              <h2>Exercises</h2>
              <button className="primary" onClick={startNewExercise}>Create New</button>
              <div style={{ marginTop: 12 }}>
                {exercises.map((ex) => (
                  <div
                    key={ex.id}
                    className={`list-item ${selectedExerciseId === ex.id ? 'active' : ''}`}
                    onClick={() => setSelectedExerciseId(ex.id)}
                  >
                    <strong>#{ex.id}</strong>
                    <div>{ex.question_text.slice(0, 60)}</div>
                    <small>{ex.answer_type}</small>
                  </div>
                ))}
              </div>
            </section>
          </div>
          <div className="detail">
            <section>
              <h2>Exercise Editor</h2>
              <label>Question</label>
              <textarea
                value={editorData.question_text}
                onChange={(e) => setEditorData({ ...editorData, question_text: e.target.value })}
              />
              <label>Answer Type</label>
              <select
                value={editorData.answer_type}
                onChange={(e) => setEditorData({ ...editorData, answer_type: e.target.value as AnswerType })}
              >
                <option value="free_text">Free text</option>
                <option value="true_false">True / False</option>
                <option value="single_choice">Single choice</option>
                <option value="ranking">Ranking</option>
              </select>

              {(editorData.answer_type === 'single_choice' || editorData.answer_type === 'ranking') && (
                <div>
                  <label>{editorData.answer_type === 'single_choice' ? 'Answer Options' : 'Items to Rank'}</label>
                  {editorData.options.map((opt, idx) => (
                    <div className="option-row" key={idx}>
                      <input
                        value={opt.text}
                        onChange={(e) => {
                          const updated = [...editorData.options]
                          updated[idx] = { ...opt, text: e.target.value }
                          setEditorData({ ...editorData, options: updated })
                        }}
                      />
                      <input
                        style={{ width: 70 }}
                        type="number"
                        value={opt.position}
                        onChange={(e) => {
                          const updated = [...editorData.options]
                          updated[idx] = { ...opt, position: Number(e.target.value) }
                          setEditorData({ ...editorData, options: updated })
                        }}
                        title="Position"
                      />
                      <button
                        className="secondary"
                        onClick={() => setEditorData({ ...editorData, options: editorData.options.filter((_, i) => i !== idx) })}
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                  <button
                    className="secondary"
                    onClick={() => setEditorData({ ...editorData, options: [...editorData.options, { id: Date.now(), text: '', position: editorData.options.length }] })}
                  >
                    Add Option
                  </button>
                </div>
              )}

              <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
                <button className="primary" onClick={saveExercise}>Save</button>
                <button className="secondary" onClick={duplicateExercise}>Duplicate</button>
                <button className="secondary" onClick={deleteExercise}>Delete</button>
              </div>
            </section>
          </div>
        </div>
      )}

      {activeTab === 'experiments' && (
        <div>
          <section>
            <h2>Create Experiment</h2>
            <div className="flex-row">
              <div style={{ flex: 2 }}>
                <label>Name</label>
                <input value={newExperiment.name} onChange={(e) => setNewExperiment({ ...newExperiment, name: e.target.value })} />
                <label>Description</label>
                <textarea
                  value={newExperiment.description}
                  onChange={(e) => setNewExperiment({ ...newExperiment, description: e.target.value })}
                />
                <div className="flex-row">
                  <div style={{ flex: 1 }}>
                    <label>Provider</label>
                    <select
                      value={newExperiment.provider}
                      onChange={(e) => setNewExperiment({ ...newExperiment, provider: e.target.value })}
                    >
                      {providerOptions.map((p) => (
                        <option key={p.value} value={p.value}>
                          {p.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div style={{ flex: 1 }}>
                    <label>Model</label>
                    <input value={newExperiment.model} onChange={(e) => setNewExperiment({ ...newExperiment, model: e.target.value })} />
                  </div>
                </div>
                <div className="flex-row">
                  <div style={{ flex: 1 }}>
                    <label>Temperature</label>
                    <input
                      type="number"
                      value={newExperiment.temperature}
                      onChange={(e) => setNewExperiment({ ...newExperiment, temperature: Number(e.target.value) })}
                    />
                  </div>
                  <div style={{ flex: 1 }}>
                    <label>Number of Runs</label>
                    <input
                      type="number"
                      value={newExperiment.runs}
                      onChange={(e) => setNewExperiment({ ...newExperiment, runs: Number(e.target.value) })}
                    />
                  </div>
                </div>
              </div>
              <div style={{ flex: 1 }}>
                <label>Select Exercises</label>
                <div>
                  {exercises.map((ex) => (
                    <div key={ex.id}>
                      <input
                        type="checkbox"
                        checked={newExperiment.exercise_ids.includes(ex.id)}
                        onChange={() => toggleExerciseSelection(ex.id)}
                        id={`ex-${ex.id}`}
                      />
                      <label htmlFor={`ex-${ex.id}`}>
                        #{ex.id} {ex.question_text.slice(0, 50)} ({ex.answer_type})
                      </label>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            {expError && <p style={{ color: 'red' }}>{expError}</p>}
            <button className="primary" onClick={startExperiment}>Start Experiment</button>
          </section>

          <section>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2>Experiments</h2>
              <button className="secondary" onClick={() => exportCsv(experiments, 'experiments.csv')}>
                Export CSV
              </button>
            </div>
            <table className="table-grid">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Name</th>
                  <th>Provider</th>
                  <th>Model</th>
                  <th>Temp</th>
                  <th>Runs</th>
                  <th>Completed</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {experiments.map((exp) => (
                  <tr
                    key={exp.id}
                    style={{ cursor: 'pointer', background: selectedExperimentId === exp.id ? '#e0f2fe' : 'white' }}
                    onClick={() => setSelectedExperimentId(exp.id)}
                  >
                    <td>{exp.id}</td>
                    <td>{exp.name}</td>
                    <td>{exp.provider}</td>
                    <td>{exp.model}</td>
                    <td>{exp.temperature}</td>
                    <td>{exp.runs}</td>
                    <td>{exp.completed_runs}</td>
                    <td>{exp.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          {selectedExperimentId && (
            <section>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h2>Exercises in Experiment #{selectedExperimentId}</h2>
                <button className="secondary" onClick={() => exportCsv(experimentExercises, 'experiment_exercises.csv')}>
                  Export CSV
                </button>
              </div>
              <table className="table-grid">
                <thead>
                  <tr>
                    <th>Exercise ID</th>
                    <th>Question</th>
                    <th>Answer Type</th>
                    <th>Completed Items</th>
                  </tr>
                </thead>
                <tbody>
                  {experimentExercises.map((ex) => (
                    <tr
                      key={ex.exercise_id}
                      style={{ cursor: 'pointer', background: selectedExperimentExerciseId === ex.exercise_id ? '#e0f2fe' : 'white' }}
                      onClick={() => setSelectedExperimentExerciseId(ex.exercise_id)}
                    >
                      <td>{ex.exercise_id}</td>
                      <td>{ex.question_text}</td>
                      <td>{ex.answer_type}</td>
                      <td>{ex.completed_items}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}

          {selectedExperimentExerciseId && (
            <section>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h2>Batch Items for Exercise #{selectedExperimentExerciseId}</h2>
                <button className="secondary" onClick={() => exportCsv(batchItems, 'batch_items.csv')}>
                  Export CSV
                </button>
              </div>
              <table className="table-grid">
                <thead>
                  <tr>
                    <th>Run Index</th>
                    <th>Parse Success</th>
                    <th>Answer</th>
                  </tr>
                </thead>
                <tbody>
                  {batchItems.map((item) => (
                    <tr key={item.id}>
                      <td>{item.run_index}</td>
                      <td>{item.parse_success ? 'Yes' : 'No'}</td>
                      <td>{typeof item.answer === 'object' ? JSON.stringify(item.answer) : String(item.answer)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}
        </div>
      )}
    </div>
  )
}

export default App

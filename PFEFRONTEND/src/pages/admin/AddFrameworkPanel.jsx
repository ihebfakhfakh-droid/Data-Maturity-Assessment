import { useMemo, useState } from 'react'
import { Layers3, Plus } from 'lucide-react'
import {
  DOMAIN_SCORING_METHODS,
  FRAMEWORK_SCORE_SCALES,
  createMaturityFramework,
  slugFrameworkCode,
} from '../../api/frameworkApi.js'
import { BtnIcon, SectionHeading } from '../../ui/IconBox.jsx'

function newLocalKey() {
  return `k-${crypto.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`}`
}

function emptyQuestion() {
  return { key: newLocalKey(), code: '', text: '' }
}

function emptySubDomain() {
  return { key: newLocalKey(), code: '', name: '', weight: 1, questions: [emptyQuestion()] }
}

function emptyDomain() {
  return {
    key: newLocalKey(),
    code: '',
    name: '',
    weight: 1,
    questions: [emptyQuestion()],
    subDomains: [emptySubDomain()],
  }
}

function mapQuestions(questions, codePrefix, sortBase = 0) {
  return (questions ?? [])
    .map((q, index) => {
      const text = String(q.text ?? '').trim()
      if (!text) return null
      const code =
        slugFrameworkCode(q.code) ||
        slugFrameworkCode(`${codePrefix}_q${index + 1}`, { maxLength: 120 })
      if (!code) return null
      return { code, text, sortOrder: sortBase + index }
    })
    .filter(Boolean)
}

function mapDomain(domain, index, parentPrefix = '') {
  const title = String(domain.name ?? '').trim()
  const code =
    slugFrameworkCode(domain.code) ||
    slugFrameworkCode(parentPrefix ? `${parentPrefix}_d${index + 1}` : `domain_${index + 1}`)
  const questions = mapQuestions(domain.questions, code, 0)
  const subDomains = (domain.subDomains ?? [])
    .map((sd, sdi) => {
      const subTitle = String(sd.name ?? '').trim()
      if (!subTitle && !(sd.questions ?? []).some((q) => String(q.text ?? '').trim())) return null
      return mapDomain({ ...sd, name: subTitle || `Sub-domain ${sdi + 1}` }, sdi, code)
    })
    .filter(Boolean)

  return {
    code,
    title,
    sortOrder: index,
    weight: domain.weight == null || domain.weight === '' ? null : Number(domain.weight),
    questions,
    subDomains,
  }
}

function buildCreatePayload(state) {
  const name = state.frameworkName.trim()
  const code = slugFrameworkCode(state.frameworkCode) || slugFrameworkCode(name)
  return {
    code,
    name,
    domainScoringMethod: state.domainScoringMethod,
    scoreScale: state.scoreScale,
    domains: state.domains.map((domain, index) => mapDomain(domain, index)),
  }
}

function validate(state) {
  const name = state.frameworkName.trim()
  if (!name) return 'Framework name is required.'

  const code = slugFrameworkCode(state.frameworkCode) || slugFrameworkCode(name)
  if (!code) return 'Framework code is required (lowercase letters, digits, underscore).'
  if (!/^[a-z0-9][a-z0-9_]{0,79}$/.test(code)) {
    return 'Framework code must match: lowercase letters, digits, underscore (max 80).'
  }
  if (code === 'ndi' || code === 'cmmi') {
    return 'Framework code is reserved (ndi / cmmi).'
  }

  if (!state.domainScoringMethod) return 'Select a domain scoring method.'
  if (!state.scoreScale) return 'Select a score scale.'
  if (state.domains.length === 0) return 'Add at least one domain.'

  for (let i = 0; i < state.domains.length; i++) {
    const d = state.domains[i]
    if (!d.name.trim()) return `Domain ${i + 1}: name is required.`
    for (let j = 0; j < d.subDomains.length; j++) {
      const sd = d.subDomains[j]
      const hasQuestion = (sd.questions ?? []).some((q) => String(q.text ?? '').trim())
      if (!sd.name.trim() && hasQuestion) {
        return `Domain "${d.name.trim()}": sub-domain ${j + 1} needs a name.`
      }
    }
  }

  const payload = buildCreatePayload(state)
  let questionCount = 0
  const walk = (domains) => {
    for (const d of domains ?? []) {
      questionCount += (d.questions ?? []).length
      walk(d.subDomains)
    }
  }
  walk(payload.domains)
  if (questionCount === 0) {
    return 'Add at least one question on a domain or a sub-domain (non-empty text).'
  }

  return null
}

export function AddFrameworkPanel({ token }) {
  const [frameworkName, setFrameworkName] = useState('')
  const [frameworkCode, setFrameworkCode] = useState('')
  const [domainScoringMethod, setDomainScoringMethod] = useState('DOMAIN_AVERAGE')
  const [scoreScale, setScoreScale] = useState('ZERO_TO_FIVE')
  const [domains, setDomains] = useState([emptyDomain()])
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const state = useMemo(
    () => ({ frameworkName, frameworkCode, domainScoringMethod, scoreScale, domains }),
    [frameworkName, frameworkCode, domainScoringMethod, scoreScale, domains],
  )

  function addDomain() {
    setDomains((prev) => [...prev, emptyDomain()])
  }

  function removeDomain(domainKey) {
    setDomains((prev) => (prev.length <= 1 ? prev : prev.filter((d) => d.key !== domainKey)))
  }

  function updateDomain(domainKey, patch) {
    setDomains((prev) => prev.map((d) => (d.key === domainKey ? { ...d, ...patch } : d)))
  }

  function addDomainQuestion(domainKey) {
    setDomains((prev) =>
      prev.map((d) => (d.key === domainKey ? { ...d, questions: [...d.questions, emptyQuestion()] } : d)),
    )
  }

  function removeDomainQuestion(domainKey, qKey) {
    setDomains((prev) =>
      prev.map((d) => {
        if (d.key !== domainKey) return d
        const next = d.questions.filter((q) => q.key !== qKey)
        return { ...d, questions: next.length ? next : [emptyQuestion()] }
      }),
    )
  }

  function updateDomainQuestion(domainKey, qKey, patch) {
    setDomains((prev) =>
      prev.map((d) => {
        if (d.key !== domainKey) return d
        return {
          ...d,
          questions: d.questions.map((q) => (q.key === qKey ? { ...q, ...patch } : q)),
        }
      }),
    )
  }

  function addSubDomain(domainKey) {
    setDomains((prev) =>
      prev.map((d) => (d.key === domainKey ? { ...d, subDomains: [...d.subDomains, emptySubDomain()] } : d)),
    )
  }

  function removeSubDomain(domainKey, sdKey) {
    setDomains((prev) =>
      prev.map((d) => {
        if (d.key !== domainKey) return d
        const next = d.subDomains.filter((sd) => sd.key !== sdKey)
        return { ...d, subDomains: next.length ? next : [emptySubDomain()] }
      }),
    )
  }

  function updateSubDomain(domainKey, sdKey, patch) {
    setDomains((prev) =>
      prev.map((d) => {
        if (d.key !== domainKey) return d
        return {
          ...d,
          subDomains: d.subDomains.map((sd) => (sd.key === sdKey ? { ...sd, ...patch } : sd)),
        }
      }),
    )
  }

  function addSubQuestion(domainKey, sdKey) {
    setDomains((prev) =>
      prev.map((d) => {
        if (d.key !== domainKey) return d
        return {
          ...d,
          subDomains: d.subDomains.map((sd) =>
            sd.key === sdKey ? { ...sd, questions: [...sd.questions, emptyQuestion()] } : sd,
          ),
        }
      }),
    )
  }

  function removeSubQuestion(domainKey, sdKey, qKey) {
    setDomains((prev) =>
      prev.map((d) => {
        if (d.key !== domainKey) return d
        return {
          ...d,
          subDomains: d.subDomains.map((sd) => {
            if (sd.key !== sdKey) return sd
            const next = sd.questions.filter((q) => q.key !== qKey)
            return { ...sd, questions: next.length ? next : [emptyQuestion()] }
          }),
        }
      }),
    )
  }

  function updateSubQuestion(domainKey, sdKey, qKey, patch) {
    setDomains((prev) =>
      prev.map((d) => {
        if (d.key !== domainKey) return d
        return {
          ...d,
          subDomains: d.subDomains.map((sd) => {
            if (sd.key !== sdKey) return sd
            return {
              ...sd,
              questions: sd.questions.map((q) => (q.key === qKey ? { ...q, ...patch } : q)),
            }
          }),
        }
      }),
    )
  }

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    setSuccess('')
    const v = validate(state)
    if (v) {
      setError(v)
      return
    }
    setSubmitting(true)
    try {
      const body = buildCreatePayload(state)
      await createMaturityFramework(token, body)
      setSuccess('Framework created successfully.')
      setFrameworkName('')
      setFrameworkCode('')
      setDomainScoringMethod('DOMAIN_AVERAGE')
      setScoreScale('ZERO_TO_FIVE')
      setDomains([emptyDomain()])
    } catch (err) {
      setError(err?.message ?? 'Could not create framework')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="teamLayout">
      <section className="sectionCard">
        <div className="sectionHeader">
          <SectionHeading
            icon={Layers3}
            title="Add Framework"
            subtitle="Define evaluation domains, optional sub-domains, and questions. Domain scoring and score scale follow the backend maturity-framework contract."
          />
        </div>

        {error ? <div className="alert alertError">{error}</div> : null}
        {success ? <div className="alert alertSuccess">{success}</div> : null}

        <form className="form" onSubmit={onSubmit}>
          <div className="formSection">
            <div className="formSectionHeader">
              <span className="formSectionEyebrow">Framework settings</span>
              <h3 className="formSectionTitle">General information</h3>
            </div>
            <div className="frameworkGeneralGrid">
              <label className="field frameworkGeneralField">
                <span className="label">Framework name</span>
                <input
                  className="input"
                  value={frameworkName}
                  onChange={(e) => setFrameworkName(e.target.value)}
                  required
                  placeholder="e.g. Custom maturity"
                />
              </label>
              <label className="field frameworkGeneralField">
                <span className="label">Framework code</span>
                <input
                  className="input"
                  value={frameworkCode}
                  onChange={(e) => setFrameworkCode(e.target.value)}
                  placeholder="auto from name if empty (e.g. custom_maturity)"
                />
                <span className="tinyNote">Lowercase letters, digits, underscore. Reserved: ndi, cmmi.</span>
              </label>
              <label className="field frameworkGeneralField">
                <span className="label">Domain scoring method</span>
                <select
                  className="select"
                  value={domainScoringMethod}
                  onChange={(e) => setDomainScoringMethod(e.target.value)}
                >
                  {DOMAIN_SCORING_METHODS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
                <div className="frameworkMethodHelp">
                  <ul>
                    <li>
                      <strong>Domain minimum:</strong> uses the lowest question score in the domain.
                    </li>
                    <li>
                      <strong>Domain average:</strong> uses the mean of question scores in the domain.
                    </li>
                  </ul>
                </div>
              </label>
              <label className="field frameworkGeneralField">
                <span className="label">Score scale</span>
                <select className="select" value={scoreScale} onChange={(e) => setScoreScale(e.target.value)}>
                  {FRAMEWORK_SCORE_SCALES.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </div>

          <div className="frameworkBuilderList">
            {domains.map((domain, di) => (
              <div key={domain.key} className="frameworkDomainCard">
                <div className="frameworkDomainHead">
                  <h3 className="frameworkBlockTitle">Domain {di + 1}</h3>
                  <button
                    type="button"
                    className="btn btnDanger btnSm"
                    onClick={() => removeDomain(domain.key)}
                    disabled={domains.length <= 1}
                  >
                    Remove domain
                  </button>
                </div>

                <div className="fieldRow">
                  <label className="field">
                    <span className="label">Domain name</span>
                    <input
                      className="input"
                      value={domain.name}
                      onChange={(e) => updateDomain(domain.key, { name: e.target.value })}
                      required
                      placeholder="Domain label"
                    />
                  </label>
                  <label className="field">
                    <span className="label">Domain code (optional)</span>
                    <input
                      className="input"
                      value={domain.code}
                      onChange={(e) => updateDomain(domain.key, { code: e.target.value })}
                      placeholder="auto if empty"
                    />
                  </label>
                  <label className="field frameworkWeightField">
                    <span className="label">Weight</span>
                    <input
                      className="input"
                      type="number"
                      min={0}
                      step={0.01}
                      value={domain.weight ?? 1}
                      onChange={(e) =>
                        updateDomain(domain.key, {
                          weight: Number(e.target.value) || 1,
                        })
                      }
                    />
                  </label>
                </div>

                <div className="frameworkSubSection">
                  <div className="frameworkSubSectionHead">
                    <span className="label" style={{ margin: 0 }}>
                      Questions for this domain
                    </span>
                    <button type="button" className="btn btnGhost btnSm" onClick={() => addDomainQuestion(domain.key)}>
                      Add question
                    </button>
                  </div>
                  <div className="frameworkQuestionList">
                    {domain.questions.map((q) => (
                      <div key={q.key} className="frameworkQuestionRow">
                        <label className="field" style={{ flex: '0 0 140px' }}>
                          <span className="label">Code</span>
                          <input
                            className="input"
                            value={q.code}
                            onChange={(e) => updateDomainQuestion(domain.key, q.key, { code: e.target.value })}
                            placeholder="auto"
                          />
                        </label>
                        <label className="field" style={{ flex: 1, minWidth: 0 }}>
                          <span className="label">Question</span>
                          <input
                            className="input"
                            value={q.text}
                            onChange={(e) => updateDomainQuestion(domain.key, q.key, { text: e.target.value })}
                            placeholder="Question text"
                          />
                        </label>
                        <button
                          type="button"
                          className="btn btnGhost btnSm frameworkQRemove"
                          onClick={() => removeDomainQuestion(domain.key, q.key)}
                          disabled={domain.questions.length <= 1}
                          aria-label="Remove question"
                        >
                          Remove
                        </button>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="frameworkSubSection">
                  <div className="frameworkSubSectionHead">
                    <span className="label" style={{ margin: 0 }}>
                      Sub-domains
                    </span>
                    <button type="button" className="btn btnGhost btnSm" onClick={() => addSubDomain(domain.key)}>
                      Add sub-domain
                    </button>
                  </div>

                  {domain.subDomains.map((sd, sdi) => (
                    <div key={sd.key} className="frameworkSubDomainCard">
                      <div className="frameworkDomainHead">
                        <h4 className="frameworkBlockTitleSm">Sub-domain {sdi + 1}</h4>
                        <button
                          type="button"
                          className="btn btnDanger btnSm"
                          onClick={() => removeSubDomain(domain.key, sd.key)}
                          disabled={domain.subDomains.length <= 1}
                        >
                          Remove
                        </button>
                      </div>
                      <div className="fieldRow">
                        <label className="field">
                          <span className="label">Sub-domain name</span>
                          <input
                            className="input"
                            value={sd.name}
                            onChange={(e) => updateSubDomain(domain.key, sd.key, { name: e.target.value })}
                            placeholder="Sub-domain label"
                          />
                        </label>
                        <label className="field">
                          <span className="label">Code (optional)</span>
                          <input
                            className="input"
                            value={sd.code}
                            onChange={(e) => updateSubDomain(domain.key, sd.key, { code: e.target.value })}
                            placeholder="auto if empty"
                          />
                        </label>
                        <label className="field frameworkWeightField">
                          <span className="label">Weight</span>
                          <input
                            className="input"
                            type="number"
                            min={0}
                            step={0.01}
                            value={sd.weight ?? 1}
                            onChange={(e) =>
                              updateSubDomain(domain.key, sd.key, {
                                weight: Number(e.target.value) || 1,
                              })
                            }
                          />
                        </label>
                      </div>

                      <div className="frameworkSubSectionHead" style={{ marginTop: 10 }}>
                        <span className="label" style={{ margin: 0 }}>
                          Questions for this sub-domain
                        </span>
                        <button
                          type="button"
                          className="btn btnGhost btnSm"
                          onClick={() => addSubQuestion(domain.key, sd.key)}
                        >
                          Add question
                        </button>
                      </div>
                      <div className="frameworkQuestionList">
                        {sd.questions.map((q) => (
                          <div key={q.key} className="frameworkQuestionRow">
                            <label className="field" style={{ flex: '0 0 140px' }}>
                              <span className="label">Code</span>
                              <input
                                className="input"
                                value={q.code}
                                onChange={(e) => updateSubQuestion(domain.key, sd.key, q.key, { code: e.target.value })}
                                placeholder="auto"
                              />
                            </label>
                            <label className="field" style={{ flex: 1, minWidth: 0 }}>
                              <span className="label">Question</span>
                              <input
                                className="input"
                                value={q.text}
                                onChange={(e) => updateSubQuestion(domain.key, sd.key, q.key, { text: e.target.value })}
                                placeholder="Question text"
                              />
                            </label>
                            <button
                              type="button"
                              className="btn btnGhost btnSm frameworkQRemove"
                              onClick={() => removeSubQuestion(domain.key, sd.key, q.key)}
                              disabled={sd.questions.length <= 1}
                              aria-label="Remove question"
                            >
                              Remove
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginTop: 8 }}>
            <button type="button" className="btn btnGhost btnWithIcon" onClick={addDomain}>
              <BtnIcon icon={Plus} />
              Add domain
            </button>
            <button type="submit" className="btn btnPrimary btnWithIcon" disabled={submitting}>
              <BtnIcon icon={Layers3} />
              {submitting ? 'Saving…' : 'Save Framework'}
            </button>
          </div>
        </form>
      </section>
    </div>
  )
}

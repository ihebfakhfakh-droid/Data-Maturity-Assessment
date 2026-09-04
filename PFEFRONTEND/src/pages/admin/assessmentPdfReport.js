function frameworkKeyFromSegmentForPdf(seg, fallbackKey = 'framework') {
  const raw = `${seg?.segmentCode ?? ''} ${seg?.segmentTitle ?? ''}`.toLowerCase()
  if (raw.includes('cmmi')) return 'cmmi'
  if (raw.includes('ndi')) return 'ndi'
  return fallbackKey
}

function frameworkLabelFromKeyForPdf(key) {
  if (key === 'ndi') return 'NDI'
  if (key === 'cmmi') return 'CMMI'
  return String(key ?? 'Framework').toUpperCase()
}

function answerForPdf(ans) {
  return {
    text: ans?.questionText ?? ans?.questionCode ?? 'Question',
    score: ans?.score,
    answeredAt: ans?.answeredAt,
  }
}

export function frameworksForAssessmentPdf(assessment) {
  const segments = assessment?.segments ?? []
  const frameworkAverages = assessment?.frameworkAverages ?? []
  const frameworkAvg = assessment?.frameworkAvg ?? null
  const frameworkAverageScore = assessment?.frameworkAverageScore ?? assessment?.globalAverageScore ?? null
  const groups = new Map()

  for (const seg of segments) {
    const key = frameworkKeyFromSegmentForPdf(seg, frameworkAverages[0]?.key ?? 'framework')
    if (!groups.has(key)) {
      const frameworkSummary = frameworkAverages.find((item) => item.key === key)
      const avg = frameworkSummary?.avg ?? frameworkAvg
      groups.set(key, {
        label: frameworkLabelFromKeyForPdf(key),
        globalScore: avg,
        overallAverageScore: frameworkSummary?.averageScore ?? frameworkAverageScore,
        domains: [],
      })
    }
    groups.get(key).domains.push({
      title: seg.segmentTitle ?? seg.segmentCode ?? 'Domain',
      score: seg.score,
      questions: (seg.answers ?? []).map(answerForPdf),
      subdomains: (seg.subDomains ?? [])
        .filter((sub) => (sub.answers ?? []).length > 0)
        .map((sub) => ({
          name: sub.name ?? 'Subdomain',
          questions: (sub.answers ?? []).map(answerForPdf),
        })),
    })
  }

  return [...groups.values()]
}

export function buildAdminAssessmentPdfReport({ clientName, assessment }) {
  return {
    clientName,
    year: assessment?.year,
    version: assessment?.version ?? assessment?.versionNumber,
    status: 'SUBMITTED',
    submittedAt: assessment?.submittedAt,
    frameworks: frameworksForAssessmentPdf(assessment),
  }
}

function text(value, fallback = '—') {
  const next = String(value ?? '').trim()
  return next || fallback
}

function score(value) {
  return value === null || value === undefined || value === '' ? '—' : `${value} / 5`
}

function numericScore(value) {
  if (value === null || value === undefined || value === '') return null
  const next = Number(value)
  return Number.isFinite(next) ? Math.max(0, Math.min(5, next)) : null
}

function formatDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return text(value)
  return date.toLocaleString()
}

function safeFilePart(value) {
  return String(value ?? 'assessment')
    .trim()
    .replaceAll(/[^a-zA-Z0-9._-]+/g, '_')
    .replaceAll(/^_+|_+$/g, '')
    .slice(0, 80) || 'assessment'
}

export function isSubmittedAssessment(assessment) {
  return String(assessment?.status ?? '').toUpperCase() === 'SUBMITTED'
}

export async function exportAssessmentPdf(report) {
  const { jsPDF } = await import('jspdf')
  const doc = new jsPDF({ unit: 'pt', format: 'a4' })
  const page = {
    width: doc.internal.pageSize.getWidth(),
    height: doc.internal.pageSize.getHeight(),
    marginX: 42,
    marginY: 44,
  }
  const maxWidth = page.width - page.marginX * 2
  let y = page.marginY

  function remainingHeight() {
    return page.height - page.marginY - y
  }

  function addPage() {
    doc.addPage()
    y = page.marginY
  }

  function ensureSpace(height = 18) {
    if (y + height <= page.height - page.marginY) return
    addPage()
  }

  function writeLine(value = '', options = {}) {
    const {
      size = 10,
      style = 'normal',
      gap = 14,
      indent = 0,
      color = [40, 40, 45],
    } = options
    doc.setFont('helvetica', style)
    doc.setFontSize(size)
    doc.setTextColor(...color)
    const lines = doc.splitTextToSize(text(value, ''), maxWidth - indent)
    ensureSpace(Math.max(lines.length, 1) * gap)
    doc.text(lines.length ? lines : [''], page.marginX + indent, y)
    y += Math.max(lines.length, 1) * gap
  }

  function writeGap(size = 8) {
    y += size
  }

  function radarChartHeight(options = {}) {
    return (options.chartHeight ?? 235) + 12
  }

  function questionChartHeight(rows, options = {}) {
    return (rows ?? []).length > 0 ? radarChartHeight(options) : 0
  }

  function estimatedLineHeight(value, indent = 0, gap = 14) {
    const lines = doc.splitTextToSize(text(value, ''), maxWidth - indent)
    return Math.max(lines.length, 1) * gap
  }

  function estimateQuestionBlockHeight(question, indent = 18) {
    const questionLine = `Question 1 : ${text(question.text)}`
    return (
      estimatedLineHeight(questionLine, indent) +
      estimatedLineHeight(`Score : ${score(question.score)}`, indent + 10) +
      estimatedLineHeight(`Answered at : ${formatDate(question.answeredAt)}`, indent + 10)
    )
  }

  function writeQuestionBlock(questionIndex, question, indent = 18) {
    const questionLine = `Question ${questionIndex + 1} : ${text(question.text)}`
    const neededHeight =
      estimatedLineHeight(questionLine, indent) +
      estimatedLineHeight(`Score : ${score(question.score)}`, indent + 10) +
      estimatedLineHeight(`Answered at : ${formatDate(question.answeredAt)}`, indent + 10)

    ensureSpace(neededHeight)
    writeLine(questionLine, { size: 10, indent })
    writeLine(`Score : ${score(question.score)}`, { size: 10, indent: indent + 10 })
    writeLine(`Answered at : ${formatDate(question.answeredAt)}`, { size: 9, indent: indent + 10, color: [95, 95, 100] })
  }

  function estimateDomainBlockHeight(domain, domainIndex) {
    let height = 0
    height += estimatedLineHeight(`Domain ${domainIndex + 1} : ${text(domain.title)}`, 0, 16)
    height += estimatedLineHeight(`Score domain : ${score(domain.score)}`, 12)

    const directQuestions = domain.questions ?? []
    for (const question of directQuestions) {
      height += estimateQuestionBlockHeight(question, 18)
    }
    height += questionChartHeight(directQuestions, { indent: 12 })

    for (const [subIndex, subdomain] of (domain.subdomains ?? []).entries()) {
      height += estimatedLineHeight(`Subdomain ${domainIndex + 1}.${subIndex + 1} : ${text(subdomain.name)}`, 14)
      const subdomainQuestions = subdomain.questions ?? []
      for (const question of subdomainQuestions) {
        height += estimateQuestionBlockHeight(question, 24)
      }
      height += questionChartHeight(subdomainQuestions, { indent: 24 })
    }

    height += 6
    return height
  }

  function ensureDomainStart(domain, domainIndex) {
    const fullDomainHeight = estimateDomainBlockHeight(domain, domainIndex)
    const fullPageCapacity = page.height - page.marginY * 2
    const minUsefulStartHeight = Math.min(fullDomainHeight, fullPageCapacity)
    if (remainingHeight() < minUsefulStartHeight) {
      addPage()
    }
  }

  function chartValuesForRows(rows) {
    return (rows ?? [])
      .map((row, index) => ({
        label: text(row.label ?? row.title ?? row.text ?? `Q${index + 1}`, `Q${index + 1}`),
        value: numericScore(row.score),
      }))
      .filter((row) => row.value !== null)
  }

  function drawRadarChart(title, rows, options = {}) {
    const values = chartValuesForRows(rows)

    if (values.length === 0) {
      writeLine(`${title} : no scored data available.`, { size: 9, indent: options.indent ?? 12, color: [95, 95, 100] })
      writeGap(4)
      return
    }

    const chartWidth = Math.min(maxWidth - (options.indent ?? 0), options.chartWidth ?? 430)
    const chartHeight = options.chartHeight ?? 235
    const left = page.marginX + (options.indent ?? 0)
    const neededHeight = radarChartHeight(options)
    const centerX = left + chartWidth / 2
    const centerY = y + (options.centerOffsetY ?? chartHeight / 2)
    const radius = options.radius ?? 72
    const angleOffset = -Math.PI / 2

    ensureSpace(neededHeight)
    doc.setFont('helvetica', 'bold')
    doc.setFontSize(10)
    doc.setTextColor(40, 40, 45)
    doc.text(title, left, y + 10)

    const pointAt = (index, valueRadius) => {
      const angle = angleOffset + (Math.PI * 2 * index) / values.length
      return {
        x: centerX + Math.cos(angle) * valueRadius,
        y: centerY + Math.sin(angle) * valueRadius,
      }
    }

    doc.setLineWidth(0.45)
    for (let level = 1; level <= 5; level += 1) {
      const levelRadius = (radius * level) / 5
      doc.setDrawColor(level === 5 ? 205 : 232, level === 5 ? 210 : 235, level === 5 ? 218 : 240)
      const first = pointAt(0, levelRadius)
      let previous = first
      for (let index = 1; index < values.length; index += 1) {
        const current = pointAt(index, levelRadius)
        doc.line(previous.x, previous.y, current.x, current.y)
        previous = current
      }
      if (values.length > 1) doc.line(previous.x, previous.y, first.x, first.y)
      doc.setFont('helvetica', 'normal')
      doc.setFontSize(7)
      doc.setTextColor(120, 120, 126)
      doc.text(String(level), centerX + 4, centerY - levelRadius + 3)
    }

    values.forEach((row, index) => {
      const axisEnd = pointAt(index, radius)
      doc.setDrawColor(225, 228, 234)
      doc.line(centerX, centerY, axisEnd.x, axisEnd.y)

      const labelPoint = pointAt(index, radius + 22)
      const shortLabel = row.label.length > 16 ? `${row.label.slice(0, 15)}…` : row.label
      doc.setFont('helvetica', 'normal')
      doc.setFontSize(7)
      doc.setTextColor(75, 75, 82)
      doc.text(shortLabel, labelPoint.x, labelPoint.y, {
        align: labelPoint.x < centerX - 8 ? 'right' : labelPoint.x > centerX + 8 ? 'left' : 'center',
        maxWidth: 70,
      })
    })

    const dataPoints = values.map((row, index) => pointAt(index, (radius * row.value) / 5))
    doc.setDrawColor(248, 72, 94)
    doc.setLineWidth(1.2)
    for (let index = 0; index < dataPoints.length; index += 1) {
      const current = dataPoints[index]
      const next = dataPoints[(index + 1) % dataPoints.length]
      if (dataPoints.length > 1) doc.line(current.x, current.y, next.x, next.y)
    }

    dataPoints.forEach((point, index) => {
      doc.setFillColor(248, 72, 94)
      doc.circle(point.x, point.y, 2.6, 'F')
      doc.setFont('helvetica', 'normal')
      doc.setFontSize(7)
      doc.setTextColor(40, 40, 45)
      doc.text(String(values[index].value), point.x + 4, point.y - 4)
    })

    doc.setFont('helvetica', 'normal')
    doc.setFontSize(8)
    doc.setTextColor(95, 95, 100)
    doc.text('Radar scale: 0 to 5', left, y + chartHeight - 8)
    y += neededHeight
  }

  function drawBarChart(title, rows, options = {}) {
    const values = chartValuesForRows(rows)

    if (values.length === 0) {
      writeLine(`${title} : no scored data available.`, { size: 9, indent: options.indent ?? 12, color: [95, 95, 100] })
      writeGap(4)
      return
    }

    const chartWidth = Math.min(maxWidth - (options.indent ?? 0), options.chartWidth ?? 430)
    const chartHeight = options.chartHeight ?? 235
    const left = page.marginX + (options.indent ?? 0)
    const neededHeight = radarChartHeight(options)
    const plotLeft = left + 38
    const plotTop = y + 34
    const plotWidth = chartWidth - 54
    const plotHeight = chartHeight - 74
    const baselineY = plotTop + plotHeight

    ensureSpace(neededHeight)
    doc.setFont('helvetica', 'bold')
    doc.setFontSize(10)
    doc.setTextColor(40, 40, 45)
    doc.text(title, left, y + 10)

    doc.setLineWidth(0.45)
    doc.setFont('helvetica', 'normal')
    doc.setFontSize(7)
    for (let tick = 0; tick <= 5; tick += 1) {
      const tickY = baselineY - (plotHeight * tick) / 5
      doc.setDrawColor(tick === 0 ? 190 : 226, tick === 0 ? 196 : 232, tick === 0 ? 205 : 238)
      doc.line(plotLeft, tickY, plotLeft + plotWidth, tickY)
      doc.setTextColor(120, 120, 126)
      doc.text(String(tick), plotLeft - 14, tickY + 2)
    }

    const slotWidth = plotWidth / values.length
    const barWidth = Math.min(64, slotWidth * 0.45)
    values.forEach((row, index) => {
      const barHeight = (plotHeight * row.value) / 5
      const x = plotLeft + slotWidth * index + (slotWidth - barWidth) / 2
      const yTop = baselineY - barHeight
      doc.setFillColor(20, 184, 166)
      doc.rect(x, yTop, barWidth, barHeight, 'F')

      doc.setFont('helvetica', 'bold')
      doc.setFontSize(7)
      doc.setTextColor(40, 40, 45)
      doc.text(String(row.value), x + barWidth / 2, yTop - 5, { align: 'center' })

      const shortLabel = row.label.length > 18 ? `${row.label.slice(0, 17)}…` : row.label
      doc.setFont('helvetica', 'normal')
      doc.setFontSize(7)
      doc.setTextColor(75, 75, 82)
      doc.text(shortLabel, x + barWidth / 2, baselineY + 14, { align: 'center', maxWidth: slotWidth - 4 })
    })

    doc.setFont('helvetica', 'normal')
    doc.setFontSize(8)
    doc.setTextColor(95, 95, 100)
    doc.text('Bar chart scale: 0 to 5', left, y + chartHeight - 8)
    y += neededHeight
  }

  function drawQuestionScoreChart(title, rows, options = {}) {
    const questionCount = (rows ?? []).length
    if (questionCount === 0) return
    if (questionCount <= 2) {
      drawBarChart(title.replace(/^Radar Chart/u, 'Bar Chart'), rows, options)
      return
    }
    drawRadarChart(title, rows, options)
  }

  doc.setProperties({ title: 'Assessment Report' })
  writeLine('Assessment Report', { size: 20, style: 'bold', gap: 24, color: [248, 72, 94] })
  writeLine(`Client : ${text(report.clientName)}`, { size: 11, style: 'bold' })
  writeLine(`Year : ${text(report.year)}`, { size: 11 })
  writeLine(`Version : ${text(report.version)}`, { size: 11 })
  writeLine(`Status : ${text(report.status)}`, { size: 11 })
  writeLine(`Submitted at : ${formatDate(report.submittedAt)}`, { size: 11 })
  writeGap(8)

  for (const [frameworkIndex, framework] of (report.frameworks ?? []).entries()) {
    if (frameworkIndex > 0) writeGap(10)
    writeLine(`Framework : ${text(framework.label)}`, { size: 15, style: 'bold', gap: 19 })
    writeLine(`Overall Score : ${score(framework.globalScore)}`, { size: 12, style: 'bold' })
    writeLine(`Overall Average Score : ${score(framework.overallAverageScore)}`, { size: 12, style: 'bold' })
    writeGap(4)

    for (const [domainIndex, domain] of (framework.domains ?? []).entries()) {
      ensureDomainStart(domain, domainIndex)
      writeLine(`Domain ${domainIndex + 1} : ${text(domain.title)}`, { size: 12, style: 'bold', gap: 16 })
      writeLine(`Score domain : ${score(domain.score)}`, { size: 10, indent: 12 })

      const directQuestions = domain.questions ?? []
      for (const [questionIndex, question] of directQuestions.entries()) {
        writeQuestionBlock(questionIndex, question, 18)
      }
      drawQuestionScoreChart(`Radar Chart Domain ${domainIndex + 1} : ${text(domain.title)}`, directQuestions, {
        indent: 12,
      })

      for (const [subIndex, subdomain] of (domain.subdomains ?? []).entries()) {
        writeLine(`Subdomain ${domainIndex + 1}.${subIndex + 1} : ${text(subdomain.name)}`, {
          size: 11,
          style: 'bold',
          indent: 14,
        })
        for (const [questionIndex, question] of (subdomain.questions ?? []).entries()) {
          writeQuestionBlock(questionIndex, question, 24)
        }
        drawQuestionScoreChart(
          `Radar Chart Subdomain ${domainIndex + 1}.${subIndex + 1} : ${text(subdomain.name)}`,
          subdomain.questions ?? [],
          {
            indent: 24,
          },
        )
      }

      writeGap(6)
    }

    addPage()
    drawRadarChart(
      `Overall Score Radar Chart : ${text(framework.label)}`,
      (framework.domains ?? []).map((domain, index) => ({
        label: domain.title ?? `Domain ${index + 1}`,
        score: domain.score,
      })),
      {
        chartHeight: 300,
        chartWidth: 470,
        centerOffsetY: 154,
        radius: 98,
      },
    )
  }

  const fileName = [
    'assessment-report',
    safeFilePart(report.clientName),
    safeFilePart(report.year),
    safeFilePart(report.version),
  ].filter(Boolean).join('-')
  doc.save(`${fileName}.pdf`)
}

function escapeHtml(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function safeHref(value: string) {
  const trimmed = value.trim()
  return /^(https?:\/\/|mailto:)/i.test(trimmed) ? trimmed.replace(/"/g, '%22') : ''
}

function renderInline(value: string) {
  let html = escapeHtml(value)
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>')
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>')
  html = html.replace(/\[([^\]]+)]\(([^)]+)\)/g, (_match, label: string, url: string) => {
    const href = safeHref(url)
    return href ? `<a href="${href}" target="_blank" rel="noopener noreferrer">${label}</a>` : label
  })
  return html
}

function tableCells(row: string) {
  const normalized = row.trim().replace(/^\|/, '').replace(/\|$/, '')
  return normalized ? normalized.split('|').map((cell) => cell.trim()) : []
}

function isTableRow(row: string) {
  return row.includes('|') && tableCells(row).length > 1
}
function isDivider(row: string) {
  const cells = tableCells(row)
  return cells.length > 0 && cells.every((cell) => /^:?-{3,}:?$/.test(cell))
}

export function renderMarkdownToHtml(markdown: string) {
  const output: string[] = []
  let list: 'ul' | 'ol' | null = null
  let code: string[] | null = null
  let table: string[] = []

  const closeList = () => {
    if (list) output.push(`</${list}>`)
    list = null
  }
  const flushCode = () => {
    if (code) output.push(`<pre><code>${escapeHtml(code.join('\n'))}</code></pre>`)
    code = null
  }
  const flushTable = () => {
    if (!table.length) return
    const headers = tableCells(table[0] || '')
    const start = table[1] && isDivider(table[1]) ? 2 : 1
    const head = `<thead><tr>${headers.map((cell) => `<th>${renderInline(cell)}</th>`).join('')}</tr></thead>`
    const body = table
      .slice(start)
      .map((row) => {
        const cells = tableCells(row)
        return `<tr>${headers.map((_header, index) => `<td>${renderInline(cells[index] || '')}</td>`).join('')}</tr>`
      })
      .join('')
    output.push(`<div class="md-table-wrap"><table>${head}<tbody>${body}</tbody></table></div>`)
    table = []
  }

  for (const rawLine of String(markdown || '')
    .replace(/\r\n/g, '\n')
    .split('\n')) {
    const line = rawLine.trim()
    if (line.startsWith('```')) {
      if (code) flushCode()
      else {
        flushTable()
        closeList()
        code = []
      }
      continue
    }
    if (code) {
      code.push(rawLine)
      continue
    }
    if (isTableRow(line)) {
      closeList()
      table.push(line)
      continue
    }
    flushTable()
    if (!line) {
      closeList()
      continue
    }

    const heading = line.match(/^(#{1,6})\s+(.+)$/)
    if (heading) {
      closeList()
      const level = heading[1]!.length
      output.push(`<h${level}>${renderInline(heading[2]!)}</h${level}>`)
      continue
    }
    if (/^---+$/.test(line)) {
      closeList()
      output.push('<hr />')
      continue
    }
    const unordered = line.match(/^[-*+]\s+(.+)$/)
    if (unordered) {
      if (list !== 'ul') {
        closeList()
        output.push('<ul>')
        list = 'ul'
      }
      output.push(`<li>${renderInline(unordered[1]!)}</li>`)
      continue
    }
    const ordered = line.match(/^\d+\.\s+(.+)$/)
    if (ordered) {
      if (list !== 'ol') {
        closeList()
        output.push('<ol>')
        list = 'ol'
      }
      output.push(`<li>${renderInline(ordered[1]!)}</li>`)
      continue
    }
    const quote = line.match(/^>\s?(.+)$/)
    if (quote) {
      closeList()
      output.push(`<blockquote>${renderInline(quote[1]!)}</blockquote>`)
      continue
    }
    closeList()
    output.push(`<p>${renderInline(line)}</p>`)
  }
  flushTable()
  flushCode()
  closeList()
  return output.join('\n')
}

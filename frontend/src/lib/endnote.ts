export interface ImportRecord {
  title: string
  authors: string
  journal: string
  year: number | null
  volume: string
  issue: string
  pages: string
  doi: string
  abstract: string
  keywords: string
  language: string
}

export function parseEndnote(content: string): ImportRecord[] {
  const records: ImportRecord[] = []
  const matches = content.match(/%0 (.+?)(?=%0 |$)/gs) || []
  for (const block of matches) {
    const record: ImportRecord = {
      title: '',
      authors: '',
      journal: '',
      year: null,
      volume: '',
      issue: '',
      pages: '',
      doi: '',
      abstract: '',
      keywords: '',
      language: 'zh',
    }
    for (const line of block.split('\n')) {
      const value = line.slice(2).trim()
      if (line.startsWith('%T')) record.title = value
      else if (line.startsWith('%A')) record.authors += `${record.authors ? ', ' : ''}${value}`
      else if (line.startsWith('%J')) record.journal = value
      else if (line.startsWith('%D')) record.year = Number.parseInt(value, 10) || null
      else if (line.startsWith('%V')) record.volume = value
      else if (line.startsWith('%N')) record.issue = value
      else if (line.startsWith('%P')) record.pages = value
      else if (line.startsWith('%R')) record.doi = value
      else if (line.startsWith('%X')) record.abstract += value
      else if (line.startsWith('%K')) record.keywords = value
    }
    if (record.title) records.push(record)
  }
  return records
}

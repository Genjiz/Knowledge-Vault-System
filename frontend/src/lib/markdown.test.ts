import { describe, expect, it } from 'vitest'
import { renderMarkdownToHtml } from './markdown'

describe('renderMarkdownToHtml', () => {
  it('renders headings, lists and tables', () => {
    const html = renderMarkdownToHtml('# 标题\n\n- 条目\n\n| A | B |\n| --- | --- |\n| 1 | 2 |')
    expect(html).toContain('<h1>标题</h1>')
    expect(html).toContain('<li>条目</li>')
    expect(html).toContain('<table>')
  })

  it('escapes raw HTML and drops unsafe links', () => {
    const html = renderMarkdownToHtml('<script>alert(1)</script> [危险](javascript:alert(1))')
    expect(html).not.toContain('<script>')
    expect(html).not.toContain('href="javascript:')
    expect(html).toContain('&lt;script&gt;')
  })
})

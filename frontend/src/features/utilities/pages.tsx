import { Link } from '@tanstack/react-router'
import { useState } from 'react'
import { toast } from 'sonner'
import { literatureApi } from '@/api/resources'
import { Button, Card, Field, Input, PageHero, PanelHeader, Select } from '@/components/ui'
import { downloadText } from '@/lib/utils'
import { parseEndnote, type ImportRecord } from '@/lib/endnote'

interface ImportResult {
  success: number
  failed: number
  items: Array<ImportRecord & { success: boolean; message: string }>
}
export function ImportPage() {
  const [mode, setMode] = useState('manual'),
    [file, setFile] = useState<File | null>(null),
    [working, setWorking] = useState(false),
    [result, setResult] = useState<ImportResult | null>(null)
  const run = async () => {
    if (!file) return toast.warning('请先选择文件')
    setWorking(true)
    const next: ImportResult = { success: 0, failed: 0, items: [] }
    try {
      for (const record of parseEndnote(await file.text())) {
        try {
          await literatureApi.create(record as unknown as Record<string, unknown>)
          next.success++
          next.items.push({ ...record, success: true, message: '导入成功' })
        } catch (error) {
          next.failed++
          next.items.push({
            ...record,
            success: false,
            message: error instanceof Error ? error.message : '导入失败',
          })
        }
      }
      setResult(next)
      toast.success(`导入完成：成功 ${next.success} 条`)
    } finally {
      setWorking(false)
    }
  }
  return (
    <div className="page-shell">
      <PageHero
        eyebrow="Intake Pipeline · Import"
        title="导入文献"
        description="支持手动录入以及 EndNote、NoteExpress 文本批量导入。"
        metrics={[
          { label: 'Current Mode', value: mode },
          { label: 'Imported', value: result?.success || 0 },
          { label: 'Failed', value: result?.failed || 0 },
        ]}
      />
      <Card>
        <PanelHeader title="导入入口" />
        <div className="actions mb-5">
          <Button
            variant={mode === 'manual' ? 'primary' : 'secondary'}
            onClick={() => setMode('manual')}
          >
            手动录入
          </Button>
          <Button
            variant={mode === 'endnote' ? 'primary' : 'secondary'}
            onClick={() => setMode('endnote')}
          >
            EndNote
          </Button>
          <Button
            variant={mode === 'noteexpress' ? 'primary' : 'secondary'}
            onClick={() => setMode('noteexpress')}
          >
            NoteExpress
          </Button>
        </div>
        {mode === 'manual' ? (
          <Button asChild>
            <Link to="/literatures/new">前往添加文献</Link>
          </Button>
        ) : (
          <div className="form-grid">
            <Field className="span-8" label="导入文件">
              <Input
                type="file"
                accept={mode === 'endnote' ? '.txt,.enw' : '.txt,.nel'}
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
            </Field>
            <div className="span-4 flex items-end">
              <Button disabled={working} onClick={() => void run()}>
                开始导入
              </Button>
            </div>
          </div>
        )}
      </Card>
      {result && (
        <Card>
          <PanelHeader
            title="导入结果"
            caption={`成功 ${result.success} 条，失败 ${result.failed} 条`}
          />
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>标题</th>
                  <th>作者</th>
                  <th>状态</th>
                  <th>说明</th>
                </tr>
              </thead>
              <tbody>
                {result.items.map((item, index) => (
                  <tr key={`${item.title}-${index}`}>
                    <td>{item.title}</td>
                    <td>{item.authors}</td>
                    <td>{item.success ? '成功' : '失败'}</td>
                    <td>{item.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  )
}

export function BackupPage() {
  const [exporting, setExporting] = useState(false),
    [restoring, setRestoring] = useState(false),
    [file, setFile] = useState<File | null>(null),
    [mode, setMode] = useState('merge')
  const exportData = async () => {
    setExporting(true)
    try {
      const response = await fetch('/api/backup/export')
      const body = await response.json()
      if (body.code !== 200) throw new Error(body.message)
      downloadText(
        JSON.stringify(body.data, null, 2),
        `literature-backup-${new Date().toISOString().slice(0, 10)}.json`,
        'application/json',
      )
      toast.success('数据导出成功')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '导出失败')
    } finally {
      setExporting(false)
    }
  }
  const restore = async () => {
    if (!file) return toast.warning('请先选择备份文件')
    if (
      !confirm(
        mode === 'overwrite'
          ? '覆盖模式会清空现有数据，确定继续吗？'
          : '合并备份内容，确定继续吗？',
      )
    )
      return
    setRestoring(true)
    try {
      const response = await fetch('/api/backup/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ data: JSON.parse(await file.text()), mode }),
      })
      const body = await response.json()
      if (body.code !== 200) throw new Error(body.message)
      toast.success(`恢复成功：导入 ${body.data.imported} 条文献`)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '恢复失败')
    } finally {
      setRestoring(false)
    }
  }
  return (
    <div className="page-shell">
      <PageHero
        eyebrow="Preservation · Backup"
        title="备份与恢复"
        description="导出正式数据快照，或以合并、覆盖模式恢复。"
        metrics={[
          { label: 'Export', value: exporting ? '进行中' : 'Ready' },
          { label: 'Restore', value: restoring ? '进行中' : 'Idle' },
          { label: 'Mode', value: mode },
        ]}
      />
      <div className="content-grid-2">
        <Card>
          <PanelHeader
            title="数据备份"
            caption="导出所有正式文献数据为 JSON，不包含 PDF 文件本体。"
          />
          <Button disabled={exporting} onClick={() => void exportData()}>
            导出数据
          </Button>
        </Card>
        <Card>
          <PanelHeader title="数据恢复" />
          <div className="form-grid">
            <Field className="span-12" label="备份文件">
              <Input
                type="file"
                accept=".json"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
            </Field>
            <Field className="span-12" label="恢复模式">
              <Select value={mode} onChange={(e) => setMode(e.target.value)}>
                <option value="merge">合并模式</option>
                <option value="overwrite">覆盖模式</option>
              </Select>
            </Field>
          </div>
          <Button className="mt-4" disabled={restoring} onClick={() => void restore()}>
            开始恢复
          </Button>
        </Card>
      </div>
      <Card>
        <PanelHeader title="存储位置" />
        <p className="muted">
          数据库：backend/data/db/app.db
          <br />
          PDF：backend/data/uploads/pdfs/
          <br />
          任务产物：backend/data/artifacts/
        </p>
      </Card>
    </div>
  )
}

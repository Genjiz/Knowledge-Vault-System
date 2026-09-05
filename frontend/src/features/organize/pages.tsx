import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { toast } from 'sonner'
import type { Folder, Tag } from '@/api/types'
import { folderApi, tagApi } from '@/api/resources'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  Field,
  Input,
  LoadingState,
  Modal,
  PageHero,
  PanelHeader,
  Select,
} from '@/components/ui'

export function TagPage() {
  const client = useQueryClient(),
    query = useQuery({ queryKey: ['tags'], queryFn: tagApi.list }),
    [editing, setEditing] = useState<Tag | null>(null),
    [open, setOpen] = useState(false),
    [name, setName] = useState(''),
    [color, setColor] = useState('#0f172a')
  const save = useMutation({
    mutationFn: () =>
      editing ? tagApi.update(editing.id, { name, color }) : tagApi.create({ name, color }),
    onSuccess: async () => {
      toast.success(editing ? '标签已更新' : '标签已创建')
      setOpen(false)
      await client.invalidateQueries({ queryKey: ['tags'] })
    },
  })
  const remove = useMutation({
    mutationFn: tagApi.remove,
    onSuccess: async () => {
      toast.success('标签已删除')
      await client.invalidateQueries({ queryKey: ['tags'] })
    },
  })
  if (query.isLoading) return <LoadingState />
  if (query.error) return <ErrorState error={query.error} />
  const tags = query.data || [],
    used = tags.filter((x) => x.literature_count > 0).length,
    total = tags.reduce((s, x) => s + x.literature_count, 0)
  const show = (tag?: Tag) => {
    setEditing(tag || null)
    setName(tag?.name || '')
    setColor(tag?.color || '#0f172a')
    setOpen(true)
  }
  return (
    <div className="page-shell">
      <PageHero
        eyebrow="Vocabulary Layer · Taxonomy"
        title="标签管理"
        description="用颜色和命名规则维护主题词表。"
        metrics={[
          { label: 'Tag Count', value: tags.length },
          { label: 'In Use', value: used },
          { label: 'Unused', value: tags.length - used },
          { label: 'Coverage', value: total },
        ]}
      />
      <Card>
        <PanelHeader title="标签清单" actions={<Button onClick={() => show()}>添加标签</Button>} />
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>标签</th>
                <th>颜色</th>
                <th>文献数量</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {tags.map((row) => (
                <tr key={row.tag.id}>
                  <td>
                    <Badge className="text-white" style={{ backgroundColor: row.tag.color }}>
                      {row.tag.name}
                    </Badge>
                  </td>
                  <td>{row.tag.color}</td>
                  <td>{row.literature_count}</td>
                  <td>
                    <div className="actions">
                      <Button variant="secondary" onClick={() => show(row.tag)}>
                        编辑
                      </Button>
                      <Button
                        variant="danger"
                        onClick={() => {
                          if (confirm('确定删除这个标签吗？')) remove.mutate(row.tag.id)
                        }}
                      >
                        删除
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
      <Modal
        open={open}
        onOpenChange={setOpen}
        title={editing ? '编辑标签' : '添加标签'}
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              取消
            </Button>
            <Button disabled={!name.trim() || save.isPending} onClick={() => save.mutate()}>
              保存
            </Button>
          </>
        }
      >
        <div className="form-grid">
          <Field className="span-12" label="名称">
            <Input value={name} onChange={(e) => setName(e.target.value)} />
          </Field>
          <Field className="span-12" label="颜色">
            <Input type="color" value={color} onChange={(e) => setColor(e.target.value)} />
          </Field>
        </div>
      </Modal>
    </div>
  )
}

function flatten(folders: Folder[], path = ''): Array<Folder & { fullPath: string }> {
  return folders.flatMap((folder) => {
    const fullPath = path ? `${path} / ${folder.name}` : folder.name
    return [{ ...folder, fullPath }, ...flatten(folder.children || [], fullPath)]
  })
}
function depth(folders: Folder[], level = 1): number {
  return folders.length
    ? Math.max(...folders.map((f) => depth(f.children || [], level + 1)))
    : level - 1
}
function FolderNodes({
  folders,
  onEdit,
  onAdd,
  onDelete,
}: {
  folders: Folder[]
  onEdit: (f: Folder) => void
  onAdd: (f: Folder) => void
  onDelete: (f: Folder) => void
}) {
  return (
    <div className="space-y-2">
      {folders.map((folder) => (
        <div key={folder.id} className="item-card">
          <div className="flex items-center justify-between gap-3">
            <strong>{folder.name}</strong>
            <div className="actions">
              <Button variant="ghost" onClick={() => onAdd(folder)}>
                添加子级
              </Button>
              <Button variant="secondary" onClick={() => onEdit(folder)}>
                编辑
              </Button>
              <Button variant="danger" onClick={() => onDelete(folder)}>
                删除
              </Button>
            </div>
          </div>
          {folder.children?.length ? (
            <div className="mt-3 ml-5 border-l pl-4">
              <FolderNodes
                folders={folder.children}
                onEdit={onEdit}
                onAdd={onAdd}
                onDelete={onDelete}
              />
            </div>
          ) : null}
        </div>
      ))}
    </div>
  )
}
export function FolderPage() {
  const client = useQueryClient(),
    query = useQuery({ queryKey: ['folders'], queryFn: folderApi.list }),
    [open, setOpen] = useState(false),
    [editing, setEditing] = useState<Folder | null>(null),
    [name, setName] = useState(''),
    [parent, setParent] = useState('')
  const list = useMemo(() => flatten(query.data || []), [query.data])
  const save = useMutation({
    mutationFn: () =>
      editing
        ? folderApi.update(editing.id, { name, parent_id: parent ? Number(parent) : null })
        : folderApi.create({ name, parent_id: parent ? Number(parent) : null }),
    onSuccess: async () => {
      toast.success('文件夹已保存')
      setOpen(false)
      await client.invalidateQueries({ queryKey: ['folders'] })
    },
  })
  const remove = useMutation({
    mutationFn: folderApi.remove,
    onSuccess: async () => client.invalidateQueries({ queryKey: ['folders'] }),
  })
  if (query.isLoading) return <LoadingState />
  if (query.error) return <ErrorState error={query.error} />
  const show = (folder?: Folder, parentFolder?: Folder) => {
    setEditing(folder || null)
    setName(folder?.name || '')
    setParent(String(folder?.parent_id || parentFolder?.id || ''))
    setOpen(true)
  }
  return (
    <div className="page-shell">
      <PageHero
        eyebrow="Structure Map · Folders"
        title="文件夹管理"
        description="用层级结构组织长期稳定的研究主题。"
        metrics={[
          { label: 'Root Nodes', value: query.data?.length || 0 },
          { label: 'All Folders', value: list.length },
          { label: 'Deepest Path', value: depth(query.data || []) },
        ]}
      />
      <Card>
        <PanelHeader
          title="文件夹树"
          actions={<Button onClick={() => show()}>添加文件夹</Button>}
        />
        {query.data?.length ? (
          <FolderNodes
            folders={query.data}
            onEdit={(f) => show(f)}
            onAdd={(f) => show(undefined, f)}
            onDelete={(f) => {
              if (confirm('删除文件夹将同时删除子文件夹，确定继续吗？')) remove.mutate(f.id)
            }}
          />
        ) : (
          <EmptyState />
        )}
      </Card>
      <Modal
        open={open}
        onOpenChange={setOpen}
        title={editing ? '编辑文件夹' : '添加文件夹'}
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              取消
            </Button>
            <Button disabled={!name.trim()} onClick={() => save.mutate()}>
              保存
            </Button>
          </>
        }
      >
        <div className="form-grid">
          <Field className="span-12" label="名称">
            <Input value={name} onChange={(e) => setName(e.target.value)} />
          </Field>
          <Field className="span-12" label="父文件夹">
            <Select value={parent} onChange={(e) => setParent(e.target.value)}>
              <option value="">根目录</option>
              {list
                .filter((f) => f.id !== editing?.id)
                .map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.fullPath}
                  </option>
                ))}
            </Select>
          </Field>
        </div>
      </Modal>
    </div>
  )
}

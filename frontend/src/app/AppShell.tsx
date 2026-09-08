import { Link, Outlet, useRouterState } from '@tanstack/react-router'
import {
  Archive,
  BarChart3,
  BrainCircuit,
  BookOpen,
  Download,
  FileText,
  Folder,
  Gauge,
  Tags,
  Settings2,
  Upload,
  Video,
  Workflow,
} from 'lucide-react'

const groups = [
  {
    label: 'Workspace',
    items: [
      ['/', '仪表盘', Gauge],
      ['/literatures', '文献列表', FileText],
      ['/paper-analysis', '论文分析', BrainCircuit],
      ['/tags', '标签管理', Tags],
      ['/folders', '文件夹管理', Folder],
      ['/statistics', '统计分析', BarChart3],
    ],
  },
  {
    label: 'Collection',
    items: [
      ['/crawler/journals', '期刊与采集源', BookOpen],
      ['/crawler/tasks', '采集任务台', Workflow],
      ['/crawler/issues', '采集期号库', Archive],
    ],
  },
  {
    label: 'Media',
    items: [
      ['/video-notes', '视频转笔记', Video],
      ['/video-notes/tasks', '视频任务列表', FileText],
    ],
  },
  {
    label: 'System',
    items: [['/settings/models', '模型配置', Settings2]],
  },
  {
    label: 'Utilities',
    items: [
      ['/import', '导入文献', Upload],
      ['/backup', '备份恢复', Download],
    ],
  },
] as const

export function AppShell() {
  const pathname = useRouterState({ select: (state) => state.location.pathname })
  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="brand">
          <span>Knowledge Workspace</span>
          <strong>Knowledge Vault</strong>
        </div>
        <nav>
          {groups.map((group) => (
            <div className="nav-group" key={group.label}>
              <div className="nav-label">{group.label}</div>
              {group.items.map(([to, label, Icon]) => {
                const active =
                  to === '/' ? pathname === '/' : pathname === to || pathname.startsWith(`${to}/`)
                return (
                  <Link key={to} to={to} className={active ? 'nav-link active' : 'nav-link'}>
                    <Icon size={17} />
                    <span>{label}</span>
                  </Link>
                )
              })}
            </div>
          ))}
        </nav>
      </aside>
      <main className="main-content">
        <div className="page-container">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

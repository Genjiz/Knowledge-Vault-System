import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { useMemo } from 'react'
import { literatureApi } from '@/api/resources'
import { Chart } from '@/components/chart'
import { Button, Card, ErrorState, LoadingState, PageHero, PanelHeader } from '@/components/ui'
import { formatDate } from '@/lib/utils'

const colors = ['#111827', '#0f766e', '#2563eb', '#d97706', '#dc2626']

function useStatistics() {
  return useQuery({ queryKey: ['statistics'], queryFn: literatureApi.statistics })
}
function pieOption(data: Array<{ name: string; value: number }>, palette = colors) {
  return {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    color: palette,
    series: [
      {
        type: 'pie',
        radius: ['45%', '72%'],
        center: ['50%', '44%'],
        itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 3 },
        data,
      },
    ],
  }
}

export function DashboardPage() {
  const statsQuery = useStatistics()
  const recentQuery = useQuery({
    queryKey: ['literatures', 'recent'],
    queryFn: () => literatureApi.list({ page: 1, per_page: 5 }),
  })
  if (statsQuery.isLoading || recentQuery.isLoading) return <LoadingState />
  if (statsQuery.error || recentQuery.error)
    return <ErrorState error={statsQuery.error || recentQuery.error} />
  const stats = statsQuery.data!
  const status = stats.by_status || {}
  const completed = status['已读完'] || 0,
    reading = status['正在阅读'] || 0,
    unread = status['未读'] || 0,
    skim = status['摘要浏览'] || 0
  const zh = stats.by_language?.zh || 0,
    en = stats.by_language?.en || 0
  const latest = stats.monthly?.at(-1)
  return (
    <div className="page-shell">
      <PageHero
        eyebrow="Research Desk · Overview"
        title="文献工作台"
        description="在一个视图里看清文献总量、阅读节奏、语言结构和近期新增。"
        metrics={[
          { label: 'Library Size', value: stats.total || 0 },
          { label: 'Completed', value: completed },
          { label: 'In Progress', value: reading },
          { label: 'Unread', value: unread },
        ]}
      />
      <div className="stats-grid">
        {[
          ['文献总数', stats.total || 0, '当前数据库内全部正式文献记录。'],
          ['已读完成', completed, '已经完成深读或整理的文献。'],
          ['正在阅读', reading, '当前仍在推进中的阅读任务。'],
          ['摘要浏览/未读', skim + unread, '适合继续筛选和安排优先级。'],
        ].map(([label, value, caption]) => (
          <article className="stat-panel" key={label}>
            <div className="stat-label">{label}</div>
            <div className="stat-value">{value}</div>
            <p className="stat-caption">{caption}</p>
          </article>
        ))}
      </div>
      <Card>
        <PanelHeader
          title="阅读节奏提示"
          caption={`语言分布：中文 ${zh} / 英文 ${en}；${latest ? `${latest.month} 新增 ${latest.count} 篇` : '暂无月度趋势数据'}`}
          actions={
            <Button asChild>
              <Link to="/literatures/new">添加文献</Link>
            </Button>
          }
        />
      </Card>
      <div className="content-grid-2">
        <Card>
          <PanelHeader title="阅读状态分布" />
          <Chart
            option={pieOption(Object.entries(status).map(([name, value]) => ({ name, value })))}
          />
        </Card>
        <Card>
          <PanelHeader title="语言结构" />
          <Chart
            option={pieOption(
              [
                { name: '中文', value: zh },
                { name: '英文', value: en },
              ].filter((item) => item.value > 0),
              ['#14b8a6', '#334155'],
            )}
          />
        </Card>
      </div>
      <Card>
        <PanelHeader
          title="最近新增文献"
          actions={
            <Button variant="ghost" asChild>
              <Link to="/literatures">查看全部</Link>
            </Button>
          }
        />
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>标题</th>
                <th>作者</th>
                <th>年份</th>
                <th>状态</th>
                <th>添加时间</th>
              </tr>
            </thead>
            <tbody>
              {recentQuery.data!.items.map((item) => (
                <tr key={item.id}>
                  <td>
                    <Link to="/literatures/$id" params={{ id: String(item.id) }}>
                      <strong>{item.title}</strong>
                    </Link>
                  </td>
                  <td>{item.authors || '未填写'}</td>
                  <td>{item.year || '-'}</td>
                  <td>{item.status || '未读'}</td>
                  <td>{formatDate(item.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}

export function StatisticsPage() {
  const query = useStatistics()
  const stats = query.data
  const chartData = useMemo(
    () => Object.entries(stats?.by_status || {}).map(([name, value]) => ({ name, value })),
    [stats],
  )
  if (query.isLoading) return <LoadingState />
  if (query.error || !stats) return <ErrorState error={query.error} />
  const zh = stats.by_language?.zh || 0,
    en = stats.by_language?.en || 0,
    monthly = stats.monthly || []
  return (
    <div className="page-shell">
      <PageHero
        eyebrow="Insight Atlas · Analytics"
        title="统计分析"
        description="从阅读状态、语言结构和月度趋势观察文献库的积累节奏。"
        metrics={[
          { label: 'Total', value: stats.total || 0 },
          { label: 'Chinese', value: zh },
          { label: 'English', value: en },
          { label: 'Latest Month', value: monthly.at(-1)?.count || 0 },
        ]}
      />
      <div className="content-grid-2">
        <Card>
          <PanelHeader title="阅读状态分布" />
          <Chart option={pieOption(chartData)} />
        </Card>
        <Card>
          <PanelHeader title="语言结构" />
          <Chart
            option={pieOption(
              [
                { name: '中文', value: zh },
                { name: '英文', value: en },
              ],
              ['#14b8a6', '#334155'],
            )}
          />
        </Card>
      </div>
      <Card>
        <PanelHeader title="月度新增趋势" />
        <Chart
          className="chart-surface chart-surface--lg"
          option={{
            tooltip: { trigger: 'axis' },
            grid: { left: 42, right: 20, top: 28, bottom: 36 },
            xAxis: { type: 'category', data: monthly.map((x) => x.month), boundaryGap: false },
            yAxis: { type: 'value' },
            series: [
              {
                type: 'line',
                smooth: true,
                data: monthly.map((x) => x.count),
                lineStyle: { width: 3, color: '#111827' },
                itemStyle: { color: '#111827' },
                areaStyle: { color: 'rgba(15,23,42,.08)' },
              },
            ],
          }}
        />
      </Card>
    </div>
  )
}

type FullTextTaskLike = { status?: string } | undefined

export function isFullTextRunning(task: FullTextTaskLike) {
  return task?.status === 'pending' || task?.status === 'running'
}

export function isFullTextActive(task: FullTextTaskLike) {
  return isFullTextRunning(task) || task?.status === 'waiting_user'
}

export function fullTextStatusLabel(status?: string) {
  if (status === 'completed') return '已完成'
  if (status === 'partial') return '部分完成'
  if (status === 'failed') return '失败'
  if (status === 'running') return '下载中'
  if (status === 'waiting_user') return '等待用户处理'
  return '等待开始'
}

export function fullTextActionLabel(failureCode?: string | null) {
  if (failureCode === 'verification_required') return '验证完成后继续'
  return '继续下载'
}

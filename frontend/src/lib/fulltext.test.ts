import { describe, expect, it } from 'vitest'
import {
  fullTextActionLabel,
  fullTextStatusLabel,
  isFullTextActive,
  isFullTextRunning,
} from './fulltext'

describe('fulltext task presentation', () => {
  it('distinguishes background work from user-action waits', () => {
    expect(isFullTextRunning({ status: 'running' })).toBe(true)
    expect(isFullTextRunning({ status: 'waiting_user' })).toBe(false)
    expect(isFullTextActive({ status: 'waiting_user' })).toBe(true)
  })

  it('shows recovery actions without assuming the user changed networks', () => {
    expect(fullTextStatusLabel('waiting_user')).toBe('等待用户处理')
    expect(fullTextActionLabel('verification_required')).toBe('验证完成后继续')
    expect(fullTextActionLabel('access_blocked')).toBe('继续下载')
    expect(fullTextActionLabel('browser_unavailable')).toBe('继续下载')
  })
})

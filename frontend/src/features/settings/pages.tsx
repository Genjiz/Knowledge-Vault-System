import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { KeyRound, Pencil, PlugZap, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import type { LLMProfile } from '@/api/types'
import { llmApi } from '@/api/resources'
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
import { formatDate } from '@/lib/utils'

interface ProfileDraft {
  id?: number
  name: string
  protocol: 'gemini' | 'openai'
  base_url: string
  model_name: string
  api_key: string
  enabled: boolean
  has_api_key?: boolean
}

const emptyDraft: ProfileDraft = {
  name: '',
  protocol: 'gemini',
  base_url: '',
  model_name: '',
  api_key: '',
  enabled: true,
}

function profileDraft(profile?: LLMProfile): ProfileDraft {
  return profile
    ? {
        id: profile.id,
        name: profile.name,
        protocol: profile.protocol,
        base_url: profile.base_url || '',
        model_name: profile.model_name,
        api_key: '',
        enabled: profile.enabled,
        has_api_key: profile.has_api_key,
      }
    : { ...emptyDraft }
}

export function ModelSettingsPage() {
  const client = useQueryClient()
  const profiles = useQuery({ queryKey: ['llm-profiles'], queryFn: llmApi.profiles })
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState<ProfileDraft>(emptyDraft)
  const refresh = () => client.invalidateQueries({ queryKey: ['llm-profiles'] })
  const save = useMutation({
    mutationFn: () => {
      const payload = {
        name: draft.name,
        protocol: draft.protocol,
        base_url: draft.base_url,
        model_name: draft.model_name,
        api_key: draft.api_key,
        enabled: draft.enabled,
      }
      return draft.id ? llmApi.updateProfile(draft.id, payload) : llmApi.createProfile(payload)
    },
    onSuccess: async () => {
      setOpen(false)
      toast.success('模型档案已保存')
      await refresh()
    },
    onError: (error) => toast.error(error.message),
  })
  const testProfile = useMutation({
    mutationFn: llmApi.testProfile,
    onSuccess: async (profile) => {
      toast[profile.last_check_status === 'ok' ? 'success' : 'error'](
        profile.last_check_message || '测试完成',
      )
      await refresh()
    },
    onError: (error) => toast.error(error.message),
  })
  const remove = useMutation({
    mutationFn: llmApi.removeProfile,
    onSuccess: async () => {
      toast.success('模型档案已删除')
      await refresh()
    },
    onError: (error) => toast.error(error.message),
  })
  if (profiles.isLoading) return <LoadingState />
  if (profiles.error) return <ErrorState error={profiles.error} />
  const list = profiles.data || []
  return (
    <div className="page-shell">
      <PageHero
        eyebrow="System · Models"
        title="模型配置"
        description="管理大模型连接、模型名称和访问密钥。"
        metrics={[
          { label: 'Profiles', value: list.length },
          { label: 'Enabled', value: list.filter((item) => item.enabled).length },
          { label: 'Configured Keys', value: list.filter((item) => item.has_api_key).length },
        ]}
      />
      <Card>
        <PanelHeader
          title="模型档案"
          actions={
            <Button
              onClick={() => {
                setDraft(profileDraft())
                setOpen(true)
              }}
            >
              <Plus size={16} />
              新增模型
            </Button>
          }
        />
        {list.length ? (
          <div className="table-wrap">
            <table className="data-table model-profiles-table">
              <thead>
                <tr>
                  <th>档案</th>
                  <th>协议与地址</th>
                  <th>密钥</th>
                  <th>连接状态</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {list.map((profile) => (
                  <tr key={profile.id}>
                    <td data-label="档案">
                      <strong>{profile.name}</strong>
                      <div className="muted">{profile.model_name}</div>
                    </td>
                    <td data-label="协议与地址">
                      <Badge tone={profile.protocol === 'gemini' ? 'info' : 'neutral'}>
                        {profile.protocol === 'gemini' ? 'Gemini Native' : 'OpenAI Compatible'}
                      </Badge>
                      <div className="muted break-all">{profile.base_url || 'Google 默认地址'}</div>
                    </td>
                    <td data-label="密钥">
                      <Badge tone={profile.has_api_key ? 'success' : 'warning'}>
                        <KeyRound size={12} />
                        {profile.has_api_key ? '已配置' : '未配置'}
                      </Badge>
                    </td>
                    <td data-label="连接状态">
                      <Badge
                        tone={
                          profile.last_check_status === 'ok'
                            ? 'success'
                            : profile.last_check_status
                              ? 'danger'
                              : 'neutral'
                        }
                      >
                        {profile.last_check_status === 'ok'
                          ? '可用'
                          : profile.last_check_status
                            ? '失败'
                            : '未测试'}
                      </Badge>
                      {profile.last_checked_at && (
                        <div className="muted">{formatDate(profile.last_checked_at)}</div>
                      )}
                    </td>
                    <td data-label="操作">
                      <div className="actions">
                        <Button
                          variant="secondary"
                          disabled={testProfile.isPending || !profile.enabled}
                          onClick={() => testProfile.mutate(profile.id)}
                        >
                          <PlugZap size={15} />
                          测试
                        </Button>
                        <button
                          className="icon-button"
                          aria-label={`编辑 ${profile.name}`}
                          title="编辑"
                          onClick={() => {
                            setDraft(profileDraft(profile))
                            setOpen(true)
                          }}
                        >
                          <Pencil size={16} />
                        </button>
                        <button
                          className="icon-button"
                          aria-label={`删除 ${profile.name}`}
                          title="删除"
                          onClick={() => {
                            if (confirm(`确定删除模型档案“${profile.name}”吗？`))
                              remove.mutate(profile.id)
                          }}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState>尚未配置模型</EmptyState>
        )}
      </Card>
      <Modal
        open={open}
        onOpenChange={setOpen}
        title={draft.id ? '编辑模型档案' : '新增模型档案'}
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              取消
            </Button>
            <Button disabled={save.isPending} onClick={() => save.mutate()}>
              {save.isPending ? '保存中...' : '保存'}
            </Button>
          </>
        }
      >
        <div className="form-grid">
          <Field className="span-6" label="显示名称">
            <Input
              value={draft.name}
              onChange={(e) => setDraft({ ...draft, name: e.target.value })}
            />
          </Field>
          <Field className="span-6" label="协议">
            <Select
              value={draft.protocol}
              onChange={(e) =>
                setDraft({ ...draft, protocol: e.target.value === 'openai' ? 'openai' : 'gemini' })
              }
            >
              <option value="gemini">Gemini Native</option>
              <option value="openai">OpenAI Compatible</option>
            </Select>
          </Field>
          <Field className="span-12" label="Base URL">
            <Input
              placeholder={
                draft.protocol === 'gemini'
                  ? '留空使用 Google 默认地址'
                  : 'https://api.example.com/v1'
              }
              value={draft.base_url}
              onChange={(e) => setDraft({ ...draft, base_url: e.target.value })}
            />
          </Field>
          <Field className="span-12" label="模型名称">
            <Input
              value={draft.model_name}
              onChange={(e) => setDraft({ ...draft, model_name: e.target.value })}
            />
          </Field>
          <Field
            className="span-12"
            label="API Key"
            hint={draft.has_api_key ? '已配置；留空保持原密钥' : undefined}
          >
            <Input
              type="password"
              autoComplete="new-password"
              value={draft.api_key}
              onChange={(e) => setDraft({ ...draft, api_key: e.target.value })}
            />
          </Field>
          <label className="switch-label span-12">
            <input
              type="checkbox"
              checked={draft.enabled}
              onChange={(e) => setDraft({ ...draft, enabled: e.target.checked })}
            />
            启用此模型
          </label>
        </div>
      </Modal>
    </div>
  )
}

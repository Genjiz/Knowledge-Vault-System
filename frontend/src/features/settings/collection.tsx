import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { KeyRound, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import { collectionApi } from '@/api/resources'
import {
  Badge,
  Button,
  Card,
  ErrorState,
  Field,
  Input,
  LoadingState,
  PageHero,
  PanelHeader,
} from '@/components/ui'

export function CollectionSettingsPage() {
  const client = useQueryClient()
  const keyStatus = useQuery({
    queryKey: ['collection-elsevier-key'],
    queryFn: collectionApi.elsevierKey,
  })
  const [apiKey, setApiKey] = useState('')
  const refresh = () => client.invalidateQueries({ queryKey: ['collection-elsevier-key'] })
  const save = useMutation({
    mutationFn: () => collectionApi.setElsevierKey(apiKey),
    onSuccess: async () => {
      setApiKey('')
      toast.success('采集密钥已保存')
      await refresh()
    },
    onError: (error) => toast.error(error.message),
  })
  const clear = useMutation({
    mutationFn: collectionApi.clearElsevierKey,
    onSuccess: async () => {
      setApiKey('')
      toast.success('采集密钥已清除')
      await refresh()
    },
    onError: (error) => toast.error(error.message),
  })

  if (keyStatus.isLoading) return <LoadingState />
  if (keyStatus.error) return <ErrorState error={keyStatus.error} />

  return (
    <div className="page-shell">
      <PageHero
        eyebrow="Collection · Settings"
        title="采集设置"
        description="管理期刊采集服务使用的访问凭据。"
        metrics={[
          {
            label: 'Research Products API',
            value: keyStatus.data?.has_api_key ? 'Configured' : 'Not Configured',
          },
        ]}
      />
      <Card>
        <PanelHeader
          title="Elsevier Research Products API"
          actions={
            <Badge tone={keyStatus.data?.has_api_key ? 'success' : 'warning'}>
              <KeyRound size={12} />
              {keyStatus.data?.has_api_key ? '已配置' : '未配置'}
            </Badge>
          }
        />
        <div className="form-grid">
          <Field
            className="span-12"
            label="API Key"
            hint="Elsevier 与 Scopus API 共用该 Research Products API Key；密钥不会回显。"
          >
            <Input
              type="password"
              autoComplete="new-password"
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
            />
          </Field>
          <div className="actions span-12">
            <Button disabled={!apiKey.trim() || save.isPending} onClick={() => save.mutate()}>
              <KeyRound size={16} />
              {save.isPending ? '保存中...' : '保存密钥'}
            </Button>
            {keyStatus.data?.has_api_key && (
              <Button variant="secondary" disabled={clear.isPending} onClick={() => clear.mutate()}>
                <Trash2 size={16} />
                清除密钥
              </Button>
            )}
          </div>
        </div>
      </Card>
    </div>
  )
}

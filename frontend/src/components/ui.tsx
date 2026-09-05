import * as Dialog from '@radix-ui/react-dialog'
import { Slot } from '@radix-ui/react-slot'
import { X } from 'lucide-react'
import type {
  ButtonHTMLAttributes,
  HTMLAttributes,
  InputHTMLAttributes,
  PropsWithChildren,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from 'react'
import { cn } from '@/lib/utils'

export function Button({
  className,
  variant = 'primary',
  asChild,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
  asChild?: boolean
}) {
  const Component = asChild ? Slot : 'button'
  return <Component className={cn('button', `button--${variant}`, className)} {...props} />
}

export function Card({ className, ...props }: HTMLAttributes<HTMLElement>) {
  return <section className={cn('surface-panel', className)} {...props} />
}

export function Badge({
  children,
  tone = 'neutral',
  className,
  ...props
}: PropsWithChildren<
  HTMLAttributes<HTMLSpanElement> & { tone?: 'neutral' | 'success' | 'warning' | 'danger' | 'info' }
>) {
  return (
    <span className={cn('badge', `badge--${tone}`, className)} {...props}>
      {children}
    </span>
  )
}

export function Field({
  label,
  hint,
  children,
  className,
}: {
  label: string
  hint?: string
  children: ReactNode
  className?: string
}) {
  return (
    <label className={cn('field', className)}>
      <span className="field__label">{label}</span>
      {children}
      {hint && <span className="field__hint">{hint}</span>}
    </label>
  )
}

export const Input = ({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) => (
  <input className={cn('input', className)} {...props} />
)
export const Textarea = ({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) => (
  <textarea className={cn('input textarea', className)} {...props} />
)
export const Select = ({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) => (
  <select className={cn('input select', className)} {...props} />
)

export function Modal({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
  wide = false,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description?: string
  children: ReactNode
  footer?: ReactNode
  wide?: boolean
}) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content className={cn('dialog-content', wide && 'dialog-content--wide')}>
          <div className="dialog-header">
            <div>
              <Dialog.Title className="dialog-title">{title}</Dialog.Title>
              {description && (
                <Dialog.Description className="dialog-description">
                  {description}
                </Dialog.Description>
              )}
            </div>
            <Dialog.Close className="icon-button" aria-label="关闭">
              <X size={18} />
            </Dialog.Close>
          </div>
          <div className="dialog-body">{children}</div>
          {footer && <div className="dialog-footer">{footer}</div>}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

export function PageHero({
  eyebrow,
  title,
  description,
  metrics,
}: {
  eyebrow: string
  title: string
  description: string
  metrics?: Array<{ label: string; value: ReactNode }>
}) {
  return (
    <header className="page-hero">
      <div className="page-hero__body">
        <div>
          <div className="page-eyebrow">{eyebrow}</div>
          <h1 className="page-title">{title}</h1>
          <p className="page-subtitle">{description}</p>
        </div>
        {metrics && (
          <div className="hero-meta-grid">
            {metrics.map((item) => (
              <div className="hero-meta-tile" key={item.label}>
                <span className="hero-meta-label">{item.label}</span>
                <strong className="hero-meta-value">{item.value}</strong>
              </div>
            ))}
          </div>
        )}
      </div>
    </header>
  )
}

export function PanelHeader({
  title,
  caption,
  actions,
}: {
  title: string
  caption?: string
  actions?: ReactNode
}) {
  return (
    <div className="surface-panel__header">
      <div>
        <h2 className="surface-panel__title">{title}</h2>
        {caption && <p className="surface-panel__caption">{caption}</p>}
      </div>
      {actions}
    </div>
  )
}

export function EmptyState({ children = '暂无数据' }: PropsWithChildren) {
  return <div className="empty-state">{children}</div>
}
export function LoadingState() {
  return <div className="empty-state">正在加载...</div>
}
export function ErrorState({ error }: { error: unknown }) {
  return (
    <div className="alert alert--danger">
      {error instanceof Error ? error.message : '加载失败，请稍后重试'}
    </div>
  )
}

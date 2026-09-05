export interface Tag {
  id: number
  name: string
  color: string
}
export interface TagRecord {
  tag: Tag
  literature_count: number
}
export interface Folder {
  id: number
  name: string
  parent_id?: number | null
  children?: Folder[]
}
export interface Literature {
  id: number
  title: string
  authors?: string
  journal?: string
  year?: number | null
  volume?: string
  issue?: string
  pages?: string
  doi?: string
  url?: string
  abstract?: string
  keywords?: string
  language?: string
  status?: string
  literature_type?: string
  publisher?: string
  pdf_path?: string | null
  created_at?: string
  tags?: Tag[]
  folder_ids?: number[]
  source?: string
  journal_id?: number | null
  status_changed_at?: string | null
}
export interface LiteraturePage {
  items: Literature[]
  total: number
  page?: number
  per_page?: number
}
export interface MonthlyStat {
  month: string
  count: number
}
export interface Statistics {
  total: number
  by_status?: Record<string, number>
  by_language?: Record<string, number>
  monthly?: MonthlyStat[]
}
export interface Note {
  id: number
  literature_id: number
  type: string
  title?: string
  content: string
  page_number?: number | null
  position_info?: string
  excerpt_type?: string
  rating?: number
  action_required?: string
  created_at?: string
}
export interface SourceConfigField {
  key: string
  label: string
  required?: boolean
  placeholder?: string
  help?: string
}
export interface SourceMeta {
  source_id: string
  display_name: string
  region: string
  capabilities: Record<string, boolean>
  config_fields: SourceConfigField[]
}
export interface JournalSource {
  source_id: string
  enabled: boolean
  is_default?: boolean
  config_json?: string
  last_check_status?: string
  last_check_message?: string
  last_checked_at?: string
}
export interface Journal {
  id: number
  name: string
  issn?: string
  publisher?: string
  region: string
  sources: JournalSource[]
  stats?: { issue_count?: number; last_collected_at?: string }
}
export interface CrawlTask {
  id: number
  journal_name: string
  source_type: string
  year: number
  issue: string
  status: string
  error_message?: string
  created_at?: string
  started_at?: string
}
export interface RawPaper {
  id: number
  title?: string
  title_zh?: string
  authors?: string
  abstract?: string
  abstract_zh?: string
  detail_url?: string
  translation_status?: string
  keywords?: string
  doi?: string
  pages?: string
}
export interface RawIssue {
  id: number
  journal_name: string
  source_type: string
  region: string
  year: number
  issue: string
  volume?: string
  source_url?: string
  paper_count?: number
  translation_status?: string
  analysis_status?: string
  papers?: RawPaper[]
}
export interface IssueAnalysis {
  id?: number
  status?: string
  content_markdown?: string
}
export interface RawIssuePage {
  items: RawIssue[]
  total: number
  page?: number
  per_page?: number
}
export interface SourceTestResult {
  last_check_status?: string
  last_check_message?: string
  last_checked_at?: string
}
export interface ProbeIssue {
  issue: string
  volume?: string
  published_at?: string
}
export interface ProbeIssuesResult {
  journal_name: string
  source_id: string
  year: number
  issues: ProbeIssue[]
}
export interface CrawlTaskResult {
  task: CrawlTask
  raw_issue: RawIssue
}
export interface ImportKnownResult {
  created?: unknown[]
  updated?: unknown[]
}
export interface VideoTask {
  id: number
  source_url: string
  bvid?: string
  video_title?: string
  status: string
  current_step?: string
  progress_message?: string
  error_message?: string
  updated_at?: string
  audio_path?: string
  transcript_path?: string
  note_path?: string
  metadata_path?: string
  transcript_content?: string
  note_content?: string
}
export interface VideoLog {
  id: number
  level?: string
  message: string
  created_at?: string
}

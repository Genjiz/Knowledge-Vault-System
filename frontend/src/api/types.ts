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
  pdf_source_type?: string | null
  pdf_source_raw_paper_id?: number | null
  pdf_sha256?: string | null
  pdf_size_bytes?: number | null
  created_at?: string
  tags?: Tag[]
  folder_ids?: number[]
  source?: string
  field_sources?: Record<string, string>
  collection_sources?: Array<{
    id: number
    raw_paper_id: number
    source_type: string
  }>
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
  ingest_scope: 'issue' | 'year'
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
  literature_id?: number
  pdf_path?: string
  translation_status?: string
  keywords?: string
  doi?: string
  pages?: string
  volume?: string
  issue?: string
}
export interface ElsevierKeyStatus {
  has_api_key: boolean
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
  expected_paper_count?: number
  paper_count?: number
  title_collected_count?: number
  abstract_collected_count?: number
  fulltext_collected_count?: number
  translation_status?: string
  translation_profile_id?: number | null
  translation_profile_name?: string | null
  translation_model_name?: string | null
  analysis_status?: string
  papers?: RawPaper[]
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
  raw_issue?: RawIssue | null
  raw_issues: RawIssue[]
  fulltext_task?: FullTextTask
  fulltext_error?: string
}
export interface FullTextTaskItem {
  id: number
  literature_id?: number | null
  literature_title?: string | null
  raw_paper_id?: number | null
  source_type: string
  source_url?: string | null
  status: string
  error_message?: string | null
  pdf_path?: string | null
  file_size_bytes?: number | null
}
export interface FullTextTask {
  id: number
  mode: 'single' | 'issue' | 'after_ingestion'
  source_type: string
  raw_issue_id?: number | null
  status: string
  replace_existing?: boolean
  total_count: number
  succeeded_count: number
  failed_count: number
  skipped_count: number
  progress_message?: string | null
  error_message?: string | null
  items: FullTextTaskItem[]
  created_at?: string
  started_at?: string | null
  finished_at?: string | null
}
export interface LLMProfile {
  id: number
  name: string
  protocol: 'gemini' | 'openai'
  base_url?: string | null
  model_name: string
  enabled: boolean
  has_api_key: boolean
  last_check_status?: string | null
  last_check_message?: string | null
  last_checked_at?: string | null
}
export interface AnalysisIssueOption {
  journal_id?: number | null
  journal: string
  year: number
  volume: string
  issue: string
  paper_count: number
}
export interface PaperAnalysisItem {
  id: number
  literature_id?: number | null
  title: string
  authors?: string
  journal?: string
  year?: number | null
  volume?: string
  issue?: string
  text_asset_id?: number | null
  abstract?: string
  keywords?: string
}
export interface PaperAnalysis {
  id: number
  title: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  profile_id?: number | null
  profile_name?: string | null
  model_name?: string | null
  paper_count: number
  prompt_template_version?: string
  prompt_template_snapshot?: string | null
  custom_instruction?: string | null
  include_fulltext?: boolean
  fulltext_count?: number
  fulltext_failed_count?: number
  fulltext_error_message?: string | null
  content_markdown?: string | null
  error_message?: string | null
  created_at?: string
  finished_at?: string | null
  items?: PaperAnalysisItem[]
}
export interface PaperAnalysisPromptTemplate {
  version: string
  content: string
}
export interface PaperAnalysisPage {
  items: PaperAnalysis[]
  total: number
}
export interface VideoTask {
  id: number
  source_url: string
  bvid?: string
  video_title?: string
  status: string
  profile_id?: number | null
  profile_name?: string | null
  model_name?: string | null
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

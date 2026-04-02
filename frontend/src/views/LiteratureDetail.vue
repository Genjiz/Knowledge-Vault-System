<template>
  <div class="max-w-5xl mx-auto pb-16">
    <!-- 顶部导航与操作区 -->
    <div class="mb-8 flex items-center justify-between">
      <el-button @click="$router.back()" class="rounded-lg shadow-sm border-gray-200 hover:bg-gray-50 text-gray-700">
        <el-icon class="mr-1"><ArrowLeft /></el-icon>
        返回文献库
      </el-button>
      <div class="flex items-center gap-3">
        <el-button type="primary" plain class="rounded-lg" @click="$router.push(`/literatures/${literature.id}/edit`)">
          <el-icon class="mr-1"><Edit /></el-icon> 编辑
        </el-button>
        <el-button type="danger" plain class="rounded-lg" @click="handleDelete">
          <el-icon class="mr-1"><Delete /></el-icon> 删除
        </el-button>
      </div>
    </div>

    <!-- 文献基础详情卡片 -->
    <div v-loading="loading" class="bg-surface rounded-2xl shadow-soft p-8 mb-8">
      <div class="text-center mb-8 pb-8 border-b border-gray-100">
        <h2 class="text-2xl font-bold text-gray-900 leading-snug mb-4 tracking-tight">{{ literature.title }}</h2>
        <div class="flex flex-wrap items-center justify-center gap-4 text-gray-600 mb-6 text-sm">
          <div class="flex items-center">
            <el-icon class="mr-1.5"><User /></el-icon>
            <span class="font-medium">{{ literature.authors }}</span>
          </div>
          <div v-if="literature.journal" class="flex items-center px-3 py-1 bg-gray-50 rounded-md">
            <el-icon class="mr-1.5"><Tickets /></el-icon>
            <span class="italic">{{ literature.journal }}</span>
          </div>
          <div v-if="literature.year" class="flex items-center px-3 py-1 bg-gray-50 rounded-md font-medium">
            <el-icon class="mr-1.5"><Calendar /></el-icon>
            {{ literature.year }}
          </div>
        </div>
        
        <div class="flex flex-wrap items-center justify-center gap-2 mb-6" v-if="literature.tags && literature.tags.length">
          <span v-for="tag in literature.tags" :key="tag.id" 
                class="px-3 py-1 rounded-full text-sm font-medium text-white shadow-sm"
                :style="{ backgroundColor: tag.color }">
            {{ tag.name }}
          </span>
        </div>
        
        <div class="flex items-center justify-center gap-3 bg-gray-50/50 py-3 rounded-xl max-w-sm mx-auto">
          <span class="text-sm font-medium text-gray-500">当前阅读进度：</span>
          <el-tag :type="getStatusType(literature.status)" effect="light" class="border-0 font-medium px-4">
            {{ literature.status }}
          </el-tag>
          <el-select v-model="literature.status" @change="updateStatus" class="w-32" size="small">
            <el-option label="未读" value="未读" />
            <el-option label="摘要浏览" value="摘要浏览" />
            <el-option label="正在阅读" value="正在阅读" />
            <el-option label="已读完" value="已读完" />
            <el-option label="需要重读" value="需要重读" />
          </el-select>
        </div>
      </div>

      <!-- 摘要和详情 -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div class="lg:col-span-2">
          <div class="mb-8">
            <h3 class="text-lg font-bold text-gray-900 flex items-center mb-3">
              <span class="w-1 h-5 bg-primary rounded-full mr-2"></span>
              摘要 (Abstract)
            </h3>
            <p class="text-gray-600 leading-relaxed text-left text-sm whitespace-pre-line bg-gray-50/50 p-5 rounded-xl border border-gray-100">
              {{ literature.abstract || '暂无摘要' }}
            </p>
          </div>
          <div v-if="literature.keywords">
            <h3 class="text-lg font-bold text-gray-900 flex items-center mb-3">
              <span class="w-1 h-5 bg-primary rounded-full mr-2"></span>
              关键词
            </h3>
            <p class="text-gray-600 text-sm bg-gray-50/50 p-4 rounded-xl border border-gray-100">
              {{ literature.keywords }}
            </p>
          </div>
        </div>
        
        <div class="lg:col-span-1">
          <!-- 元数据表格 -->
          <div class="bg-gray-50 rounded-xl p-5 border border-gray-100 mb-6">
            <h3 class="text-sm font-bold text-gray-900 mb-4 border-b border-gray-200 pb-2">详细元数据</h3>
            <div class="space-y-3 text-sm">
              <div class="flex justify-between" v-if="literature.doi">
                <span class="text-gray-500">DOI</span>
                <span class="text-gray-900 font-medium">{{ literature.doi }}</span>
              </div>
              <div class="flex justify-between" v-if="literature.literature_type">
                <span class="text-gray-500">文献类型</span>
                <span class="text-gray-900 capitalize">{{ literature.literature_type }}</span>
              </div>
              <div class="flex justify-between" v-if="literature.language">
                <span class="text-gray-500">语言</span>
                <span class="text-gray-900 font-medium">{{ literature.language === 'zh' ? '中文' : '英文' }}</span>
              </div>
              <div class="flex justify-between" v-if="literature.volume || literature.issue">
                <span class="text-gray-500">卷 / 期</span>
                <span class="text-gray-900 font-medium">{{ literature.volume || '-' }} / {{ literature.issue || '-' }}</span>
              </div>
              <div class="flex justify-between" v-if="literature.pages">
                <span class="text-gray-500">页码</span>
                <span class="text-gray-900 font-medium">{{ literature.pages }}</span>
              </div>
              <div class="flex justify-between items-center" v-if="literature.url">
                <span class="text-gray-500">外部链接</span>
                <a :href="literature.url" target="_blank" class="text-primary hover:underline flex items-center gap-1">
                  访问来源 <el-icon><Link /></el-icon>
                </a>
              </div>
            </div>
          </div>

          <!-- PDF 下载模块 -->
          <div class="bg-primary-light-9 rounded-xl p-5 border border-primary-light-8">
            <h3 class="text-sm font-bold text-primary-dark-2 mb-4 flex items-center">
              <el-icon class="mr-1.5"><Document /></el-icon>
              原件附件
            </h3>
            <div v-if="literature.pdf_path" class="flex flex-col gap-3">
              <el-button type="primary" class="w-full shadow-md rounded-lg" @click="openPdf">
                马上阅读原件 PDF
              </el-button>
              <el-button type="danger" plain class="w-full border-red-200 bg-white" @click="handleDeletePdf">
                移除该附件
              </el-button>
            </div>
            <div v-else class="text-center">
              <el-upload :show-file-list="false" accept=".pdf" :before-upload="handleUploadPdf">
                <el-button type="primary" plain class="w-full bg-white border-primary-light-5 hover:bg-primary-light-9">
                  <el-icon class="mr-1"><Upload /></el-icon> 上传 PDF 附件
                </el-button>
              </el-upload>
              <p class="text-xs text-gray-500 mt-2">支持检索本地文件上传</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 笔记卡片区域 -->
    <div class="bg-surface rounded-2xl shadow-soft p-8">
      <div class="flex items-center justify-between mb-6 pb-4 border-b border-gray-100">
        <h3 class="text-xl font-bold text-gray-900 flex items-center">
          <el-icon class="mr-2 text-primary"><Collection /></el-icon> 阅读笔记
        </h3>
        <el-dropdown @command="showNoteDialog" trigger="click">
          <el-button type="primary" class="shadow-sm rounded-lg hover:-translate-y-0.5 transition-transform">
            <el-icon class="mr-1"><Plus /></el-icon> 记录灵感
          </el-button>
          <template #dropdown>
            <el-dropdown-menu class="rounded-xl w-40">
              <el-dropdown-item command="idea" class="py-2"><el-icon class="text-primary"><Opportunity /></el-icon> 想法笔记</el-dropdown-item>
              <el-dropdown-item command="excerpt" class="py-2"><el-icon class="text-green-500"><DocumentCopy /></el-icon> 重点摘录</el-dropdown-item>
              <el-dropdown-item command="structure" class="py-2"><el-icon class="text-orange-400"><List /></el-icon> 结构梳理</el-dropdown-item>
              <el-dropdown-item command="critique" class="py-2" divided><el-icon class="text-red-500"><ChatDotRound /></el-icon> 批判评价</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>

      <!-- 优雅的定制 Tabs -->
      <el-tabs v-model="activeNoteType" class="mb-6 modern-tabs">
        <el-tab-pane label="全部" name="all" />
        <el-tab-pane name="idea">
          <template #label><span class="flex items-center gap-1.5"><el-icon><Opportunity /></el-icon> 想法</span></template>
        </el-tab-pane>
        <el-tab-pane name="excerpt">
          <template #label><span class="flex items-center gap-1.5"><el-icon><DocumentCopy /></el-icon> 摘录</span></template>
        </el-tab-pane>
        <el-tab-pane name="structure">
          <template #label><span class="flex items-center gap-1.5"><el-icon><List /></el-icon> 结构</span></template>
        </el-tab-pane>
        <el-tab-pane name="critique">
          <template #label><span class="flex items-center gap-1.5"><el-icon><ChatDotRound /></el-icon> 评价</span></template>
        </el-tab-pane>
      </el-tabs>

      <!-- 笔记流 -->
      <div class="space-y-4">
        <div v-for="note in filteredNotes" :key="note.id" 
             class="group border border-gray-100 rounded-xl p-5 hover:border-gray-300 hover:shadow-sm transition-all relative overflow-hidden bg-white">
          
          <!-- 侧边颜色条指示器 -->
          <div class="absolute left-0 top-0 bottom-0 w-1" :class="getNoteIndicatorClass(note.type)"></div>
          
          <div class="flex items-center flex-wrap gap-3 mb-3 ml-2">
            <el-tag size="small" :type="getNoteTypeTag(note.type)" effect="light" class="border-0 font-medium">
              {{ getNoteTypeLabel(note.type) }}
            </el-tag>
            
            <div v-if="note.page_number" class="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-md flex items-center">
              <el-icon class="mr-1"><Reading /></el-icon> P{{ note.page_number }}
            </div>
            
            <div v-if="note.excerpt_type" class="text-xs bg-green-50 text-green-600 px-2 py-0.5 rounded-md border border-green-100">
              {{ note.excerpt_type }}
            </div>
            
            <div v-if="note.rating" class="flex items-center">
              <el-rate v-model="note.rating" disabled size="small" />
            </div>
            
            <span class="text-xs text-gray-400 ml-auto">{{ formatDate(note.created_at) }}</span>
            <div class="flex items-center opacity-0 group-hover:opacity-100 transition-opacity ml-2">
              <el-button type="primary" link size="small" @click="editNote(note)">编辑</el-button>
              <el-button type="danger" link size="small" @click="deleteNote(note)">删除</el-button>
            </div>
          </div>
          
          <div class="ml-2">
            <h4 v-if="note.title" class="font-bold text-gray-900 mb-2">{{ note.title }}</h4>
            <div class="text-gray-600 text-sm leading-relaxed whitespace-pre-wrap font-sans" v-html="note.content"></div>
            
            <div v-if="note.action_required" class="mt-4 bg-orange-50 border border-orange-100 rounded-lg p-3 text-sm text-orange-800 flex items-start">
              <el-icon class="mt-0.5 mr-2 text-orange-500"><Warning /></el-icon>
              <div>
                <span class="font-bold block mb-0.5">下一步行动：</span>
                <span>{{ note.action_required }}</span>
              </div>
            </div>
          </div>
        </div>
        
        <div v-if="filteredNotes.length === 0" class="py-16 text-center text-gray-400">
          <el-icon class="text-4xl mb-3 opacity-50"><Document /></el-icon>
          <p>当前过滤条件下尚无笔记记录，快速开始记录吧。</p>
        </div>
      </div>
    </div>

    <!-- 弹窗部分不深度修改，仅适度应用 Tailwind utility -->
    <el-dialog v-model="noteDialogVisible" :title="getNoteDialogTitle()" width="650px" class="rounded-2xl" destroy-on-close>
      <el-form :model="noteForm" label-width="100px" class="mt-4">
        <el-form-item label="标题">
          <el-input v-model="noteForm.title" placeholder="可选，给笔记起个标题" />
        </el-form-item>
        <el-form-item label="页码">
          <div class="flex gap-4">
            <el-input-number v-model="noteForm.page_number" :min="1" placeholder="页码" class="w-32" />
            <el-input v-model="noteForm.position_info" placeholder="如：第3章方法部分..." class="flex-1" />
          </div>
        </el-form-item>
        <el-form-item v-if="noteForm.type === 'excerpt'" label="摘录类型">
          <el-select v-model="noteForm.excerpt_type" placeholder="选择摘录内容主题" class="w-1/2">
            <el-option label="核心观点" value="核心观点" />
            <el-option label="研究方法" value="研究方法" />
            <el-option label="数据结果" value="数据结果" />
            <el-option label="重要结论" value="重要结论" />
            <el-option label="关键定义" value="关键定义" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="noteForm.type === 'critique'" label="评价评分">
          <el-rate v-model="noteForm.rating" show-text :texts="['极弱', '局限', '一般', '有启发', '卓越贡献']" />
        </el-form-item>
        <el-form-item label="内容说明">
          <el-input v-model="noteForm.content" type="textarea" :rows="8" placeholder="尽情记录您的思考（支持纯文本格式）..." resize="none" />
        </el-form-item>
        <el-form-item v-if="noteForm.type === 'idea'" label="行动项">
          <el-input v-model="noteForm.action_required" placeholder="如需进一步验证或阅读其他材料..." />
        </el-form-item>
        <el-form-item v-if="noteForm.type === 'structure'">
          <div class="bg-gray-50 border border-gray-100 p-4 rounded-xl text-sm text-gray-500 w-full mb-2">
            <strong><el-icon><InfoFilled /></el-icon> 提示：</strong>结构笔记建议分层级梳理原文献的大纲。
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="flex justify-end gap-3 mt-2">
          <el-button @click="noteDialogVisible = false" class="rounded-lg">取 消</el-button>
          <el-button type="primary" @click="saveNote" class="rounded-lg px-6 shadow-md shadow-primary/20">发 布</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLiteratureStore } from '@/stores/literature'
import * as literatureApi from '@/api/literature'
import * as noteApi from '@/api/note'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, ArrowDown, Opportunity, DocumentCopy, List, ChatDotRound, Warning, InfoFilled, User, Tickets, Calendar, Link, Collection, Delete, Edit, Document, Upload, Plus, Reading } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const literatureStore = useLiteratureStore()

const loading = ref(false)
const literature = ref({})
const notes = ref([])
const activeNoteType = ref('all')
const noteDialogVisible = ref(false)
const editingNote = ref(null)

const noteForm = reactive({
  type: 'idea',
  title: '',
  content: '',
  page_number: null,
  position_info: '',
  excerpt_type: '',
  rating: 0,
  action_required: ''
})

const filteredNotes = computed(() => {
  if (activeNoteType.value === 'all') {
    return notes.value
  }
  return notes.value.filter(n => n.type === activeNoteType.value)
})

const getStatusType = (status) => {
  const types = {
    '未读': 'info',
    '摘要浏览': 'warning',
    '正在阅读': 'primary',
    '已读完': 'success',
    '需要重读': 'danger'
  }
  return types[status] || 'info'
}

const getNoteTypeLabel = (type) => {
  const labels = {
    'idea': '想法',
    'excerpt': '摘录',
    'structure': '结构',
    'critique': '评价'
  }
  return labels[type] || type
}

const getNoteTypeTag = (type) => {
  const tags = {
    'idea': 'primary',
    'excerpt': 'success',
    'structure': 'warning',
    'critique': 'danger'
  }
  return tags[type] || 'info'
}

const getNoteIndicatorClass = (type) => {
  const mapping = {
    'idea': 'bg-primary',
    'excerpt': 'bg-green-500',
    'structure': 'bg-orange-400',
    'critique': 'bg-red-500'
  }
  return mapping[type] || 'bg-gray-300'
}

const getNoteDialogTitle = () => {
  const type = noteForm.type
  const labels = {
    'idea': '✨ 记录想法灵感',
    'excerpt': '📝 摘要引用',
    'structure': '🗂️ 文章结构梳理',
    'critique': '⚖️ 评价与批判'
  }
  return editingNote.value ? `编辑${labels[type].split(' ')[1]}` : labels[type]
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

const fetchLiterature = async () => {
  loading.value = true
  try {
    literature.value = await literatureStore.fetchLiterature(route.params.id)
  } finally {
    loading.value = false
  }
}

const fetchNotes = async () => {
  const result = await noteApi.getNotes(route.params.id)
  notes.value = result
}

const updateStatus = async () => {
  await literatureStore.updateLiterature(literature.value.id, { status: literature.value.status })
  ElMessage.success('阅读状态已保存')
}

const openPdf = () => {
  if (literature.value.pdf_path) {
    window.open(`/${literature.value.pdf_path}`, '_blank')
  }
}

const handleUploadPdf = async (file) => {
  try {
    await literatureApi.uploadPdf(literature.value.id, file)
    literature.value = await literatureStore.fetchLiterature(route.params.id)
    ElMessage.success('PDF附件上传成功')
  } catch (e) {
    ElMessage.error('PDF上传失败，请检查文件大小或格式')
  }
  return false
}

const handleDeletePdf = async () => {
  try {
    await ElMessageBox.confirm('确定要移除所附的原件 PDF 吗？', '操作警告', {
      confirmButtonText: '确定移除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await literatureApi.deletePdf(literature.value.id)
    literature.value.pdf_path = null
    ElMessage.success('PDF 移除成功')
  } catch (e) {}
}

const handleDelete = async () => {
  try {
    await ElMessageBox.confirm('这篇文献连同所有阅读笔记将被彻底删除，此操作不可逆。确定继续吗？', '删除文献', {
      confirmButtonText: '确定删除',
      cancelButtonText: '保留',
      type: 'error',
      confirmButtonClass: 'el-button--danger'
    })
    await literatureStore.deleteLiterature(literature.value.id)
    ElMessage.success('文献删除完毕')
    router.push('/literatures')
  } catch (e) {}
}

const showNoteDialog = (type) => {
  editingNote.value = null
  noteForm.type = type
  noteForm.title = ''
  noteForm.content = ''
  noteForm.page_number = null
  noteForm.position_info = ''
  noteForm.excerpt_type = ''
  noteForm.rating = 0
  noteForm.action_required = ''
  noteDialogVisible.value = true
}

const editNote = (note) => {
  editingNote.value = note
  noteForm.type = note.type
  noteForm.title = note.title || ''
  noteForm.content = note.content
  noteForm.page_number = note.page_number
  noteForm.position_info = note.position_info || ''
  noteForm.excerpt_type = note.excerpt_type || ''
  noteForm.rating = note.rating || 0
  noteForm.action_required = note.action_required || ''
  noteDialogVisible.value = true
}

const saveNote = async () => {
  if (!noteForm.content) {
    ElMessage.warning('笔记不能没有内容')
    return
  }

  const data = {
    literature_id: parseInt(route.params.id),
    type: noteForm.type,
    title: noteForm.title,
    content: noteForm.content,
    page_number: noteForm.page_number,
    position_info: noteForm.position_info,
    excerpt_type: noteForm.excerpt_type,
    rating: noteForm.rating,
    action_required: noteForm.action_required
  }

  if (editingNote.value) {
    await noteApi.updateNote(editingNote.value.id, data)
    ElMessage.success('笔记已更新')
  } else {
    await noteApi.createNote(data)
    ElMessage.success('笔记增加成功')
  }

  noteDialogVisible.value = false
  fetchNotes()
}

const deleteNote = async (note) => {
  try {
    await ElMessageBox.confirm('确定要删除这条阅读记录吗？', '提示', {
      confirmButtonText: '确定丢弃',
      cancelButtonText: '手滑了',
      type: 'warning'
    })
    await noteApi.deleteNote(note.id)
    ElMessage.success('该记录已被删除')
    fetchNotes()
  } catch (e) {}
}

onMounted(() => {
  fetchLiterature()
  fetchNotes()
})
</script>

<style>
/* 移除 Tabs 底部的灰色横线使其更干净 */
.modern-tabs .el-tabs__nav-wrap::after {
  height: 1px;
  background-color: #f3f4f6;
}
.modern-tabs .el-tabs__item {
  font-size: 15px;
  font-weight: 500;
  color: #6b7280;
}
.modern-tabs .el-tabs__item.is-active {
  color: var(--el-color-primary);
  font-weight: 600;
}
</style>

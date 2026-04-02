<template>
  <div class="page-shell">
    <section class="page-hero">
      <div class="page-hero__body lg:grid-cols-[1.45fr_0.95fr]">
        <div>
          <div class="page-eyebrow">
            <span>Library Index</span>
            <span class="h-1 w-1 rounded-full bg-slate-400"></span>
            <span>Search & Organize</span>
          </div>
          <h2 class="page-title">文献列表</h2>
          <p class="page-subtitle">
            统一管理正式入库文献。支持多维筛选、标签过滤、附件判断和快速进入详情、编辑、删除等操作。
          </p>
        </div>

        <div class="hero-meta-grid self-start">
          <div class="hero-meta-tile">
            <div class="hero-meta-label">Page Items</div>
            <div class="hero-meta-value">{{ literatures.length }}</div>
          </div>
          <div class="hero-meta-tile">
            <div class="hero-meta-label">Total Records</div>
            <div class="hero-meta-value">{{ pagination.total }}</div>
          </div>
          <div class="hero-meta-tile">
            <div class="hero-meta-label">With PDF</div>
            <div class="hero-meta-value">{{ pdfCount }}</div>
          </div>
          <div class="hero-meta-tile">
            <div class="hero-meta-label">Active Tags</div>
            <div class="hero-meta-value">{{ filters.tag_ids.length }}</div>
          </div>
        </div>
      </div>
    </section>

    <section class="surface-panel">
      <div class="surface-panel__header">
        <div>
          <h3 class="surface-panel__title">检索与筛选</h3>
          <p class="surface-panel__caption">用结构化条件缩小范围，而不是在大表里反复滚动。</p>
        </div>
        <el-button type="primary" size="large" @click="$router.push('/literatures/new')">
          <template #icon>
            <el-icon><Plus /></el-icon>
          </template>
          添加文献
        </el-button>
      </div>

      <el-form label-position="top">
        <div class="filter-grid">
          <el-form-item label="标题" class="filter-span-3 !mb-0">
            <el-input v-model="filters.title" placeholder="按标题搜索" clearable />
          </el-form-item>

          <el-form-item label="作者" class="filter-span-2 !mb-0">
            <el-input v-model="filters.authors" placeholder="按作者搜索" clearable />
          </el-form-item>

          <el-form-item label="摘要" class="filter-span-3 !mb-0">
            <el-input v-model="filters.abstract" placeholder="按摘要关键词搜索" clearable />
          </el-form-item>

          <el-form-item label="标签" class="filter-span-4 !mb-0">
            <el-select
              v-model="filters.tag_ids"
              multiple
              collapse-tags
              collapse-tags-tooltip
              placeholder="选择标签"
              clearable
            >
              <el-option
                v-for="tag in allTags"
                :key="tag.tag.id"
                :label="tag.tag.name"
                :value="tag.tag.id"
              >
                <span class="flex items-center gap-2">
                  <span class="h-2 w-2 rounded-full" :style="{ backgroundColor: tag.tag.color }"></span>
                  <span>{{ tag.tag.name }}</span>
                </span>
              </el-option>
            </el-select>
          </el-form-item>

          <el-form-item label="状态" class="filter-span-2 !mb-0">
            <el-select v-model="filters.status" placeholder="全部状态" clearable>
              <el-option label="未读" value="未读" />
              <el-option label="摘要浏览" value="摘要浏览" />
              <el-option label="正在阅读" value="正在阅读" />
              <el-option label="已读完" value="已读完" />
              <el-option label="需要重读" value="需要重读" />
            </el-select>
          </el-form-item>

          <el-form-item label="语言" class="filter-span-2 !mb-0">
            <el-select v-model="filters.language" placeholder="不限" clearable>
              <el-option label="中文" value="zh" />
              <el-option label="英文" value="en" />
            </el-select>
          </el-form-item>

          <el-form-item label="年份范围" class="filter-span-4 !mb-0">
            <el-date-picker
              v-model="yearRange"
              type="yearrange"
              range-separator="至"
              start-placeholder="开始年份"
              end-placeholder="结束年份"
              value-format="YYYY"
            />
          </el-form-item>

          <el-form-item label="PDF 附件" class="filter-span-2 !mb-0">
            <el-select v-model="filters.has_pdf" placeholder="不限" clearable>
              <el-option label="有附件" :value="true" />
              <el-option label="无附件" :value="false" />
            </el-select>
          </el-form-item>

          <div class="filter-span-12 flex flex-wrap items-center justify-between gap-4">
            <div class="insight-strip">
              <div class="insight-chip">
                <span>当前页共 <strong>{{ literatures.length }}</strong> 篇</span>
              </div>
              <div class="insight-chip">
                <span>命中标签 <strong>{{ filters.tag_ids.length || 0 }}</strong> 个</span>
              </div>
              <div class="insight-chip">
                <span>附件文献 <strong>{{ pdfCount }}</strong> 篇</span>
              </div>
            </div>

            <div class="flex flex-wrap gap-3">
              <el-button @click="resetFilters">重置</el-button>
              <el-button type="primary" :loading="loading" @click="handleFilter">应用筛选</el-button>
            </div>
          </div>
        </div>
      </el-form>
    </section>

    <section class="surface-panel table-shell">
      <div class="surface-panel__header">
        <div>
          <h3 class="surface-panel__title">正式文献库</h3>
          <p class="surface-panel__caption">聚焦标题、作者、状态、标签与附件，适合高频管理和检索。</p>
        </div>
      </div>

      <el-table v-loading="loading" :data="literatures" style="width: 100%">
        <el-table-column prop="title" label="标题" min-width="330">
          <template #default="{ row }">
            <div class="flex flex-col gap-2 py-1">
              <router-link
                :to="`/literatures/${row.id}`"
                class="line-clamp-2 text-[15px] font-semibold text-slate-950 no-underline transition-colors hover:text-slate-700"
              >
                {{ row.title }}
              </router-link>
              <div class="flex flex-wrap items-center gap-3 text-sm text-slate-500">
                <span class="inline-flex items-center gap-1">
                  <el-icon><User /></el-icon>
                  <span class="line-clamp-1 max-w-[220px]">{{ row.authors || '未填写作者' }}</span>
                </span>
                <span v-if="row.journal" class="inline-flex items-center gap-1">
                  <el-icon><Tickets /></el-icon>
                  <span class="line-clamp-1 max-w-[190px] italic">{{ row.journal }}</span>
                </span>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="year" label="年份" width="96" align="center">
          <template #default="{ row }">
            <span class="rounded-full bg-slate-100 px-3 py-1 text-sm font-semibold text-slate-700">
              {{ row.year || '-' }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="130" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" effect="light" round>
              {{ row.status || '未读' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="tags" label="标签" min-width="180">
          <template #default="{ row }">
            <div class="flex flex-wrap gap-1.5">
              <span
                v-for="tag in row.tags?.slice(0, 3)"
                :key="tag.id"
                class="rounded-full px-2.5 py-1 text-xs font-semibold text-white shadow-sm"
                :style="{ backgroundColor: tag.color }"
              >
                {{ tag.name }}
              </span>
              <span
                v-if="row.tags?.length > 3"
                class="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-500"
              >
                +{{ row.tags.length - 3 }}
              </span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="pdf_path" label="附件" width="90" align="center">
          <template #default="{ row }">
            <el-button
              v-if="row.pdf_path"
              circle
              plain
              type="danger"
              @click="openPdf(row)"
            >
              <el-icon><Document /></el-icon>
            </el-button>
            <span v-else class="text-slate-300">-</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="190" fixed="right" align="right">
          <template #default="{ row }">
            <div class="flex items-center justify-end gap-2">
              <el-tooltip content="查看详情">
                <el-button circle plain @click="$router.push(`/literatures/${row.id}`)">
                  <el-icon><View /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="编辑">
                <el-button circle plain type="primary" @click="$router.push(`/literatures/${row.id}/edit`)">
                  <el-icon><Edit /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="删除">
                <el-button circle plain type="danger" @click="handleDelete(row)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="mt-8 flex justify-end">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.perPage"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useLiteratureStore } from '@/stores/literature'
import { useTagStore } from '@/stores/tag'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Document, Edit, Plus, Tickets, User, View } from '@element-plus/icons-vue'

const router = useRouter()
const literatureStore = useLiteratureStore()
const tagStore = useTagStore()

const literatures = ref([])
const allTags = ref([])
const loading = ref(false)
const yearRange = ref(null)

const filters = reactive({
  title: '',
  authors: '',
  abstract: '',
  tag_ids: [],
  status: null,
  language: null,
  has_pdf: null
})

const pagination = reactive({
  page: 1,
  perPage: 10,
  total: 0
})

const pdfCount = computed(() => literatures.value.filter(item => item.pdf_path).length)

const getStatusType = (status) => {
  const types = {
    未读: 'info',
    摘要浏览: 'warning',
    正在阅读: 'primary',
    已读完: 'success',
    需要重读: 'danger'
  }
  return types[status] || 'info'
}

const fetchLiteratures = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      per_page: pagination.perPage,
      status: filters.status,
      language: filters.language,
      tag_ids: filters.tag_ids.length > 0 ? filters.tag_ids : null,
      has_pdf: filters.has_pdf,
      title: filters.title || null,
      authors: filters.authors || null,
      abstract: filters.abstract || null
    }

    if (yearRange.value) {
      params.year_start = parseInt(yearRange.value[0], 10)
      params.year_end = parseInt(yearRange.value[1], 10)
    }

    const result = await literatureStore.fetchLiteratures(params)
    literatures.value = result.items
    pagination.total = result.total
  } finally {
    loading.value = false
  }
}

const handleFilter = () => {
  pagination.page = 1
  fetchLiteratures()
}

const resetFilters = () => {
  filters.title = ''
  filters.authors = ''
  filters.abstract = ''
  filters.tag_ids = []
  filters.status = null
  filters.language = null
  filters.has_pdf = null
  yearRange.value = null
  pagination.page = 1
  fetchLiteratures()
}

const handleSizeChange = (size) => {
  pagination.perPage = size
  pagination.page = 1
  fetchLiteratures()
}

const handlePageChange = (page) => {
  pagination.page = page
  fetchLiteratures()
}

const openPdf = (literature) => {
  if (literature.pdf_path) {
    window.open(`/${literature.pdf_path}`, '_blank')
  }
}

const handleDelete = async (literature) => {
  try {
    await ElMessageBox.confirm('确定要删除这篇文献吗？此操作不可撤销。', '删除确认', {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'error'
    })

    await literatureStore.deleteLiterature(literature.id)
    ElMessage.success('文献已删除')
    fetchLiteratures()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败，请重试')
    }
  }
}

onMounted(async () => {
  allTags.value = await tagStore.fetchTags()
  fetchLiteratures()
})
</script>

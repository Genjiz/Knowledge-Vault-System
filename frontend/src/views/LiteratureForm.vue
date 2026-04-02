<template>
  <div class="max-w-4xl mx-auto pb-16">
    <div class="mb-8 flex items-center justify-between">
      <el-button @click="$router.back()" class="rounded-lg shadow-sm border-gray-200 hover:bg-gray-50 text-gray-700">
        <el-icon class="mr-1"><ArrowLeft /></el-icon>
        返回
      </el-button>
      <h2 class="text-2xl font-bold text-gray-900 tracking-tight">{{ isEdit ? '编辑文献资料' : '添加新文献' }}</h2>
      <div class="w-20"></div> <!-- 占位保持居中对齐 -->
    </div>

    <div class="bg-surface rounded-2xl shadow-soft p-8 relative overflow-hidden">
      <!-- 装饰背景 -->
      <div class="absolute top-0 right-0 w-64 h-64 bg-primary-light-9 rounded-bl-full opacity-50 pointer-events-none -mr-10 -mt-10"></div>
      
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" class="relative z-10 custom-form">
        <!-- 核心信息区 -->
        <h3 class="text-lg font-bold text-gray-800 mb-6 flex items-center">
          <span class="w-1.5 h-5 bg-primary rounded-full mr-2"></span>
          核心元数据
        </h3>
        
        <el-form-item label="文献标题" prop="title">
          <el-input v-model="form.title" placeholder="如：Attention Is All You Need" size="large" class="modern-input" />
        </el-form-item>

        <el-form-item label="作者" prop="authors">
          <el-input v-model="form.authors" placeholder="多个作者以逗号分隔，如：Ashish Vaswani, Noam Shazeer..." size="large" class="modern-input" />
        </el-form-item>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <el-form-item label="来源期刊 / 会议" class="lg:col-span-2">
            <el-input v-model="form.journal" placeholder="如：NIPS 2017" size="large" class="modern-input" />
          </el-form-item>
          
          <el-form-item label="发表年份">
            <el-input-number v-model="form.year" :min="1900" :max="2100" class="w-full" size="large" controls-position="right" />
          </el-form-item>
          
          <el-form-item label="文献类型">
            <el-select v-model="form.literature_type" class="w-full" size="large">
              <el-option label="期刊文章" value="journal" />
              <el-option label="会议论文" value="conference" />
              <el-option label="学位论文" value="thesis" />
              <el-option label="图书章节" value="book" />
            </el-select>
          </el-form-item>
        </div>

        <div class="border-t border-gray-100 my-8"></div>

        <!-- 分类与状态区 -->
        <h3 class="text-lg font-bold text-gray-800 mb-6 flex items-center">
          <span class="w-1.5 h-5 bg-green-500 rounded-full mr-2"></span>
          分类与状态
        </h3>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-2">
          <el-form-item label="使用语言">
            <el-select v-model="form.language" class="w-full" size="large">
              <el-option label="简体中文 (zh-CN)" value="zh" />
              <el-option label="English (en-US)" value="en" />
            </el-select>
          </el-form-item>
          
          <el-form-item label="当前阅读状态">
             <el-select v-model="form.status" class="w-full" size="large">
              <el-option label="📌 未读" value="未读" />
              <el-option label="👀 摘要浏览" value="摘要浏览" />
              <el-option label="📖 正在阅读" value="正在阅读" />
              <el-option label="✅ 已读完" value="已读完" />
              <el-option label="🔄 需要重读" value="需要重读" />
            </el-select>
          </el-form-item>
        </div>

        <el-form-item label="内容摘要">
          <el-input v-model="form.abstract" type="textarea" :rows="5" placeholder="可粘贴原论文的 Abstract，方便后续检索..." class="modern-textarea" />
        </el-form-item>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-2">
          <el-form-item label="关键词">
            <el-input v-model="form.keywords" placeholder="以逗号分隔，如：Deep Learning, NLP" size="large" class="modern-input" />
          </el-form-item>

          <el-form-item label="知识标签">
            <el-select 
              v-model="form.tag_ids" 
              multiple 
              filterable 
              allow-create
              default-first-option
              placeholder="选择已有标签或直接回车创建" 
              class="w-full modern-select"
              size="large"
              @change="handleTagChange"
            >
              <el-option 
                v-for="tag in availableTags" 
                :key="tag.id" 
                :label="tag.name" 
                :value="tag.id"
              >
                <span class="flex items-center gap-2">
                  <span class="w-3 h-3 rounded-full" :style="{ backgroundColor: tag.color }"></span>
                  {{ tag.name }}
                </span>
              </el-option>
            </el-select>
          </el-form-item>
        </div>

        <div class="border-t border-gray-100 my-8"></div>

        <!-- 附件与高级区 -->
        <h3 class="text-lg font-bold text-gray-800 mb-6 flex items-center">
          <span class="w-1.5 h-5 bg-orange-400 rounded-full mr-2"></span>
          原件附件
        </h3>

        <el-form-item>
          <div class="w-full border-2 border-dashed border-gray-200 rounded-2xl p-6 text-center hover:border-primary transition-colors bg-gray-50/50" v-if="!form.pdf_path && !pdfFile">
            <el-upload 
              :show-file-list="false" 
              accept=".pdf" 
              :before-upload="handlePdfSelect"
              class="w-full"
              drag
            >
              <el-icon class="text-4xl text-gray-400 mb-2"><UploadFilled /></el-icon>
              <div class="text-gray-700 font-medium text-lg">点击或拖拽上传 PDF 原件</div>
              <div class="text-gray-400 text-sm mt-1">系统将尝试自动提取标题、作者与摘要等元数据</div>
            </el-upload>
          </div>
          
          <div v-else class="flex flex-col md:flex-row items-center justify-between w-full bg-primary-light-9 p-4 rounded-xl border border-primary-light-8">
            <div class="flex items-center gap-3">
              <div class="w-12 h-12 bg-white rounded-lg flex items-center justify-center text-primary shadow-sm">
                <el-icon class="text-2xl"><Document /></el-icon>
              </div>
              <div class="flex flex-col">
                <span class="font-bold text-gray-800 line-clamp-1 break-all">{{ pdfFile?.name || form.pdf_path.split('/').pop() }}</span>
                <span class="text-xs text-primary-light-3">PDF 附件已就绪</span>
              </div>
            </div>
            <el-button type="danger" plain size="small" @click="removePdf" class="mt-3 md:mt-0 rounded-lg bg-white">移除该文件</el-button>
          </div>
        </el-form-item>

        <div class="mt-8">
          <el-collapse class="modern-collapse border-none">
            <el-collapse-item name="advanced">
              <template #title>
                <span class="font-bold text-gray-600 flex items-center text-base">
                  <el-icon class="mr-2"><Setting /></el-icon> 展开高级选项 (卷/期/页码/DOI...)
                </span>
              </template>
              <div class="p-6 bg-gray-50/80 rounded-xl mt-4 space-y-4 border border-gray-100">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <el-form-item label="DOI (数字对象标识符)">
                    <el-input v-model="form.doi" placeholder="如：10.1000/xyz123" class="modern-input" />
                  </el-form-item>
                  <el-form-item label="在线链接">
                    <el-input v-model="form.url" placeholder="论文的来源 URL" class="modern-input">
                      <template #prefix><el-icon><Link /></el-icon></template>
                    </el-input>
                  </el-form-item>
                </div>
                
                <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <el-form-item label="卷 (Volume)">
                    <el-input v-model="form.volume" class="modern-input" />
                  </el-form-item>
                  <el-form-item label="期 (Issue)">
                    <el-input v-model="form.issue" class="modern-input" />
                  </el-form-item>
                  <el-form-item label="页码 (Pages)">
                    <el-input v-model="form.pages" placeholder="如：123-135" class="modern-input" />
                  </el-form-item>
                </div>
                
                <el-form-item label="出版方 / 学校">
                  <el-input v-model="form.publisher" placeholder="如学位论文可填写颁发学位的学校" class="modern-input" />
                </el-form-item>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>

        <!-- 提交浮动工具栏 -->
        <div class="mt-10 flex items-center justify-end gap-4 p-5 bg-gray-50 rounded-xl shadow-inner border border-gray-100">
          <span class="text-gray-400 text-sm mr-auto">所有带 <span class="text-red-500">*</span> 的通常为必填项。</span>
          <el-button size="large" @click="$router.back()" class="rounded-xl border-gray-300 px-8 hover:bg-white hover:text-gray-900">取 消</el-button>
          <el-button type="primary" size="large" @click="handleSubmit" :loading="submitting" class="rounded-xl px-10 shadow-md shadow-primary/20 text-base">
            {{ isEdit ? '保 存 更 新' : '建 立 档 案' }}
          </el-button>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLiteratureStore } from '@/stores/literature'
import { useTagStore } from '@/stores/tag'
import * as literatureApi from '@/api/literature'
import * as tagApi from '@/api/tag'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Document, UploadFilled, Setting, Link } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const literatureStore = useLiteratureStore()
const tagStore = useTagStore()

const formRef = ref(null)
const submitting = ref(false)
const pdfFile = ref(null)
const availableTags = ref([])

const isEdit = computed(() => !!route.params.id)

const form = reactive({
  title: '',
  authors: '',
  journal: '',
  year: null,
  volume: '',
  issue: '',
  pages: '',
  doi: '',
  abstract: '',
  keywords: '',
  pdf_path: '',
  url: '',
  language: 'en',
  literature_type: 'journal',
  publisher: '',
  status: '未读',
  tag_ids: []
})

const rules = {
  title: [{ required: true, message: '必须输入一篇文章标题', trigger: 'blur' }],
  authors: [{ required: true, message: '请填写至少一名作者信息', trigger: 'blur' }]
}

const handleTagChange = async (selectedIds) => {
  const newTagId = selectedIds.find(id => typeof id === 'string' && !availableTags.value.find(t => t.id === id))
  
  if (newTagId && typeof newTagId === 'string') {
    try {
      const newTag = await tagApi.createTag({ name: newTagId, color: '#002FA7' })
      availableTags.value.push(newTag)
      const index = form.tag_ids.indexOf(newTagId)
      if (index !== -1) {
        form.tag_ids[index] = newTag.id
      }
      ElMessage.success(`全新标签 "${newTagId}" 已建立`)
    } catch (e) {
      const index = form.tag_ids.indexOf(newTagId)
      if (index !== -1) {
        form.tag_ids.splice(index, 1)
      }
      ElMessage.error('创建新标签失败')
    }
  }
}

const handlePdfSelect = async (file) => {
  pdfFile.value = file
  
  try {
    const extracted = await extractPdfMetadata(file)
    if (extracted.title && !form.title) {
      form.title = extracted.title
    }
    if (extracted.authors && !form.authors) {
      form.authors = extracted.authors
    }
    if (extracted.abstract && !form.abstract) {
      form.abstract = extracted.abstract
    }
    if (extracted.keywords && !form.keywords) {
      form.keywords = extracted.keywords
    }
    if (extracted.year && !form.year) {
      form.year = extracted.year
    }
    if (extracted.language) {
      form.language = extracted.language
    }
    ElMessage.success('已聪慧地从 PDF 文档中解析出可用元数据 ✨')
  } catch (e) {
    console.log('PDF元数据识别失败', e)
  }
  
  return false
}

const extractPdfMetadata = async (file) => {
  return new Promise((resolve) => {
    const reader = new FileReader()
    reader.onload = async (e) => {
      try {
        const typedArray = new Uint8Array(e.target.result)
        const pdf = await pdfjsLib.getDocument(typedArray).promise
        const metadata = await pdf.getMetadata()
        
        let info = metadata.info || {}
        let result = {
          title: info.Title || '',
          authors: info.Author || '',
          abstract: '',
          keywords: info.Keywords || '',
          year: null,
          language: 'en'
        }
        
        if (info.CreationDate) {
          const yearMatch = info.CreationDate.match(/D:(\d{4})/)
          if (yearMatch) {
            result.year = parseInt(yearMatch[1])
          }
        }
        
        if (result.title && /[\u4e00-\u9fa5]/.test(result.title)) {
          result.language = 'zh'
        }
        
        const firstPage = await pdf.getPage(1)
        const textContent = await firstPage.getTextContent()
        const text = textContent.items.map(item => item.str).join(' ')
        
        if (!result.abstract) {
          const abstractMatch = text.match(/(?:Abstract|摘要)[：:\s]*([\s\S]{50,500}?)(?=\n\n|Keywords|关键词|Introduction|引言|$)/i)
          if (abstractMatch) {
            result.abstract = abstractMatch[1].trim().substring(0, 500)
          }
        }
        
        if (!result.keywords) {
          const keywordsMatch = text.match(/(?:Keywords|关键词)[：:\s]*([^\n]+)/i)
          if (keywordsMatch) {
            result.keywords = keywordsMatch[1].trim()
          }
        }
        
        resolve(result)
      } catch (err) {
        resolve({})
      }
    }
    reader.readAsArrayBuffer(file)
  })
}

const removePdf = () => {
  pdfFile.value = null
  form.pdf_path = ''
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
  } catch {
    ElMessage.warning('请检查并完善带红星的必填表单项')
    return
  }

  submitting.value = true
  try {
    const data = { ...form }
    
    if (isEdit.value) {
      await literatureStore.updateLiterature(route.params.id, data)
      
      if (pdfFile.value) {
        await literatureApi.uploadPdf(route.params.id, pdfFile.value)
      }
      
      ElMessage.success('文档资料编辑已妥善保存')
    } else {
      const newLiterature = await literatureStore.createLiterature(data)
      
      if (pdfFile.value) {
        await literatureApi.uploadPdf(newLiterature.id, pdfFile.value)
      }
      
      ElMessage.success('成功收入新的文献！')
    }
    
    router.push('/literatures')
  } catch (e) {
    ElMessage.error('服务器遇到了意外，提交失败。')
  } finally {
    submitting.value = false
  }
}

const fetchLiterature = async () => {
  if (!isEdit.value) return
  
  const literature = await literatureStore.fetchLiterature(route.params.id)
  Object.assign(form, {
    title: literature.title,
    authors: literature.authors,
    journal: literature.journal || '',
    year: literature.year,
    volume: literature.volume || '',
    issue: literature.issue || '',
    pages: literature.pages || '',
    doi: literature.doi || '',
    abstract: literature.abstract || '',
    keywords: literature.keywords || '',
    pdf_path: literature.pdf_path || '',
    url: literature.url || '',
    language: literature.language || 'en',
    literature_type: literature.literature_type || 'journal',
    publisher: literature.publisher || '',
    status: literature.status || '未读',
    tag_ids: literature.tags?.map(t => t.id) || []
  })
}

onMounted(async () => {
  const result = await tagStore.fetchTags()
  availableTags.value = result.map(t => t.tag)
  fetchLiterature()
})
</script>

<style>
/* 根据现代设计美学专门覆盖和美化部分 Element 表单组件 */
.custom-form .el-form-item__label {
  font-weight: 600 !important;
  color: #4b5563 !important;
  padding-bottom: 6px !important;
}

.modern-input .el-input__wrapper,
.modern-textarea .el-textarea__inner,
.modern-select .el-select__wrapper {
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05) !important;
  border-radius: 8px !important;
  background-color: #fafafa !important;
  transition: all 0.2s ease;
}

.modern-input .el-input__wrapper:hover,
.modern-textarea .el-textarea__inner:hover,
.modern-select .el-select__wrapper:hover {
  background-color: #fff !important;
  box-shadow: 0 0 0 1px #d1d5db !important;
}

.modern-input .el-input__wrapper.is-focus,
.modern-textarea .el-textarea__inner:focus,
.modern-select .el-select__wrapper.is-focused {
  background-color: #fff !important;
  box-shadow: 0 0 0 2px rgba(0, 47, 167, 0.2) !important;
}

/* 覆盖 el-collapse 默认生硬边框 */
.modern-collapse {
  border: none !important;
}
.modern-collapse .el-collapse-item__header {
  border-bottom: none !important;
  background-color: transparent !important;
}
.modern-collapse .el-collapse-item__wrap {
  border-bottom: none !important;
  background-color: transparent !important;
}
</style>

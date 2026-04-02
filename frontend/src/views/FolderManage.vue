<template>
  <div class="page-shell">
    <section class="page-hero">
      <div class="page-hero__body lg:grid-cols-[1.45fr_0.95fr]">
        <div>
          <div class="page-eyebrow">
            <span>Structure Map</span>
            <span class="h-1 w-1 rounded-full bg-slate-400"></span>
            <span>Folders</span>
          </div>
          <h2 class="page-title">文件夹管理</h2>
          <p class="page-subtitle">
            用层级结构组织正式文献。文件夹适合表达长期稳定的研究主题，而不是临时筛选条件。
          </p>
        </div>

        <div class="hero-meta-grid self-start">
          <div class="hero-meta-tile">
            <div class="hero-meta-label">Root Nodes</div>
            <div class="hero-meta-value">{{ folderTree.length }}</div>
          </div>
          <div class="hero-meta-tile">
            <div class="hero-meta-label">All Folders</div>
            <div class="hero-meta-value">{{ flatFolderList.length }}</div>
          </div>
          <div class="hero-meta-tile">
            <div class="hero-meta-label">Deepest Path</div>
            <div class="hero-meta-value">{{ deepestDepth }}</div>
          </div>
        </div>
      </div>
    </section>

    <section class="surface-panel">
      <div class="surface-panel__header">
        <div>
          <h3 class="surface-panel__title">层级工作区</h3>
          <p class="surface-panel__caption">保持层级清晰，避免同一主题在多个路径中重复出现。</p>
        </div>
        <el-button type="primary" size="large" @click="showDialog()">添加文件夹</el-button>
      </div>

      <div class="insight-strip">
        <div class="insight-chip">
          <span>当前总层级深度 <strong>{{ deepestDepth }}</strong></span>
        </div>
        <div class="insight-chip">
          <span>可选父级 <strong>{{ flatFolderList.length }}</strong> 个</span>
        </div>
      </div>
    </section>

    <section class="surface-panel">
      <div class="surface-panel__header">
        <div>
          <h3 class="surface-panel__title">文件夹树</h3>
          <p class="surface-panel__caption">悬停节点即可快速添加子文件夹、编辑或删除。</p>
        </div>
      </div>

      <el-tree
        v-if="folderTree.length > 0"
        :data="folderTree"
        :props="treeProps"
        node-key="id"
        default-expand-all
        :expand-on-click-node="false"
        class="folder-tree"
      >
        <template #default="{ data }">
          <div class="flex w-full items-center justify-between gap-4 rounded-2xl px-3 py-3 transition-colors hover:bg-slate-50">
            <span class="inline-flex items-center gap-2 font-medium text-slate-800">
              <el-icon><Folder /></el-icon>
              {{ data.name }}
            </span>
            <span class="flex items-center gap-2 opacity-70 transition-opacity hover:opacity-100">
              <el-button plain size="small" @click.stop="showDialog(null, data)">添加子文件夹</el-button>
              <el-button plain size="small" @click.stop="showDialog(data)">编辑</el-button>
              <el-button plain size="small" type="danger" @click.stop="handleDelete(data)">删除</el-button>
            </span>
          </div>
        </template>
      </el-tree>

      <el-empty v-else description="暂无文件夹，点击上方按钮开始创建"></el-empty>
    </section>

    <el-dialog v-model="dialogVisible" :title="editingFolder ? '编辑文件夹' : '添加文件夹'" width="460px">
      <el-form :model="folderForm" label-position="top">
        <el-form-item label="名称">
          <el-input v-model="folderForm.name" placeholder="请输入文件夹名称" />
        </el-form-item>
        <el-form-item label="父文件夹">
          <el-select
            v-model="folderForm.parent_id"
            placeholder="选择父文件夹（可选）"
            clearable
            style="width: 100%;"
          >
            <el-option
              v-for="folder in flatFolderList"
              :key="folder.id"
              :label="folder.fullPath"
              :value="folder.id"
              :disabled="editingFolder && folder.id === editingFolder.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveFolder">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import * as folderApi from '@/api/folder'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Folder } from '@element-plus/icons-vue'

const folderTree = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const editingFolder = ref(null)

const treeProps = {
  children: 'children',
  label: 'name'
}

const folderForm = reactive({
  name: '',
  parent_id: null
})

const flatFolderList = computed(() => {
  const list = []
  const flatten = (folders, path = '') => {
    for (const folder of folders) {
      const fullPath = path ? `${path} / ${folder.name}` : folder.name
      list.push({ id: folder.id, name: folder.name, fullPath })
      if (folder.children?.length) flatten(folder.children, fullPath)
    }
  }
  flatten(folderTree.value)
  return list
})

const deepestDepth = computed(() => {
  const getDepth = (folders, depth = 1) => {
    if (!folders.length) return depth - 1
    return Math.max(...folders.map(folder => getDepth(folder.children || [], depth + 1)))
  }
  return getDepth(folderTree.value)
})

const fetchFolders = async () => {
  loading.value = true
  try {
    folderTree.value = await folderApi.getFolders()
  } finally {
    loading.value = false
  }
}

const showDialog = (folder = null, parent = null) => {
  editingFolder.value = folder
  if (folder) {
    folderForm.name = folder.name
    folderForm.parent_id = folder.parent_id
  } else {
    folderForm.name = ''
    folderForm.parent_id = parent ? parent.id : null
  }
  dialogVisible.value = true
}

const saveFolder = async () => {
  if (!folderForm.name.trim()) {
    ElMessage.warning('请输入文件夹名称')
    return
  }

  try {
    if (editingFolder.value) {
      await folderApi.updateFolder(editingFolder.value.id, {
        name: folderForm.name,
        parent_id: folderForm.parent_id
      })
      ElMessage.success('文件夹已更新')
    } else {
      await folderApi.createFolder({
        name: folderForm.name,
        parent_id: folderForm.parent_id
      })
      ElMessage.success('文件夹已创建')
    }
    dialogVisible.value = false
    fetchFolders()
  } catch {
    ElMessage.error('操作失败')
  }
}

const handleDelete = async (folder) => {
  try {
    await ElMessageBox.confirm('删除文件夹将同时删除其中的子文件夹，确定要继续吗？', '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await folderApi.deleteFolder(folder.id)
    ElMessage.success('文件夹已删除')
    fetchFolders()
  } catch {}
}

onMounted(() => {
  fetchFolders()
})
</script>

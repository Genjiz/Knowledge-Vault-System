<template>
  <el-container class="h-screen overflow-hidden bg-surface-muted font-sans text-slate-800">
    <el-aside width="264px" class="border-r border-slate-200/70 bg-white/92 shadow-[0_18px_60px_-40px_rgba(15,23,42,0.45)] backdrop-blur">
      <div class="flex h-20 items-center border-b border-slate-200/70 px-6">
        <div>
          <p class="text-[11px] uppercase tracking-[0.35em] text-slate-400">Knowledge Workspace</p>
          <h1 class="mt-2 text-xl font-black tracking-tight text-slate-950">Knowledge Vault</h1>
        </div>
      </div>

      <el-menu
        :default-active="activeMenu"
        router
        class="border-r-0 px-3 py-5"
        active-text-color="var(--el-color-primary)"
        text-color="#475569"
      >
        <div class="mb-2 px-3 text-[11px] uppercase tracking-[0.28em] text-slate-400">Workspace</div>
        <el-menu-item index="/" class="mb-1 rounded-2xl">
          <el-icon><House /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/literatures" class="mb-1 rounded-2xl">
          <el-icon><Document /></el-icon>
          <span>文献列表</span>
        </el-menu-item>
        <el-menu-item index="/tags" class="mb-1 rounded-2xl">
          <el-icon><PriceTag /></el-icon>
          <span>标签管理</span>
        </el-menu-item>
        <el-menu-item index="/folders" class="mb-1 rounded-2xl">
          <el-icon><Folder /></el-icon>
          <span>文件夹管理</span>
        </el-menu-item>
        <el-menu-item index="/statistics" class="mb-1 rounded-2xl">
          <el-icon><DataAnalysis /></el-icon>
          <span>统计分析</span>
        </el-menu-item>

        <div class="mx-3 my-4 border-t border-slate-200/70"></div>

        <div class="mb-2 px-3 text-[11px] uppercase tracking-[0.28em] text-slate-400">Collection</div>
        <el-menu-item index="/crawler/tasks" class="mb-1 rounded-2xl">
          <el-icon><Files /></el-icon>
          <span>采集任务台</span>
        </el-menu-item>
        <el-menu-item index="/crawler/issues" class="mb-1 rounded-2xl">
          <el-icon><Reading /></el-icon>
          <span>采集期号库</span>
        </el-menu-item>

        <div class="mx-3 my-4 border-t border-slate-200/70"></div>

        <div class="mb-2 px-3 text-[11px] uppercase tracking-[0.28em] text-slate-400">Media</div>
        <el-menu-item index="/video-notes" class="mb-1 rounded-2xl">
          <el-icon><VideoPlay /></el-icon>
          <span>视频转笔记</span>
        </el-menu-item>
        <el-menu-item index="/video-notes/tasks" class="mb-1 rounded-2xl">
          <el-icon><Tickets /></el-icon>
          <span>视频任务列表</span>
        </el-menu-item>

        <div class="mx-3 my-4 border-t border-slate-200/70"></div>

        <div class="mb-2 px-3 text-[11px] uppercase tracking-[0.28em] text-slate-400">Utilities</div>
        <el-menu-item index="/import" class="mb-1 rounded-2xl">
          <el-icon><Upload /></el-icon>
          <span>导入文献</span>
        </el-menu-item>
        <el-menu-item index="/backup" class="mb-1 rounded-2xl">
          <el-icon><Download /></el-icon>
          <span>备份恢复</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-main class="overflow-y-auto bg-[radial-gradient(circle_at_top,_rgba(148,163,184,0.16),_transparent_24%),linear-gradient(180deg,_#f8fafc,_#eef2f7)] p-0">
      <div class="mx-auto flex min-h-full w-full max-w-[1440px] flex-col gap-6 px-6 py-6 lg:px-8">
        <router-view v-slot="{ Component }">
          <transition name="fade-slide" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </el-main>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  DataAnalysis,
  Document,
  Download,
  Files,
  Folder,
  House,
  PriceTag,
  Reading,
  Tickets,
  Upload,
  VideoPlay
} from '@element-plus/icons-vue'

const route = useRoute()
const activeMenu = computed(() => {
  if (route.path.startsWith('/crawler/issues')) return '/crawler/issues'
  if (route.path.startsWith('/video-notes/tasks')) return '/video-notes/tasks'
  if (route.path.startsWith('/video-notes')) return '/video-notes'
  return route.path
})
</script>

<style>
.el-menu-item {
  height: 46px;
  margin-left: 0.25rem;
  margin-right: 0.25rem;
  font-weight: 500;
}

.el-menu-item.is-active {
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.96), rgba(30, 41, 59, 0.92)) !important;
  color: #f8fafc !important;
  box-shadow: 0 18px 44px -24px rgba(15, 23, 42, 0.8);
}

.el-menu-item.is-active .el-icon,
.el-menu-item.is-active span {
  color: #f8fafc !important;
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: opacity 0.24s ease, transform 0.24s ease;
}

.fade-slide-enter-from,
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>

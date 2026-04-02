import { createApp } from 'vue'
import { createPinia } from 'pinia'
import {
  ElAlert,
  ElAside,
  ElButton,
  ElCard,
  ElCollapse,
  ElCollapseItem,
  ElColorPicker,
  ElContainer,
  ElDatePicker,
  ElDescriptions,
  ElDescriptionsItem,
  ElDialog,
  ElDropdown,
  ElDropdownItem,
  ElDropdownMenu,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElIcon,
  ElInput,
  ElInputNumber,
  ElLoading,
  ElMain,
  ElMenu,
  ElMenuItem,
  ElOption,
  ElPagination,
  ElRadio,
  ElRadioButton,
  ElRadioGroup,
  ElRate,
  ElSelect,
  ElTabPane,
  ElTable,
  ElTableColumn,
  ElTabs,
  ElTag,
  ElTooltip,
  ElTree,
  ElUpload
} from 'element-plus'
import 'element-plus/dist/index.css'
import './style.css'

import App from './App.vue'
import router from './router'

const app = createApp(App)

const elementComponents = [
  ElAlert,
  ElAside,
  ElButton,
  ElCard,
  ElCollapse,
  ElCollapseItem,
  ElColorPicker,
  ElContainer,
  ElDatePicker,
  ElDescriptions,
  ElDescriptionsItem,
  ElDialog,
  ElDropdown,
  ElDropdownItem,
  ElDropdownMenu,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElIcon,
  ElInput,
  ElInputNumber,
  ElMain,
  ElMenu,
  ElMenuItem,
  ElOption,
  ElPagination,
  ElRadio,
  ElRadioButton,
  ElRadioGroup,
  ElRate,
  ElSelect,
  ElTabPane,
  ElTable,
  ElTableColumn,
  ElTabs,
  ElTag,
  ElTooltip,
  ElTree,
  ElUpload
]

for (const component of elementComponents) {
  app.component(component.name, component)
}

app.use(createPinia())
app.use(router)
app.use(ElLoading)

app.mount('#app')

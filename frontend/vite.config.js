import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// Vite 配置：启用 Vue 单文件组件解析
export default defineConfig({
  plugins: [vue()],
});

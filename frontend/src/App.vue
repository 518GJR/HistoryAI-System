<template>
  <main class="page">
    <section class="chat-panel">
      <header class="panel-header">
        <p class="eyebrow">HistoryAI</p>
        <h1>中小学历史知识问答</h1>
      </header>

      <div class="message-list">
        <div
          v-for="message in messages"
          :key="message.id"
          class="message"
          :class="message.role"
        >
          <span class="role-label">{{ message.role === "user" ? "我" : "AI" }}</span>
          <p>{{ message.content }}</p>
          <ul v-if="message.sources && message.sources.length" class="source-list">
            <li v-for="source in message.sources" :key="source.title">
              {{ source.title }} · {{ source.dynasty || "未标注朝代" }} · 分数 {{ source.score }}
            </li>
          </ul>
        </div>
      </div>

      <form class="input-area" @submit.prevent="sendQuestion">
        <input
          v-model="question"
          type="text"
          placeholder="请输入历史问题，例如：秦始皇为什么统一六国？"
        />
        <button type="submit" :disabled="loading || !question.trim()">
          {{ loading ? "发送中" : "发送" }}
        </button>
      </form>
    </section>
  </main>
</template>

<script setup>
import { ref } from "vue";

// 后端接口地址，开发阶段默认连接本地 FastAPI 服务
const API_URL = "http://localhost:8000/api/question";

const question = ref("");
const loading = ref(false);
const messages = ref([
  {
    id: 1,
    role: "assistant",
    content: "你好，我可以帮助你梳理中小学历史知识点。",
  },
]);

// 发送问题到后端，并将回答展示到聊天窗口
async function sendQuestion() {
  const text = question.value.trim();
  if (!text) return;

  messages.value.push({
    id: Date.now(),
    role: "user",
    content: text,
  });

  question.value = "";
  loading.value = true;

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ question: text }),
    });

    const data = await response.json();
    messages.value.push({
      id: Date.now() + 1,
      role: "assistant",
      content: data.answer || "暂时没有生成回答。",
      // 保存后端返回的知识来源，方便用户判断回答依据
      sources: data.sources || [],
    });
  } catch (error) {
    messages.value.push({
      id: Date.now() + 1,
      role: "assistant",
      content: "后端服务暂时无法访问，请确认 FastAPI 已启动。",
    });
  } finally {
    loading.value = false;
  }
}
</script>

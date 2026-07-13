<template>
  <main class="page">
    <div class="workspace">
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

      <aside class="history-panel">
        <header class="history-header">
          <div>
            <p class="eyebrow">History</p>
            <h2>最近问答</h2>
          </div>
          <span class="history-count">{{ histories.length }}/20</span>
        </header>

        <p v-if="historyError" class="history-error">{{ historyError }}</p>
        <p v-else-if="historyLoading" class="history-state">正在加载历史记录...</p>
        <p v-else-if="!histories.length" class="history-state">暂无历史记录</p>

        <div v-else class="history-list">
          <article v-for="history in histories" :key="history.id" class="history-card">
            <time class="history-time">{{ formatTime(history.created_at) }}</time>
            <h3>{{ history.question }}</h3>
            <p>{{ summarize(history.answer) }}</p>
            <span class="history-source-count">
              来源 {{ Array.isArray(history.sources) ? history.sources.length : 0 }} 条
            </span>
          </article>
        </div>
      </aside>
    </div>
  </main>
</template>

<script setup>
import { onMounted, ref } from "vue";

const API_URL = "http://localhost:8000/api/question";
const HISTORY_API_URL = "http://localhost:8000/api/question/history?limit=20";

const question = ref("");
const loading = ref(false);
const histories = ref([]);
const historyLoading = ref(false);
const historyError = ref("");
const messages = ref([
  {
    id: 1,
    role: "assistant",
    content: "你好，我可以帮助你梳理中小学历史知识点。",
  },
]);

function summarize(text) {
  if (!text) return "暂无回答内容";
  return text.length > 96 ? `${text.slice(0, 96)}...` : text;
}

function formatTime(value) {
  if (!value) return "时间未知";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "时间未知";

  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

async function loadHistories() {
  historyLoading.value = true;
  historyError.value = "";

  try {
    const response = await fetch(HISTORY_API_URL);
    if (!response.ok) {
      throw new Error("history request failed");
    }

    const data = await response.json();
    histories.value = Array.isArray(data.histories) ? data.histories : [];
  } catch (error) {
    historyError.value = "历史记录暂时无法加载，请确认后端服务已启动。";
  } finally {
    historyLoading.value = false;
  }
}

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
      sources: data.sources || [],
    });

    await loadHistories();
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

onMounted(() => {
  loadHistories();
});
</script>

<template>
  <main class="page">
    <div class="workspace">
      <section class="chat-panel">
        <header class="panel-header">
          <p class="eyebrow">HistoryAI · RAG + Voice</p>
          <h1>中小学历史知识问答</h1>
          <p class="header-note">支持文字提问，也可录音识别后修改再发送。</p>
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

            <span v-if="message.answerMode" class="mode-badge">
              {{ message.answerMode === "ai" ? "真实模型生成" : "模板 fallback" }}
            </span>
            <span v-if="message.historySaved === false" class="save-warning">
              回答已生成，但历史记录保存失败
            </span>

            <ul v-if="message.sources?.length" class="source-list">
              <li v-for="source in message.sources" :key="source.title">
                {{ source.title }} · {{ source.dynasty || "未标注朝代" }} · 分数 {{ source.score }}
              </li>
            </ul>

            <section v-if="message.outline" class="outline-card">
              <h3>基础知识梳理 · {{ message.outline.topic }}</h3>
              <dl>
                <div><dt>时间</dt><dd>{{ message.outline.time || "暂无" }}</dd></div>
                <div><dt>人物</dt><dd>{{ message.outline.people?.join("、") || "暂无" }}</dd></div>
                <div><dt>事件</dt><dd>{{ message.outline.event || "暂无" }}</dd></div>
                <div><dt>原因</dt><dd>{{ message.outline.reason || "暂无" }}</dd></div>
                <div><dt>内容/经过</dt><dd>{{ message.outline.process || "暂无" }}</dd></div>
                <div><dt>结果/影响</dt><dd>{{ message.outline.result_impact || "暂无" }}</dd></div>
                <div><dt>相关知识点</dt><dd>{{ message.outline.related_points?.join("、") || "暂无" }}</dd></div>
              </dl>
            </section>

            <audio
              v-if="message.audioUrl"
              class="answer-audio"
              :src="message.audioUrl"
              controls
              autoplay
            />
            <button
              v-else-if="message.role === 'assistant' && message.canSpeak"
              class="secondary-button speak-button"
              type="button"
              :disabled="message.ttsLoading"
              @click="synthesizeAnswer(message)"
            >
              {{ message.ttsLoading ? "正在生成语音..." : "朗读回答" }}
            </button>
            <small v-if="message.ttsError" class="inline-error">{{ message.ttsError }}</small>
          </div>
        </div>

        <form class="input-area" @submit.prevent="sendQuestion">
          <div class="voice-row">
            <button
              class="record-button"
              :class="{ recording }"
              type="button"
              :disabled="loading || asrLoading"
              @click="toggleRecording"
            >
              {{ recording ? "停止录音" : asrLoading ? "正在识别..." : "开始录音" }}
            </button>
            <span class="voice-status">{{ voiceStatus }}</span>
          </div>
          <div class="question-row">
            <textarea
              v-model="question"
              rows="2"
              placeholder="请输入历史问题，或录音识别后在这里修改文字"
            />
            <button type="submit" :disabled="loading || !question.trim()">
              {{ loading ? "发送中" : "发送" }}
            </button>
          </div>
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
import { onBeforeUnmount, onMounted, ref } from "vue";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";
const QUESTION_API_URL = `${API_BASE_URL}/question`;
const HISTORY_API_URL = `${API_BASE_URL}/question/history?limit=20`;
const ASR_API_URL = `${API_BASE_URL}/speech/asr`;
const TTS_API_URL = `${API_BASE_URL}/speech/tts`;

const question = ref("");
const loading = ref(false);
const histories = ref([]);
const historyLoading = ref(false);
const historyError = ref("");
const recording = ref(false);
const asrLoading = ref(false);
const voiceStatus = ref("点击录音后讲话，停止后会自动识别。");
const messages = ref([
  {
    id: 1,
    role: "assistant",
    content: "你好，我可以帮助你进行历史问答和结构化知识梳理。",
    canSpeak: false,
  },
]);

let mediaRecorder = null;
let mediaStream = null;
let audioChunks = [];

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

async function errorDetail(response, fallback) {
  try {
    const data = await response.json();
    return data.detail || fallback;
  } catch {
    return fallback;
  }
}

async function loadHistories() {
  historyLoading.value = true;
  historyError.value = "";
  try {
    const response = await fetch(HISTORY_API_URL);
    if (!response.ok) throw new Error("history request failed");
    const data = await response.json();
    histories.value = Array.isArray(data.histories) ? data.histories : [];
  } catch {
    historyError.value = "历史记录暂时无法加载，请确认后端和数据库服务已启动。";
  } finally {
    historyLoading.value = false;
  }
}

async function toggleRecording() {
  if (recording.value) {
    mediaRecorder?.stop();
    recording.value = false;
    voiceStatus.value = "录音已停止，正在上传识别...";
    return;
  }

  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    voiceStatus.value = "当前浏览器不支持录音，请继续使用文字提问。";
    return;
  }

  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];
    mediaRecorder = new MediaRecorder(mediaStream);
    mediaRecorder.addEventListener("dataavailable", (event) => {
      if (event.data.size > 0) audioChunks.push(event.data);
    });
    mediaRecorder.addEventListener("stop", uploadRecording, { once: true });
    mediaRecorder.start();
    recording.value = true;
    voiceStatus.value = "正在录音，请讲话；完成后点击“停止录音”。";
  } catch {
    voiceStatus.value = "无法使用麦克风，请检查浏览器权限。";
    stopMediaStream();
  }
}

function stopMediaStream() {
  mediaStream?.getTracks().forEach((track) => track.stop());
  mediaStream = null;
}

async function uploadRecording() {
  stopMediaStream();
  if (!audioChunks.length) {
    voiceStatus.value = "没有录到有效音频，请重试。";
    return;
  }

  asrLoading.value = true;
  const mimeType = mediaRecorder?.mimeType || "audio/webm";
  const extension = mimeType.includes("ogg") ? "ogg" : "webm";
  const blob = new Blob(audioChunks, { type: mimeType });
  const formData = new FormData();
  formData.append("audio", blob, `recording.${extension}`);

  try {
    const response = await fetch(ASR_API_URL, { method: "POST", body: formData });
    if (!response.ok) {
      throw new Error(await errorDetail(response, "语音识别失败"));
    }
    const data = await response.json();
    question.value = data.text || "";
    voiceStatus.value = "识别完成，可修改文字后发送。";
  } catch (error) {
    voiceStatus.value = error.message || "语音识别失败，请检查 ASR 配置。";
  } finally {
    asrLoading.value = false;
    audioChunks = [];
  }
}

async function synthesizeAnswer(message) {
  if (!message.content || message.ttsLoading) return;
  message.ttsLoading = true;
  message.ttsError = "";

  try {
    const response = await fetch(TTS_API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: message.content }),
    });
    if (!response.ok) {
      throw new Error(await errorDetail(response, "语音合成失败"));
    }
    const blob = await response.blob();
    message.audioUrl = URL.createObjectURL(blob);
  } catch (error) {
    message.ttsError = error.message || "语音合成失败，可继续阅读文字回答。";
  } finally {
    message.ttsLoading = false;
  }
}

async function sendQuestion() {
  const text = question.value.trim();
  if (!text) return;

  messages.value.push({ id: Date.now(), role: "user", content: text });
  question.value = "";
  loading.value = true;

  try {
    const response = await fetch(QUESTION_API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: text }),
    });
    if (!response.ok) {
      throw new Error(await errorDetail(response, "问答请求失败"));
    }

    const data = await response.json();
    const assistantMessage = {
      id: Date.now() + 1,
      role: "assistant",
      content: data.answer || "暂时没有生成回答。",
      sources: data.sources || [],
      outline: data.knowledge_outline || null,
      answerMode: data.answer_mode,
      historySaved: data.history_saved,
      canSpeak: true,
      ttsLoading: false,
      ttsError: "",
      audioUrl: "",
    };
    messages.value.push(assistantMessage);
    await Promise.all([loadHistories(), synthesizeAnswer(assistantMessage)]);
  } catch (error) {
    messages.value.push({
      id: Date.now() + 1,
      role: "assistant",
      content: error.message || "后端服务暂时无法访问，请确认 FastAPI 已启动。",
      canSpeak: false,
    });
  } finally {
    loading.value = false;
  }
}

onMounted(loadHistories);

onBeforeUnmount(() => {
  stopMediaStream();
  messages.value.forEach((message) => {
    if (message.audioUrl) URL.revokeObjectURL(message.audioUrl);
  });
});
</script>

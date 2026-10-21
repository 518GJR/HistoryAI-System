<template>
  <main class="page">
    <div class="workspace">
      <section class="chat-panel">
        <header class="panel-header">
          <div class="panel-heading">
            <p class="eyebrow">HistoryAI · RAG + Voice</p>
            <h1>中小学历史知识问答</h1>
            <p class="header-note">支持文字提问，也可录音识别后修改再发送。</p>
          </div>
          <button
            class="new-conversation-button"
            type="button"
            :disabled="newConversationDisabled"
            @click="newConversation"
          >
            新建对话
          </button>
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
              {{ answerModeLabel(message.answerMode) }}
            </span>
            <span v-if="message.historySaved === false" class="save-warning">
              回答已生成，但历史记录保存失败
            </span>

            <h4 v-if="message.sources?.length" class="evidence-heading">检索候选来源</h4>
            <ul v-if="message.sources?.length" class="source-list candidate-source-list">
              <li
                v-for="(source, index) in message.sources"
                :key="source.knowledge_id || `${source.title}-${index}`"
              >
                <strong>{{ source.title }}</strong>
                <span> · {{ source.dynasty || "未标注朝代" }} · 分数 {{ source.score }}</span>
                <small v-if="sourceLocation(source)" class="source-location">
                  {{ sourceLocation(source) }}
                </small>
                <small v-if="sourcePages(source)" class="source-pages">
                  {{ sourcePages(source) }}
                </small>
              </li>
            </ul>

            <section v-if="message.usedEvidence?.length" class="used-evidence">
              <h4 class="evidence-heading">实际采用证据</h4>
              <ol>
                <li
                  v-for="evidence in message.usedEvidence"
                  :key="evidence.historyKey || evidence.evidence_id"
                >
                  <strong>{{ evidence.source_titles?.join(" / ") || evidence.source_title }}</strong>
                  <p>{{ evidence.text }}</p>
                  <small>
                    知识点
                    {{ evidence.knowledge_ids?.join("、") || evidence.knowledge_id || "未标注" }}
                    · 原始来源
                    {{ evidence.source_ids?.join("、") || "未标注" }}
                  </small>
                  <small>{{ evidencePages(evidence) }}</small>
                </li>
              </ol>
            </section>

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
              ref="questionInput"
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
          <button
            v-for="history in histories"
            :key="history.id"
            class="history-card"
            type="button"
            :title="history.question"
            :aria-label="`查看历史问题：${history.question}`"
            :aria-current="selectedHistoryId === history.id ? 'true' : undefined"
            :class="{ active: selectedHistoryId === history.id }"
            @click="showHistory(history)"
          >
            <span class="history-question">{{ history.question }}</span>
          </button>
        </div>
      </aside>
    </div>
  </main>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";

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
const selectedHistoryId = ref(null);
const questionInput = ref(null);
const voiceStatus = ref("点击录音后讲话，停止后会自动识别。");
const messages = ref([
  {
    id: 1,
    role: "assistant",
    content: "你好，我可以帮助你进行历史问答和结构化知识梳理。",
    canSpeak: false,
  },
]);
const newConversationDisabled = computed(
  () =>
    loading.value ||
    recording.value ||
    asrLoading.value ||
    messages.value.some((message) => message.ttsLoading),
);

let mediaRecorder = null;
let mediaStream = null;
let audioChunks = [];

function sourceLocation(source) {
  const parts = [];
  if (source?.book_title) parts.push(source.book_title);
  if (source?.lesson_number || source?.lesson_title) {
    const number = source.lesson_number ? `第${source.lesson_number}课` : "";
    parts.push([number, source.lesson_title].filter(Boolean).join(" "));
  }
  if (source?.section_title) parts.push(source.section_title);
  return parts.join(" · ");
}

function sourcePages(source) {
  const parts = [];
  if (source?.textbook_pages) parts.push(`教材第${source.textbook_pages}页`);
  if (source?.pdf_pages) parts.push(`PDF页序${source.pdf_pages}`);
  return parts.join(" · ");
}

function evidencePages(evidence) {
  const parts = [];
  if (evidence?.textbook_pages) parts.push(`教材第${evidence.textbook_pages}页`);
  if (evidence?.pdf_pages) parts.push(`PDF页序${evidence.pdf_pages}`);
  return parts.join(" · ");
}

function answerModeLabel(mode) {
  return mode === "evidence_selection" || mode === "ai"
    ? "模型辅助的教材证据选择与原句组装"
    : "模板回退";
}

async function errorDetail(response, fallback) {
  try {
    const data = await response.json();
    return data.detail || fallback;
  } catch {
    return fallback;
  }
}

function isNetworkConnectionError(error) {
  return (
    error instanceof TypeError &&
    /failed to fetch|networkerror|network request failed|load failed/i.test(
      error.message || "",
    )
  );
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

function historyUsedEvidence(sources) {
  const seen = new Set();
  const evidenceItems = [];

  for (const source of Array.isArray(sources) ? sources : []) {
    for (const evidence of Array.isArray(source.used_evidence) ? source.used_evidence : []) {
      const key = [
        evidence.evidence_id,
        evidence.knowledge_id,
        evidence.source_ids?.join("|"),
        evidence.text,
      ].join("::");
      if (seen.has(key)) continue;
      seen.add(key);
      evidenceItems.push({ ...evidence, historyKey: key });
    }
  }

  return evidenceItems;
}

function revokeMessageAudio() {
  messages.value.forEach((message) => {
    if (message.audioUrl) URL.revokeObjectURL(message.audioUrl);
  });
}

function showHistory(history) {
  const sources = Array.isArray(history.sources) ? history.sources : [];
  revokeMessageAudio();
  selectedHistoryId.value = history.id;
  messages.value = [
    {
      id: `history-${history.id}-question`,
      role: "user",
      content: history.question,
    },
    {
      id: `history-${history.id}-answer`,
      role: "assistant",
      content: history.answer || "暂无回答内容",
      sources,
      usedEvidence: historyUsedEvidence(sources),
      canSpeak: false,
    },
  ];
}

async function newConversation() {
  if (newConversationDisabled.value) return;

  revokeMessageAudio();
  selectedHistoryId.value = null;
  question.value = "";
  voiceStatus.value = "点击录音后讲话，停止后会自动识别。";
  messages.value = [
    {
      id: Date.now(),
      role: "assistant",
      content: "你好，我可以帮助你进行历史问答和结构化知识梳理。",
      canSpeak: false,
    },
  ];

  await nextTick();
  questionInput.value?.focus();
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

  selectedHistoryId.value = null;
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
      usedEvidence: data.used_evidence || [],
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
    const networkConnectionFailed = isNetworkConnectionError(error);
    if (networkConnectionFailed && !question.value.trim()) {
      question.value = text;
    }
    messages.value.push({
      id: Date.now() + 1,
      role: "assistant",
      content: networkConnectionFailed
        ? "无法连接后端服务，请确认后端已启动后重试。"
        : error.message || "问答请求失败，请稍后重试。",
      canSpeak: false,
    });
  } finally {
    loading.value = false;
  }
}

onMounted(loadHistories);

onBeforeUnmount(() => {
  stopMediaStream();
  revokeMessageAudio();
});
</script>

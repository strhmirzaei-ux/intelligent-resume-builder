const form = document.querySelector("#chat-form");
const input = document.querySelector("#message-input");
const log = document.querySelector("#chat-log");
const sendButton = document.querySelector("#send-button");
const counter = document.querySelector("#input-counter");
const errorMessage = document.querySelector("#error-message");
const score = document.querySelector("#coverage-score");
const deficiencies = document.querySelector("#deficiencies");
const sessionLabel = document.querySelector("#session-id");
const newChat = document.querySelector("#new-chat");
const exportJson = document.querySelector("#export-json");
const exportPdf = document.querySelector("#export-pdf");
const exportDocx = document.querySelector("#export-docx");

let sessionId = localStorage.getItem("resume_session_id");

function toPersianDigits(value) {
  return String(value).replace(/\d/g, (digit) => "۰۱۲۳۴۵۶۷۸۹"[digit]);
}

function updateCounter() {
  counter.textContent = `${toPersianDigits(input.value.length)} / ۲۰۰۰۰`;
}

function addMessage(text, role) {
  const article = document.createElement("article");
  article.className = `message ${role}`;
  article.innerHTML = `
    <div class="avatar">${role === "user" ? "تو" : "AI"}</div>
    <div class="bubble"></div>
  `;
  article.querySelector(".bubble").textContent = text;
  log.appendChild(article);
  log.scrollTop = log.scrollHeight;
}

async function readApiResponse(response) {
  const text = await response.text();
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    return {
      detail: `Server returned HTTP ${response.status}: ${text.slice(0, 300)}`,
    };
  }
}

function updateInsights(data) {
  score.textContent = data.coverage_score == null
    ? "—"
    : `${toPersianDigits(Math.round(data.coverage_score))}%`;
  sessionId = data.session_id;
  localStorage.setItem("resume_session_id", sessionId);
  sessionLabel.textContent = sessionId;
  exportJson.disabled = false;
  exportPdf.disabled = false;
  exportDocx.disabled = false;
  deficiencies.replaceChildren();
  if (!data.deficiencies?.length) {
    const item = document.createElement("li");
    item.className = "empty-state";
    item.textContent = "اطلاعات اصلی کامل به نظر می‌رسد.";
    deficiencies.appendChild(item);
    return;
  }
  data.deficiencies.slice(0, 8).forEach((deficiency) => {
    const item = document.createElement("li");
    item.textContent = deficiency;
    deficiencies.appendChild(item);
  });
}

async function sendMessage(event) {
  event.preventDefault();
  const message = input.value.trim();
  if (!message || sendButton.disabled) return;
  addMessage(message, "user");
  input.value = "";
  updateCounter();
  errorMessage.textContent = "";
  sendButton.disabled = true;
  sendButton.firstChild.textContent = "در حال پردازش ";

  try {
    const response = await fetch("/api/v1/chat/message", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id: sessionId }),
    });
    const body = await readApiResponse(response);
    if (!response.ok) {
      throw new Error(body.detail || "ارتباط با سرویس پردازش برقرار نشد.");
    }
    updateInsights(body);
    addMessage(body.next_question || "اطلاعاتت ثبت شد. مورد دیگری هم هست که اضافه کنی؟", "assistant");
  } catch (error) {
    errorMessage.textContent = error.message;
    addMessage("متأسفانه پردازش پیام انجام نشد. تنظیمات سرویس هوش مصنوعی را بررسی کن.", "assistant");
  } finally {
    sendButton.disabled = false;
    sendButton.firstChild.textContent = "ارسال پیام ";
    input.focus();
  }
}

function resetChat() {
  localStorage.removeItem("resume_session_id");
  sessionId = null;
  exportJson.disabled = true;
  exportPdf.disabled = true;
  exportDocx.disabled = true;
  sessionLabel.textContent = "جلسه جدید";
  score.textContent = "—";
  deficiencies.innerHTML = '<li class="empty-state">هنوز تحلیلی انجام نشده است.</li>';
  log.innerHTML = `
    <article class="message assistant">
      <div class="avatar">AI</div>
      <div class="bubble">سلام! برای شروع، هر چیزی درباره‌ی سابقه‌ی کاری، تحصیلات یا مهارت‌هایت می‌دانی همین‌جا بنویس.</div>
    </article>
  `;
  errorMessage.textContent = "";
  input.focus();
}

async function downloadResumeJson() {
  if (!sessionId) return;
  errorMessage.textContent = "";
  try {
    const response = await fetch(`/api/v1/resumes/${encodeURIComponent(sessionId)}/json`);
    const body = await readApiResponse(response);
    if (!response.ok) throw new Error(body.detail || "دریافت رزومه انجام نشد.");
    const blob = new Blob([JSON.stringify(body.resume, null, 2)], {
      type: "application/json;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "resume.json";
    document.body.appendChild(link);
    link.click();
    setTimeout(() => {
      URL.revokeObjectURL(url);
      link.remove();
    }, 1000);
  } catch (error) {
    errorMessage.textContent = error.message;
  }
}

async function downloadResumeFile(extension) {
  if (!sessionId) return;
  errorMessage.textContent = "";
  try {
    const response = await fetch(
      `/api/v1/resumes/${encodeURIComponent(sessionId)}/${extension}?fresh=${Date.now()}`,
      { cache: "no-store" },
    );
    if (!response.ok) {
      const body = await readApiResponse(response);
      throw new Error(body.detail || "دریافت فایل رزومه انجام نشد.");
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `resume-${sessionId}-latest.${extension}`;
    document.body.appendChild(link);
    link.click();
    setTimeout(() => {
      URL.revokeObjectURL(url);
      link.remove();
    }, 1000);
  } catch (error) {
    errorMessage.textContent = error.message;
  }
}

form.addEventListener("submit", sendMessage);
input.addEventListener("input", updateCounter);
newChat.addEventListener("click", resetChat);
exportJson.addEventListener("click", downloadResumeJson);
exportPdf.addEventListener("click", () => downloadResumeFile("pdf"));
exportDocx.addEventListener("click", () => downloadResumeFile("docx"));
updateCounter();
async function restoreSession() {
  if (!sessionId) return;
  try {
    const response = await fetch(
      `/api/v1/resumes/${encodeURIComponent(sessionId)}?fresh=${Date.now()}`,
      { cache: "no-store" },
    );
    if (!response.ok) throw new Error("session not found");
    sessionLabel.textContent = sessionId;
    exportJson.disabled = false;
    exportPdf.disabled = false;
    exportDocx.disabled = false;
  } catch {
    localStorage.removeItem("resume_session_id");
    sessionId = null;
    sessionLabel.textContent = "جلسه جدید";
    exportJson.disabled = true;
    exportPdf.disabled = true;
    exportDocx.disabled = true;
  }
}

restoreSession();

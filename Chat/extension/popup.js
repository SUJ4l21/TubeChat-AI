document.addEventListener("DOMContentLoaded", async () => {
  const chatBox = document.getElementById("chat-box");
  const userInput = document.getElementById("user-input");
  const sendBtn = document.getElementById("send-btn");

  // 1. Get the current active tab's URL to extract the video ID
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const url = new URL(tab.url);
  const videoId = url.searchParams.get("v");

  if (!videoId) {
    // UPDATED: Using system-alert class instead of red text
    chatBox.innerHTML =
      "<p class='system-alert'>Please open a YouTube video page first!</p>";
    userInput.disabled = true;
    sendBtn.disabled = true;
    return;
  }

  // 2. Lock the chat controls and show a loading indicator while FAISS indexes
  userInput.disabled = true;
  sendBtn.disabled = true;
  // UPDATED: Using system-alert class
  chatBox.innerHTML =
    "<p id='status-msg' class='system-alert'>Reading video transcript and building AI index... Please wait.</p>";

  try {
    const initResponse = await fetch("http://127.0.0.1:5000/initialize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ video_id: videoId }),
    });

    if (!initResponse.ok) {
      const errorData = await initResponse.json();
      throw new Error(errorData.detail || "Failed to initialize video.");
    }

    // Unlocking interface when backend is fully indexed
    const statusMsg = document.getElementById("status-msg");
    if (statusMsg) statusMsg.remove();
    // UPDATED: Clean, subtle success message matching the dark theme
    chatBox.innerHTML +=
      "<p class='system-alert' style='border-color: var(--border-strong); color: var(--text-primary);'>✨ Connected! Ask me anything about this video.</p>";
    userInput.disabled = false;
    sendBtn.disabled = false;
    userInput.focus();
  } catch (error) {
    // UPDATED: Clean error alert
    chatBox.innerHTML = `<p class='system-alert'>Error: ${error.message}</p>`;
    return;
  }

  // 3. Helper function to process and send messages
  async function handleSendMessage() {
    const question = userInput.value.trim();
    if (!question || userInput.disabled) return;

    // UPDATED: Removed "You:" prefix and added user-msg-style class
    chatBox.innerHTML += `<p class='user-msg-style'>${question}</p>`;
    userInput.value = "";
    chatBox.scrollTop = chatBox.scrollHeight;

    // Show a small thinking indicator matching the dark UI text colors
    const thinkingId = "thinking-" + Date.now();
    chatBox.innerHTML += `<p id="${thinkingId}" style="color: var(--text-secondary); font-style: italic; font-size: 0.8rem; padding: 4px 14px; background: transparent; border: none;">TubeChat is thinking...</p>`;
    chatBox.scrollTop = chatBox.scrollHeight;

    try {
      const response = await fetch("http://127.0.0.1:5000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_id: videoId, question: question }),
      });

      // Remove the thinking indicator
      const thinkingElem = document.getElementById(thinkingId);
      if (thinkingElem) thinkingElem.remove();

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Server error during generation.");
      }

      const data = await response.json();
      // UPDATED: Removed "AI:" prefix since the left-aligned bubble makes it obvious
      chatBox.innerHTML += `<p>${data.answer}</p>`;
    } catch (error) {
      const thinkingElem = document.getElementById(thinkingId);
      if (thinkingElem) thinkingElem.remove();
      // UPDATED: Clean error alert
      chatBox.innerHTML += `<p class='system-alert'>Error: ${error.message}</p>`;
    }

    chatBox.scrollTop = chatBox.scrollHeight;
  }

  // 4. Attach events for click and enter key bindings
  sendBtn.addEventListener("click", handleSendMessage);

  userInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      handleSendMessage();
    }
  });
});

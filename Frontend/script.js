const pdfPathInput = document.getElementById("pdf-path-input");
const indexButton = document.getElementById("index-button");
const indexStatus = document.getElementById("index-status");
const documentSelect = document.getElementById("document-select");

const inputbar = document.getElementById("user-input");
const but = document.getElementById("send-button");
const output = document.getElementById("chat-window");

// ---------- Load the list of already-indexed documents into the dropdown ----------

async function loadDocuments() {
  try {
    const response = await fetch("http://127.0.0.1:5000/documents");
    const data = await response.json();

    documentSelect.innerHTML = "";

    if (data.length === 0) {
      documentSelect.innerHTML = `<option value="">No documents indexed yet</option>`;
      return;
    }

    for (const name of data) {
      const option = document.createElement("option");
      option.value = name;
      option.textContent = name.replace("doc_", "");
      documentSelect.appendChild(option);
    }

  } catch (error) {
    console.log("Error loading documents:", error);
  }
}

loadDocuments();

// ---------- Index a new PDF ----------

indexButton.addEventListener("click", async function () {
  const pdfPath = pdfPathInput.value.trim();

  if (!pdfPath) return;

  indexStatus.textContent = "Indexing... this may take a while for large PDFs.";

  try {
    const response = await fetch("http://127.0.0.1:5000/index", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pdf_path: pdfPath })
    });

    const data = await response.json();
    indexStatus.textContent = data.message || data.error;

    // Refresh the dropdown so the newly indexed document shows up
    loadDocuments();

  } catch (error) {
    indexStatus.textContent = "Something went wrong while indexing.";
    console.log("Error:", error);
  }
});

// ---------- Ask a question about the selected document ----------

but.addEventListener("click", async function () {
  const question = inputbar.value.trim();
  const selectedDocument = documentSelect.value;

  if (!question) return;

  if (!selectedDocument) {
    alert("Please select a document first.");
    return;
  }

  const userBubble = document.createElement("div");
  userBubble.classList.add("message", "user");
  userBubble.textContent = question;
  output.appendChild(userBubble);

  inputbar.value = "";

  const bubble = document.createElement("div");
  bubble.classList.add("message", "loading");
  bubble.textContent = "Searching the document ...";
  output.appendChild(bubble);

  output.scrollTop = output.scrollHeight;

  try {
    const response = await fetch("http://127.0.0.1:5000/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: question, collection_name: selectedDocument })
    });

    const data = await response.json();

    const reply = document.createElement("div");
    reply.classList.add("message", "bot");
    reply.textContent = data.reply || data.error;

    bubble.remove();
    output.appendChild(reply);

  } catch (error) {
    bubble.remove();
    console.log("Error:", error);
  }

  output.scrollTop = output.scrollHeight;
});
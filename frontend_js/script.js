// script.js - Phiên bản RAG tinh gọn (Chỉ trích dẫn 1 thẻ File)

const fileInput = document.getElementById('pdf-upload');
const chatInput = document.getElementById('chat-input');
const chatForm = document.getElementById('chat-form');
const messagesArea = document.getElementById('messages-area');
const sendButton = document.getElementById('send-button');
const fileStatus = document.getElementById('file-status');
const footerMessage = document.getElementById('footer-message');
const chatEnd = document.getElementById('chat-end');
const welcomeMessage = document.getElementById('welcome-message');

let uploadedFile = null;
let isLoading = false;
const API_BASE_URL = 'http://127.0.0.1:8000';

// --- HÀM XỬ LÝ MARKDOWN ---
const formatMarkdown = (text, isBot) => {
    let html = text;
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    if (isBot) {
        html = html.replace(/^\*\s*/gm, '<li>').replace(/^-/gm, '<li>');
        if (html.includes('<li>')) {
            html = `<ul class="list-disc list-inside ml-4 mt-1">${html}</ul>`;
        }
    }
    html = html.replace(/\n/g, '<br>');
    return html;
};

// --- HÀM RENDER TIN NHẮN ---
function renderMessage(message) {
    if (welcomeMessage) welcomeMessage.style.display = 'none';

    const isUser = message.sender === 'user';
    const messageWrapper = document.createElement('div');
    messageWrapper.className = `flex w-full ${isUser ? 'justify-end' : 'justify-start'} animate-fade-in mb-4`;

    const contentBlock = document.createElement('div');
    contentBlock.className = `flex items-start ${isUser ? 'ml-auto mr-0' : 'mx-auto'}`;

    const iconDiv = document.createElement('div');
    const iconClass = isUser ? 'bg-gray-700 text-white' : 'bg-blue-500 text-white';
    iconDiv.className = `p-2 rounded-full ${iconClass} ${isUser ? 'order-2 ml-4' : 'order-1 mr-4'} mt-1 flex-shrink-0`;
    iconDiv.innerHTML = isUser
        ? '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>'
        : '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2" ry="2"></rect><path d="M9 18h6M9 6h6M12 9v6"></path></svg>';

    const textBlock = document.createElement('div');
    textBlock.className = `flex flex-col flex-1 p-0 ${isUser ? 'order-1 text-right' : 'order-2 text-left'}`;

    const senderName = document.createElement('p');
    senderName.className = 'font-semibold mb-1 text-sm text-gray-600';
    senderName.textContent = isUser ? 'Đan Dương' : 'Alvin AI Assistant';

    const textContent = document.createElement('div');
    const bubbleClass = isUser
        ? 'bg-blue-500 text-white rounded-t-xl rounded-bl-xl shadow-md inline-block max-w-lg'
        : 'bg-gray-100 text-gray-800 rounded-t-xl rounded-br-xl shadow-sm inline-block max-w-lg border border-gray-200';

    textContent.className = `text-base ${bubbleClass} p-3 whitespace-pre-wrap leading-relaxed`;
    textContent.innerHTML = formatMarkdown(message.text, !isUser);

    textBlock.appendChild(senderName);
    textBlock.appendChild(textContent);

    // --- XỬ LÝ HIỂN THỊ NGUỒN DUY NHẤT ---
    if (!isUser && message.sources && message.sources.length > 0) {
        // Lấy danh sách tên file duy nhất (không trùng lặp)
        const uniqueFiles = [...new Set(message.sources.map(src => src.file_name))];

        const sourcesDiv = document.createElement('div');
        sourcesDiv.className = `mt-3 pt-3 border-t border-gray-200 text-left`;
        sourcesDiv.innerHTML = `
        <h4 class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2">🔍 Nguồn tài liệu:</h4>
        <div class="flex flex-wrap gap-2 justify-start">
            ${uniqueFiles.map(fileName =>
            `<span class="px-2 py-1 text-[11px] bg-blue-50 text-blue-700 rounded-md border border-blue-100 shadow-sm font-medium">
                    📍 ${fileName}
                </span>`
        ).join('')}
        </div>`;
        textBlock.appendChild(sourcesDiv);
    }

    contentBlock.appendChild(iconDiv);
    contentBlock.appendChild(textBlock);
    messageWrapper.appendChild(contentBlock);
    messagesArea.appendChild(messageWrapper);
    chatEnd.scrollIntoView({ behavior: 'smooth', block: 'end' });
}

// --- CẬP NHẬT UI ---
function updateUI() {
    const isSendDisabled = !uploadedFile || isLoading || !chatInput.value.trim();
    sendButton.disabled = isSendDisabled;

    if (isSendDisabled) {
        sendButton.classList.replace('bg-blue-500', 'bg-gray-300');
        sendButton.classList.replace('text-white', 'text-gray-500');
    } else {
        sendButton.classList.replace('bg-gray-300', 'bg-blue-500');
        sendButton.classList.replace('text-gray-500', 'text-white');
    }

    chatInput.disabled = !uploadedFile || isLoading;
    chatInput.placeholder = uploadedFile ? 'Hỏi bất cứ điều gì về tài liệu...' : 'Vui lòng tải file để bắt đầu';

    if (uploadedFile) {
        footerMessage.innerHTML = `Đang chat với: <strong>${uploadedFile.name}</strong>`;
        fileStatus.innerHTML = `<span class="flex items-center text-sm text-green-600 bg-green-50 px-3 py-1 rounded-full border border-green-200">
            <span class="w-2 h-2 bg-green-500 rounded-full animate-pulse mr-2"></span>
            <strong>${uploadedFile.name}</strong>
        </span>`;
    }
}

// --- XỬ LÝ SỰ KIỆN TẢI FILE ---
fileInput.addEventListener('change', async (e) => {
    const file = e.target.files?.[0];
    if (!file || isLoading) return;

    isLoading = true;
    updateUI();
    messagesArea.innerHTML = '';

    const formData = new FormData();
    formData.append('file', file);

    try {
        renderMessage({ sender: 'bot', text: `⏳ Đang xử lý tệp: **${file.name}**...` });

        const response = await fetch(`${API_BASE_URL}/pdf/upload`, {
            method: 'POST',
            body: formData,
        });

        const data = await response.json();

        if (response.ok) {
            uploadedFile = {
                id: data.data.pdf_collection_id || data.data.collection_id,
                name: data.data.file_name,
            };
            messagesArea.innerHTML = '';
            renderMessage({
                sender: 'bot',
                text: `✅ Đã tải file **${uploadedFile.name}** thành công! Bạn muốn tìm hiểu gì trong tài liệu này?`
            });
        } else {
            throw new Error(data.detail || 'Lỗi xử lý file.');
        }
    } catch (error) {
        messagesArea.innerHTML = '';
        renderMessage({ sender: 'bot', text: `❌ Lỗi: ${error.message}` });
        uploadedFile = null;
    } finally {
        isLoading = false;
        e.target.value = '';
        updateUI();
    }
});

// --- XỬ LÝ GỬI TIN NHẮN ---
chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const input = chatInput.value.trim();
    if (!input || isLoading || !uploadedFile || !uploadedFile.id) return;

    renderMessage({ sender: 'user', text: input });
    chatInput.value = '';
    isLoading = true;
    updateUI();

    try {
        const response = await fetch(`${API_BASE_URL}/chat/ask`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                question: input,
                pdf_collection_id: uploadedFile.id,
                top_k: 5 // Tăng Top K để AI có nhiều dữ liệu tham khảo hơn
            }),
        });

        const data = await response.json();

        if (response.ok) {
            renderMessage({
                sender: 'bot',
                text: data.answer,
                sources: data.sources.map(src => ({
                    file_name: src.file_name
                })),
            });
        } else {
            console.error("Lỗi Server:", data);
            throw new Error(data.detail || 'Lỗi phản hồi.');
        }
    } catch (error) {
        renderMessage({
            sender: 'bot',
            text: `❌ Đã có lỗi xảy ra: ${error.message}`
        });
    } finally {
        isLoading = false;
        updateUI();
    }
});

chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !sendButton.disabled) {
        e.preventDefault();
        chatForm.dispatchEvent(new Event('submit'));
    }
});

chatInput.addEventListener('input', updateUI);
document.addEventListener('DOMContentLoaded', updateUI);
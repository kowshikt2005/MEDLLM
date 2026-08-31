const API_BASE = '/api';

function getToken() {
  return localStorage.getItem('medllm_token');
}

function setToken(token) {
  localStorage.setItem('medllm_token', token);
}

function removeToken() {
  localStorage.removeItem('medllm_token');
}

function getUser() {
  const user = localStorage.getItem('medllm_user');
  return user ? JSON.parse(user) : null;
}

function setUser(user) {
  localStorage.setItem('medllm_user', JSON.stringify(user));
}

function removeUser() {
  localStorage.removeItem('medllm_user');
}

function authHeaders() {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json' };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

async function handleResponse(response) {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

async function signup(email, password, fullName, phoneNumber = null) {
  const response = await fetch(`${API_BASE}/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email,
      password,
      full_name: fullName,
      phone_number: phoneNumber,
    }),
  });

  const data = await handleResponse(response);
  setToken(data.access_token);
  setUser(data.user);
  return data;
}

async function login(email, password) {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  const data = await handleResponse(response);
  setToken(data.access_token);
  setUser(data.user);
  return data;
}

function logout() {
  removeToken();
  removeUser();
}

function isLoggedIn() {
  return !!getToken();
}

async function chatStream(message, options = {}) {
  const {
    conversationId = null,
    mode = 'normal',
    model = null,
    attachments = [],
    healthContext = false,
    onRequest = () => {},
    onToken = () => {},
    onStep = () => {},
    onDone = () => {},
    onError = () => {},
  } = options;

  try {
    const response = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
        attachments,
        health_context: healthContext,
        mode,
        model,
      }),
    });

    if (!response.ok) {
      const error = await response.text();
      onError(error);
      return { conversationId: null, fullResponse: '', requestId: null, cancelled: false };
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullResponse = '';
    let resultConversationId = conversationId;
    let requestId = null;
    let cancelled = false;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const text = decoder.decode(value, { stream: true });
      const lines = text.split('\n');

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;

        try {
          const data = JSON.parse(line.slice(6));

          if (data.type === 'init') {
            requestId = data.request_id || null;
            onRequest(requestId);
          } else if (data.type === 'token') {
            fullResponse += data.content;
            onToken(data.content);
          } else if (data.type === 'step') {
            onStep(data.content);
          } else if (data.type === 'cancelled') {
            cancelled = true;
          } else if (data.type === 'done') {
            resultConversationId = data.conversation_id;
            requestId = data.request_id || requestId;
            onDone({
              conversationId: data.conversation_id,
              fullResponse,
              sources: data.sources || [],
              requestId,
              cancelled,
            });
          }
        } catch {
          // Ignore partial/malformed chunks.
        }
      }
    }

    return { conversationId: resultConversationId, fullResponse, requestId, cancelled };
  } catch (error) {
    onError(error.message);
    return { conversationId: null, fullResponse: '', requestId: null, cancelled: false };
  }
}

async function getRuntime() {
  const response = await fetch(`${API_BASE}/runtime`, {
    method: "GET",
    headers: authHeaders(),
  });
  return handleResponse(response);
}

async function cancelRequest(requestId) {
  if (!requestId) return { cancelled: false };

  try {
    const response = await fetch(`${API_BASE}/cancel?request_id=${encodeURIComponent(requestId)}`, {
      method: 'POST',
      headers: authHeaders(),
    });
    return handleResponse(response);
  } catch (error) {
    console.error('Cancel request failed:', error);
    return { cancelled: false };
  }
}

async function uploadFile(file) {
  const formData = new FormData();
  formData.append('file', file);

  const token = getToken();
  const headers = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    headers,
    body: formData,
  });

  return handleResponse(response);
}

async function transcribeAudio(audioBlob) {
  const formData = new FormData();
  formData.append('file', audioBlob, 'recording.webm');

  const token = getToken();
  const headers = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}/transcribe`, {
    method: 'POST',
    headers,
    body: formData,
  });

  return handleResponse(response);
}

async function healthCheck() {
  const response = await fetch(`${API_BASE}/health`);
  return handleResponse(response);
}

async function listConversations() {
  const response = await fetch(`${API_BASE}/conversations`, {
    method: 'GET',
    headers: authHeaders(),
  });
  return handleResponse(response);
}

async function getConversation(conversationId) {
  const response = await fetch(`${API_BASE}/conversations/${encodeURIComponent(conversationId)}`, {
    method: 'GET',
    headers: authHeaders(),
  });
  return handleResponse(response);
}

async function getProfile() {
  const response = await fetch(`${API_BASE}/profile`, {
    method: 'GET',
    headers: authHeaders(),
  });
  return handleResponse(response);
}

async function updateProfile(profilePayload) {
  const response = await fetch(`${API_BASE}/profile`, {
    method: 'PUT',
    headers: authHeaders(),
    body: JSON.stringify(profilePayload),
  });
  return handleResponse(response);
}

export const api = {
  signup,
  login,
  logout,
  isLoggedIn,
  getUser,
  getToken,
  chatStream,
  getRuntime,
  cancelRequest,
  uploadFile,
  transcribeAudio,
  healthCheck,
  listConversations,
  getConversation,
  getProfile,
  updateProfile,
};

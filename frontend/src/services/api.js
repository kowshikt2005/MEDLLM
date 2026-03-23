/**
 * Centralized API client for communicating with the FastAPI backend.
 *
 * WHY THIS FILE EXISTS:
 * Instead of every component writing its own fetch() calls with URLs,
 * headers, and error handling, they all import from here:
 *
 *   import { api } from '../services/api';
 *   const result = await api.login(email, password);
 *
 * This keeps API logic in one place. If the backend URL changes,
 * you change it here — not in 10 different components.
 *
 * HOW THE AUTH TOKEN WORKS:
 * After login/signup, we store the JWT token in localStorage.
 * Every subsequent request includes it in the Authorization header.
 * The backend reads this header to identify the user.
 */

// In development, Vite's proxy forwards /api to the backend.
// In production, this would be the actual backend URL.
const API_BASE = '/api';

// ── Token management ───────────────────────────────────

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

// ── Helper: build headers with auth token ──────────────

function authHeaders() {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

// ── Helper: handle response errors ─────────────────────

async function handleResponse(response) {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

// ═══════════════════════════════════════════════════════
// AUTH API
// ═══════════════════════════════════════════════════════

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

  // Store token and user info for future requests
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

  // Store token and user info
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

// ═══════════════════════════════════════════════════════
// CHAT API (Streaming)
// ═══════════════════════════════════════════════════════

/**
 * Send a chat message and get a streaming response.
 *
 * HOW STREAMING WORKS ON THE FRONTEND:
 * 1. We send a POST request to /api/chat
 * 2. The response is a STREAM (not a single JSON blob)
 * 3. We read it chunk by chunk using response.body.getReader()
 * 4. Each chunk contains one or more SSE events
 * 5. We parse each event and call onToken() for each token
 *
 * @param {string} message - The user's message
 * @param {object} options - Optional: conversationId, mode, onToken callback
 * @returns {Promise<object>} - { conversationId, fullResponse }
 */
async function chatStream(message, options = {}) {
  const {
    conversationId = null,
    mode = 'normal',
    attachments = [],
    healthContext = false,
    onToken = () => {},     // Called for each token: onToken("Diabetes")
    onStep = () => {},      // Called for reasoning steps (Phase 4)
    onDone = () => {},      // Called when stream completes
    onError = () => {},     // Called on error
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
      }),
    });

    if (!response.ok) {
      const error = await response.text();
      onError(error);
      return { conversationId: null, fullResponse: '' };
    }

    // Read the SSE stream
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullResponse = '';
    let resultConversationId = conversationId;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      // Decode the chunk (may contain multiple SSE events)
      const text = decoder.decode(value, { stream: true });

      // SSE format: each event starts with "data: " and ends with "\n\n"
      const lines = text.split('\n');

      for (const line of lines) {
        // SSE lines starting with "data: " contain our JSON
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6)); // Remove "data: " prefix

            if (data.type === 'token') {
              fullResponse += data.content;
              onToken(data.content);
            } else if (data.type === 'step') {
              onStep(data.content);
            } else if (data.type === 'done') {
              resultConversationId = data.conversation_id;
              onDone({ conversationId: data.conversation_id, fullResponse });
            }
          } catch {
            // Skip malformed JSON (can happen with partial chunks)
          }
        }
      }
    }

    return { conversationId: resultConversationId, fullResponse };
  } catch (error) {
    onError(error.message);
    return { conversationId: null, fullResponse: '' };
  }
}

// ═══════════════════════════════════════════════════════
// HEALTH CHECK
// ═══════════════════════════════════════════════════════

async function healthCheck() {
  const response = await fetch(`${API_BASE}/health`);
  return handleResponse(response);
}

// ═══════════════════════════════════════════════════════
// EXPORT
// ═══════════════════════════════════════════════════════

export const api = {
  // Auth
  signup,
  login,
  logout,
  isLoggedIn,
  getUser,
  getToken,

  // Chat
  chatStream,

  // System
  healthCheck,
};

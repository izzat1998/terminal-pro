<script setup lang="ts">
import { ref } from 'vue';

interface ApiEndpoint {
  method: string;
  path: string;
  description: string;
}

const endpoints: ApiEndpoint[] = [
  { method: 'GET', path: '/api/v1/containers/', description: 'List all containers with filtering' },
  { method: 'GET', path: '/api/v1/containers/{id}/', description: 'Get container details' },
  { method: 'POST', path: '/api/v1/entries/', description: 'Register vehicle entry' },
  { method: 'POST', path: '/api/v1/exits/', description: 'Register vehicle exit' },
  { method: 'GET', path: '/api/v1/yard/layout/', description: 'Get yard visualization data' },
  { method: 'POST', path: '/api/v1/orders/pre-match/', description: 'Pre-order matching' },
];

const activeEndpoint = ref<number | null>(0);
</script>

<template>
  <div class="api-section">
    <div class="api-header">
      <div class="api-badge">REST API</div>
      <h2 class="api-title">Developer-First Architecture</h2>
      <p class="api-description">
        Build custom integrations with our comprehensive REST API.
        Webhook support for real-time event notifications.
      </p>
    </div>

    <div class="api-content">
      <div class="endpoints-list">
        <div
          v-for="(endpoint, index) in endpoints"
          :key="index"
          class="endpoint-item"
          :class="{ active: activeEndpoint === index }"
          @click="activeEndpoint = activeEndpoint === index ? null : index"
        >
          <div class="endpoint-header">
            <span class="method" :class="endpoint.method.toLowerCase()">
              {{ endpoint.method }}
            </span>
            <code class="path">{{ endpoint.path }}</code>
            <svg
              class="chevron"
              :class="{ expanded: activeEndpoint === index }"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <path d="M6 9l6 6 6-6" />
            </svg>
          </div>
          <div v-if="activeEndpoint === index" class="endpoint-details">
            <p>{{ endpoint.description }}</p>
            <div class="response-example">
              <div class="example-label">Response</div>
              <pre><code>{
  "success": true,
  "data": {
    "id": 12345,
    "status": "ACTIVE"
  }
}</code></pre>
            </div>
          </div>
        </div>
      </div>

      <div class="code-highlight">
        <div class="code-header">
          <span>cURL Example</span>
          <button class="copy-btn">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="9" y="9" width="13" height="13" rx="2" />
              <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
            </svg>
          </button>
        </div>
        <pre class="code-block"><code>curl -X GET "https://api.mtt.uz/v1/containers/" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json"</code></pre>
      </div>
    </div>
  </div>
</template>

<style scoped>
.api-section {
  padding: 60px 0;
}

.api-header {
  text-align: center;
  margin-bottom: 48px;
}

.api-badge {
  display: inline-block;
  padding: 6px 16px;
  background: rgba(233, 69, 96, 0.1);
  color: #e94560;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 16px;
}

.api-title {
  font-size: 36px;
  font-weight: 700;
  color: #1f2937;
  margin: 0 0 16px 0;
}

.api-description {
  font-size: 18px;
  color: #6b7280;
  max-width: 600px;
  margin: 0 auto;
}

.api-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 32px;
  max-width: 1100px;
  margin: 0 auto;
}

.endpoints-list {
  background: white;
  border-radius: 16px;
  border: 1px solid #e5e7eb;
  overflow: hidden;
}

.endpoint-item {
  border-bottom: 1px solid #e5e7eb;
  transition: background 0.2s ease;
}

.endpoint-item:last-child {
  border-bottom: none;
}

.endpoint-item:hover {
  background: #f9fafb;
}

.endpoint-item.active {
  background: #fef2f2;
}

.endpoint-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  cursor: pointer;
}

.method {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;
  font-family: monospace;
}

.method.get {
  background: #dcfce7;
  color: #166534;
}

.method.post {
  background: #dbeafe;
  color: #1d4ed8;
}

.method.put {
  background: #fef3c7;
  color: #92400e;
}

.method.delete {
  background: #fee2e2;
  color: #dc2626;
}

.path {
  flex: 1;
  font-size: 13px;
  color: #374151;
}

.chevron {
  color: #9ca3af;
  transition: transform 0.2s ease;
}

.chevron.expanded {
  transform: rotate(180deg);
}

.endpoint-details {
  padding: 0 20px 20px 20px;
  animation: slideDown 0.2s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.endpoint-details p {
  font-size: 14px;
  color: #6b7280;
  margin: 0 0 16px 0;
}

.response-example {
  background: #1f2937;
  border-radius: 8px;
  padding: 16px;
  font-size: 13px;
}

.example-label {
  color: #9ca3af;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 8px;
}

.response-example pre {
  margin: 0;
  color: #e5e7eb;
  overflow-x: auto;
}

.code-highlight {
  background: #1f2937;
  border-radius: 16px;
  overflow: hidden;
}

.code-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.05);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.code-header span {
  font-size: 14px;
  color: #9ca3af;
}

.copy-btn {
  background: transparent;
  border: none;
  color: #9ca3af;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.copy-btn:hover {
  color: white;
  background: rgba(255, 255, 255, 0.1);
}

.code-block {
  padding: 20px;
  margin: 0;
  font-size: 14px;
  color: #e5e7eb;
  overflow-x: auto;
  line-height: 1.6;
}

@media (max-width: 900px) {
  .api-content {
    grid-template-columns: 1fr;
  }
}
</style>

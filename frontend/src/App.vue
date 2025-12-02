<template>
  <div class="flex h-screen overflow-hidden">
    <!-- Left Sidebar - Chat List -->
    <Sidebar>
      <ChatList />
    </Sidebar>

    <!-- Main Content Area -->
    <div class="flex-1 flex flex-col">
      <!-- Top Navigation -->
      <div class="bg-gray-900 border-b border-gray-700 px-4 py-3">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-4">
            <div class="px-4 py-2 rounded bg-blue-600 text-white">
              Chat
            </div>
          </div>

          <div class="text-gray-400 text-sm">
            AI Chat Application
          </div>
        </div>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-hidden">
        <ChatWindow />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import Sidebar from '@/components/common/Sidebar.vue'
import ChatList from '@/components/chat/ChatList.vue'
import ChatWindow from '@/components/chat/ChatWindow.vue'
</script>

<template>
  <aside class="w-64 bg-gray-900 text-white flex flex-col h-screen">
    <div class="p-4 border-b border-gray-700">
      <h1 class="text-xl font-bold">AI Chat</h1>
    </div>

    <div class="flex-1 overflow-y-auto">
      <slot />
    </div>

    <div class="p-4 border-t border-gray-700">
      <slot name="footer" />
    </div>
  </aside>
</template>

<script setup lang="ts">
</script>

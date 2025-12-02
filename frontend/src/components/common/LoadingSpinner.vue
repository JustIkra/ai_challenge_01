<template>
  <div class="flex items-center justify-center" :class="sizeClass">
    <div
      class="animate-spin rounded-full border-b-2"
      :class="[borderClass, sizeClass]"
    ></div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  size?: 'sm' | 'md' | 'lg'
  color?: string
}

const props = withDefaults(defineProps<Props>(), {
  size: 'md',
  color: 'border-blue-500'
})

const sizeClass = computed(() => {
  const sizes = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12'
  }
  return sizes[props.size]
})

const borderClass = computed(() => props.color)
</script>

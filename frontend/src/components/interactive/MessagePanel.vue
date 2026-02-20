<template>
  <div class="messages-container bg-white rounded-lg shadow-sm p-4">
    <div class="flex items-center justify-between mb-3">
      <h4 class="font-medium">实时消息</h4>
      <Button variant="ghost" size="sm" @click="$emit('clear')">
        <Trash2 class="w-4 h-4" />
      </Button>
    </div>

    <div class="messages-list space-y-2 max-h-60 overflow-y-auto">
      <div
        v-for="message in messages"
        :key="message.timestamp"
        class="message-item p-2 rounded text-sm"
        :class="[
          'bg-gray-50',
          { 'bg-blue-50': message.type === 'info' },
          { 'bg-green-50': message.type === 'success' },
          { 'bg-red-50': message.type === 'error' },
          { 'bg-yellow-50': message.type === 'warning' }
        ]"
      >
        <span class="text-gray-600">{{ formatTime(message.timestamp) }}</span>
        <p class="mt-1">{{ message.content }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { Trash2 } from "lucide-vue-next";

defineProps<{
	messages: Array<{ timestamp: string; content: string; type: string }>;
}>();

defineEmits(["clear"]);

const formatTime = (timestamp: string) => {
	return new Date(timestamp).toLocaleTimeString();
};
</script>

<style scoped>
.messages-list {
  max-height: 240px;
  overflow-y: auto;
}

.message-item {
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.4;
}

.message-item p {
  margin: 4px 0 0 0;
  color: #374151;
}
</style>

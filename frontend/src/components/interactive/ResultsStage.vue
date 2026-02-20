<template>
  <div class="stage-content">
    <div class="flex items-center mb-4">
      <CheckCircle class="w-6 h-6 text-green-500 mr-2" />
      <h3 class="text-xl font-semibold">建模结果</h3>
    </div>

    <div v-if="results" class="space-y-4">
      <!-- 结果摘要 -->
      <div class="bg-green-50 p-4 rounded-lg">
        <h4 class="font-medium text-green-900 mb-2">建模完成</h4>
        <p class="text-green-800">所有建模任务已完成，您可以查看详细结果或下载报告。</p>
      </div>

      <!-- 可用操作 -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Button @click="$emit('viewNotebook')" variant="outline">
          <FileText class="w-4 h-4 mr-2" />
          查看代码
        </Button>
        <Button @click="$emit('viewReport')" variant="outline">
          <FileText class="w-4 h-4 mr-2" />
          查看报告
        </Button>
        <Button @click="$emit('download')">
          <Download class="w-4 h-4 mr-2" />
          下载结果
        </Button>
        <Button @click="$emit('newModeling')">
          <Plus class="w-4 h-4 mr-2" />
          新建建模
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { CheckCircle, Download, FileText, Plus } from "lucide-vue-next";

interface ModelingResults {
	task_id?: string;
	status?: string;
	[key: string]: unknown;
}

defineProps<{
	results: ModelingResults | null;
}>();

defineEmits(["viewNotebook", "viewReport", "download", "newModeling"]);
</script>

<style scoped>
.stage-content {
  min-height: 400px;
}
</style>

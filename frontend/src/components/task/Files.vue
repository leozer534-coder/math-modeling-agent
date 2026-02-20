<script setup lang="ts">
import { getFileDownloadUrl } from "@/apis/filesApi";
import Tree from "@/components/task/Tree.vue";
import { SidebarContent, SidebarGroup } from "@/components/ui/sidebar";
import { useTaskStore } from "@/stores/task";
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";

const taskStore = useTaskStore();
const route = useRoute();
const isLoading = ref(true);
// 从消息中提取最新的文件列表（保持 computed 响应式）
const files = computed(() => taskStore.files as string[]);

// 将文件列表转换为树形结构
const fileTree = computed(() => {
	// 直接返回文件列表，不做转换，因为Tree组件期望接收string或数组
	return files.value;
});

// 监听文件树变化，更新加载状态
watch(fileTree, () => {
	// 文件列表被计算后，标记加载完成
	isLoading.value = false;
}, { immediate: true });

// 添加超时机制，确保即使数据没有加载也会在一定时间后显示内容
onMounted(() => {
	// 3秒后无论如何都取消加载状态
	setTimeout(() => {
		isLoading.value = false;
	}, 3000);
});

const handleFileClick = (file: string) => {
	// 根据文件扩展名决定操作
	const ext = file.split(".").pop()?.toLowerCase() || "";
	const imageExts = ["png", "jpg", "jpeg", "gif", "svg", "webp"];
	const previewExts = ["md", "txt", "csv", "json", "log"];

	if (imageExts.includes(ext) || previewExts.includes(ext)) {
		// 图片和文本类文件：通过下载链接在新窗口预览
		handleFileDownload(file);
	} else {
		// 其他文件直接下载
		handleFileDownload(file);
	}
};

const handleFileDownload = async (file: string) => {
	const taskId = route.params.task_id as string | undefined;
	if (!taskId) return;

	try {
		const res = await getFileDownloadUrl(taskId, file);
		const url = res.data.download_url;
		window.open(url, "_blank");
	} catch (error) {
		if (import.meta.env.DEV) {
			console.error("获取文件下载链接失败:", error);
		}
	}
};
</script>

<template>
  <SidebarContent class="h-full">
    <SidebarGroup />
    <div class="h-full flex flex-col overflow-hidden">
      <div class="px-3 py-2 font-medium text-sm border-b">Files</div>
      <div class="flex-1 overflow-auto">
        <div v-if="isLoading" class="px-3 py-2 text-sm text-muted-foreground">
          加载中...
        </div>
        <div v-else-if="fileTree.length === 0" class="px-3 py-2 text-sm text-muted-foreground">
          暂无文件
        </div>
        <div v-else class="p-2">
          <Tree v-for="(item, index) in fileTree" :key="index" :item="item" @click="handleFileClick(item)"
            @download="handleFileDownload(item)" />
        </div>
      </div>
    </div>
    <SidebarGroup />
  </SidebarContent>
</template>

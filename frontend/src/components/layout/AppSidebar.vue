<script setup lang="ts">
import {
	BILLBILL,
	DISCORD,
	GITHUB_LINK,
	QQ_GROUP,
	TWITTER,
	XHS,
} from "@/utils/const";
import { onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter } from "vue-router";
import NavUser from "./NavUser.vue";
import { getUserTasks, type TaskItem } from "@/apis/taskApi";
import { getPersistedToken } from "@/utils/auth";

import {
	Sidebar,
	SidebarContent,
	SidebarFooter,
	SidebarGroup,
	SidebarGroupContent,
	SidebarGroupLabel,
	SidebarHeader,
	SidebarMenu,
	SidebarMenuButton,
	SidebarMenuItem,
	type SidebarProps,
	SidebarRail,
} from "@/components/ui/sidebar";
import { Sigma } from "lucide-vue-next";

const props = defineProps<SidebarProps>();
const { t } = useI18n();
const router = useRouter();

// 历史任务数据
const historyTasks = ref<TaskItem[]>([]);

// 加载历史任务
async function loadHistoryTasks() {
	const token = getPersistedToken();
	if (!token) return;
	try {
		const { data } = await getUserTasks();
		historyTasks.value = data;
	} catch {
		// 静默失败，不影响侧边栏渲染
	}
}

// 导航到任务详情
function navigateToTask(taskId: string) {
	router.push(`/task/${taskId}`);
}

// 导航到新任务页面
function navigateToNewTask() {
	router.push("/chat");
}

// 格式化任务标题（截断过长的标题）
function formatTitle(title: string): string {
	return title.length > 20 ? title.slice(0, 20) + "..." : title;
}

// 状态图标
function statusIcon(status: string): string {
	switch (status) {
		case "completed":
			return "✅";
		case "processing":
			return "⏳";
		case "failed":
			return "❌";
		default:
			return "📋";
	}
}

onMounted(() => {
	loadHistoryTasks();
});

const socialMedia = [
	{
		name: "QQ",
		url: QQ_GROUP,
		icon: "/qq.svg",
	},
	{
		name: "Twitter",
		url: TWITTER,
		icon: "/twitter.svg",
	},
	{
		name: "GitHub",
		url: GITHUB_LINK,
		icon: "/github.svg",
	},
	{
		name: "Bilibili",
		url: BILLBILL,
		icon: "/bilibili.svg",
	},
	{
		name: "Xiaohongshu",
		url: XHS,
		icon: "/xiaohongshu.svg",
	},
	{
		name: "Discord",
		url: DISCORD,
		icon: "/discord.svg",
	},
];
</script>

<template>
  <Sidebar v-bind="props" class="bg-sidebar/80 backdrop-blur-xl border-r-0 shadow-lg" collapsible="icon">
    <SidebarHeader class="px-4 py-5">
      <!-- Logo -->
      <router-link to="/" class="flex items-center gap-3 group px-2">
        <div class="flex h-9 w-9 items-center justify-center rounded-[10px] bg-foreground text-background shadow-sm transition-transform duration-300 group-hover:scale-105 group-active:scale-95">
          <Sigma class="w-5 h-5" />
        </div>
        <span class="text-[15px] font-semibold tracking-tight text-foreground group-hover:text-foreground/80 transition-colors">MathModelAgent</span>
      </router-link>
    </SidebarHeader>

    <SidebarContent class="px-2">
      <!-- 开始新任务 -->
      <SidebarGroup>
        <SidebarGroupLabel class="text-[11px] font-medium text-muted-foreground/60 px-4 py-2 uppercase tracking-widest">
          {{ t("chat.start") }}
        </SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton
                as-child
                class="h-9 px-3 rounded-lg hover:bg-black/5 dark:hover:bg-white/10 transition-all duration-200"
              >
                <a @click.prevent="navigateToNewTask" class="flex items-center gap-3 cursor-pointer">
                  <span class="flex h-6 w-6 items-center justify-center rounded-md bg-blue-50 text-blue-600 dark:bg-blue-500/20 dark:text-blue-400">
                    <plus class="w-4 h-4" />
                  </span>
                  <span class="font-medium">{{ t("chat.newTask") }}</span>
                </a>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>

      <!-- 历史任务 -->
      <SidebarGroup class="mt-2">
        <SidebarGroupLabel class="text-[11px] font-medium text-muted-foreground/60 px-4 py-2 uppercase tracking-widest">
          {{ t("chat.historyTasks") }}
        </SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            <SidebarMenuItem v-if="historyTasks.length === 0">
              <div class="px-4 py-8 text-center">
                <p class="text-[13px] text-muted-foreground/50">{{ t("chat.noHistory") }}</p>
              </div>
            </SidebarMenuItem>
            <SidebarMenuItem v-for="task in historyTasks" :key="task.id" class="mb-0.5">
              <SidebarMenuButton
                as-child
                class="h-9 px-3 rounded-lg hover:bg-black/5 dark:hover:bg-white/10 transition-all duration-200 group/item"
              >
                <a @click.prevent="navigateToTask(task.id)" :title="task.title" class="flex items-center gap-2 cursor-pointer">
                  <span class="text-[10px] opacity-70 group-hover/item:opacity-100 transition-opacity w-4 text-center">{{ statusIcon(task.status) }}</span>
                  <span class="truncate text-[13px] font-medium text-foreground/80 group-hover/item:text-foreground">{{ formatTitle(task.title) }}</span>
                </a>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
    </SidebarContent>

    <SidebarRail />

    <SidebarFooter class="px-4 pb-4">
      <NavUser />
      
       <!-- 社交媒体图标 -->
      <div class="flex items-center gap-4 justify-center mt-4 pt-4 border-t border-border/40">
        <a
          v-for="item in socialMedia"
          :key="item.name"
          :href="item.url"
          target="_blank"
          class="opacity-40 hover:opacity-100 hover:scale-110 transition-all duration-300 grayscale hover:grayscale-0"
        >
          <img :src="item.icon" :alt="item.name" width="16" height="16" class="icon">
        </a>
      </div>
    </SidebarFooter>
  </Sidebar>
</template>

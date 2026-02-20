<template>
  <div class="flex items-center gap-1.5">
    <div
      v-for="(service, key) in services"
      :key="key"
      class="flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] font-medium"
      :class="getStatusClass(service.status)"
    >
      <div
        class="w-1.5 h-1.5 rounded-full"
        :class="getStatusDotClass(service.status)"
      />
      <span class="capitalize">{{ key }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { getServiceStatus } from "@/apis/commonApi";
import { useToast } from "@/components/ui/toast/use-toast";
import { onMounted, onUnmounted, ref } from "vue";

interface ServiceStatus {
	status: "running" | "error" | "unknown";
	message: string;
}

interface Services {
	backend: ServiceStatus;
	redis: ServiceStatus;
}

const { toast } = useToast();
const services = ref<Services>({
	backend: { status: "unknown", message: "Checking..." },
	redis: { status: "unknown", message: "Checking..." },
});

let statusInterval: number | null = null;

const getStatusClass = (status: string) => {
	switch (status) {
		case "running":
			return "bg-emerald-500/[0.06] text-emerald-600 dark:text-emerald-400";
		case "error":
			return "bg-red-500/[0.06] text-red-600 dark:text-red-400";
		default:
			return "bg-muted/50 text-muted-foreground/50";
	}
};

const getStatusDotClass = (status: string) => {
	switch (status) {
		case "running":
			return "bg-emerald-500 animate-pulse";
		case "error":
			return "bg-red-500";
		default:
			return "bg-muted-foreground/40";
	}
};

const checkStatus = async () => {
	try {
		const response = await getServiceStatus();
		const oldStatus = { ...services.value };
		services.value = response.data as Services;

		for (const key of Object.keys(response.data)) {
			const serviceKey = key as keyof Services;
			const newStatus = response.data[serviceKey].status;
			const oldStatusValue = oldStatus[serviceKey].status;

			if (newStatus === "error" && oldStatusValue !== "error") {
				toast({
					title: "服务警告",
					description: `${serviceKey.toUpperCase()} 服务连接失败: ${response.data[serviceKey].message}`,
					variant: "destructive",
				});
			}
		}
	} catch (error) {
		if (import.meta.env.DEV) {
			console.error("Failed to check service status:", error);
		}
		services.value = {
			backend: { status: "error", message: "无法连接后端服务" },
			redis: { status: "unknown", message: "未知" },
		};
	}
};

onMounted(() => {
	checkStatus();
	statusInterval = setInterval(checkStatus, 30000);
});

onUnmounted(() => {
	if (statusInterval) {
		clearInterval(statusInterval);
	}
});
</script>

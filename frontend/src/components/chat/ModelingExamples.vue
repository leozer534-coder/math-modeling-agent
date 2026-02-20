<script setup lang="ts">
import { useToast } from "@/components/ui/toast";
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";

import { exampleAPI } from "@/apis/commonApi";
import mcmCupC from "@/assets/example/2024高教杯C题.png";
import wuyiCupC from "@/assets/example/2025五一杯C题.png";
import huashuCupC from "@/assets/example/华数杯2023年C题.png";
import { ArrowRight } from "lucide-vue-next";

interface ModelingExample {
	id: number;
	title: string;
	source: string;
	description: string;
	tags: string[];
	problemText: string;
	image: string;
}

const { t } = useI18n();
const router = useRouter();
const { toast } = useToast();
const loadingId = ref<number | null>(null);

const examples = ref<ModelingExample[]>([
	{
		id: 1,
		title: t("chatHome.example1Title"),
		source: t("chatHome.example1Source"),
		description: "",
		tags: [t("chatHome.example1Tag1"), t("chatHome.example1Tag2")],
		problemText: "",
		image: huashuCupC,
	},
	{
		id: 2,
		title: t("chatHome.example2Title"),
		source: t("chatHome.example2Source"),
		description: "",
		tags: [t("chatHome.example2Tag1"), t("chatHome.example2Tag2")],
		problemText: "",
		image: wuyiCupC,
	},
	{
		id: 3,
		title: t("chatHome.example3Title"),
		source: t("chatHome.example3Source"),
		description: "",
		tags: [t("chatHome.example3Tag1"), t("chatHome.example3Tag2")],
		problemText: "",
		image: mcmCupC,
	},
]);

const selectExample = async (example: ModelingExample) => {
	try {
		loadingId.value = example.id;
		const res = await exampleAPI(example.id.toString(), example.source);
		const taskId = res?.data?.task_id;
		if (!taskId) {
			toast({
				title: t("chatHome.loadExampleFailed"),
				description: t("chatHome.loadExampleFailedDesc"),
				variant: "destructive",
			});
			return;
		}
		router.push(`/task/${taskId}`);
	} catch (error) {
		if (import.meta.env.DEV) {
			console.error("样例加载失败:", error);
		}
		toast({
			title: t("chatHome.loadExampleFailed"),
			description: t("chatHome.loadExampleFailedDesc"),
			variant: "destructive",
		});
	} finally {
		loadingId.value = null;
	}
};
</script>

<template>
  <div class="mt-14 mb-8">
    <!-- 标题 -->
    <div class="text-center mb-8">
      <h2 class="text-[18px] font-semibold tracking-tight text-foreground mb-1.5">
        {{ t('chatHome.examplesTitle') }}
      </h2>
    </div>

    <!-- 样例卡片网格 -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div
        v-for="example in examples"
        :key="example.id"
        class="group relative rounded-2xl border border-border/40 bg-background/80 overflow-hidden transition-all duration-200 hover:shadow-lg hover:shadow-black/[0.04] hover:border-border/60 cursor-pointer"
        @click="selectExample(example)"
      >
        <!-- 缩略图 -->
        <div class="relative h-40 overflow-hidden bg-muted/30">
          <img
            :src="example.image"
            alt=""
            class="w-full h-full object-cover object-top transition-transform duration-500 group-hover:scale-[1.03]"
          >
          <!-- hover 遮罩 -->
          <div class="absolute inset-0 bg-gradient-to-t from-black/50 via-black/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-end justify-center pb-4">
            <span class="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-white/90 text-black text-[12px] font-medium shadow-lg backdrop-blur-sm">
              {{ t('chatHome.startAnalysis') }}
              <ArrowRight class="w-3 h-3" />
            </span>
          </div>
        </div>

        <!-- 卡片信息 -->
        <div class="p-4">
          <!-- 来源标签 -->
          <p class="text-[11px] text-muted-foreground/50 font-medium uppercase tracking-wider mb-1.5">
            {{ example.source }}
          </p>

          <!-- 标题 -->
          <h3 class="text-[14px] font-medium text-foreground leading-snug line-clamp-2 mb-3">
            {{ example.title }}
          </h3>

          <!-- 标签 -->
          <div class="flex flex-wrap gap-1.5">
            <span
              v-for="tag in example.tags"
              :key="tag"
              class="px-2 py-0.5 rounded-md bg-muted/50 text-muted-foreground/70 text-[11px]"
            >
              {{ tag }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<template>
  <div class="stage-content">
    <div class="flex items-center mb-4">
      <Search class="w-6 h-6 text-blue-500 mr-2" />
      <h3 class="text-xl font-semibold">智能问题分析</h3>
    </div>

    <div v-if="analysisResult" class="space-y-4">
      <!-- 问题摘要 -->
      <div class="bg-blue-50 p-4 rounded-lg">
        <h4 class="font-medium text-blue-900 mb-2">问题摘要</h4>
        <p class="text-blue-800">{{ analysisResult.problem_summary }}</p>
      </div>

      <!-- 关键问题 -->
      <div v-if="analysisResult.key_questions.length > 0" class="bg-amber-50 p-4 rounded-lg">
        <h4 class="font-medium text-amber-900 mb-2">需要澄清的问题</h4>
        <div class="space-y-2">
          <div
            v-for="(question, index) in analysisResult.key_questions"
            :key="index"
            class="flex items-start"
          >
            <span class="text-amber-600 mr-2">Q{{ index + 1 }}:</span>
            <span class="text-gray-700">{{ question }}</span>
          </div>
        </div>

        <div class="mt-4 space-y-2">
          <Textarea
            v-for="(_question, index) in analysisResult.key_questions"
            :key="index"
            :placeholder="`请回答问题 ${index + 1}`"
            v-model="userAnswers[index]"
            class="w-full"
            rows="2"
          />
        </div>
      </div>

      <!-- 建模方法选择 -->
      <div v-if="analysisResult.suggested_approaches.length > 0" class="space-y-2">
        <h4 class="font-medium text-gray-900 mb-3">请选择建模方法：</h4>
        <div class="space-y-3">
          <div
            v-for="(approach, index) in analysisResult.suggested_approaches"
            :key="index"
            class="border rounded-lg p-4 cursor-pointer transition-colors"
            :class="[
              'approach-card',
              { 'border-blue-500 bg-blue-50': selectedApproach === index }
            ]"
            @click="selectApproach(index)"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center">
                <div class="w-5 h-5 rounded-full border-2 mr-3 flex items-center justify-center"
                     :class="selectedApproach === index ? 'border-blue-500 bg-blue-500' : 'border-gray-300'">
                  <CheckCircle v-if="selectedApproach === index" class="w-3 h-3 text-white" />
                </div>
                <div>
                  <h5 class="font-medium">{{ approach.name }}</h5>
                  <p class="text-sm text-gray-600 mt-1">{{ approach.description }}</p>
                </div>
              </div>
              <div class="text-right text-sm">
                <div class="text-amber-600">{{ approach.complexity }}复杂度</div>
                <div class="text-gray-500">{{ approach.suitable_for }}</div>
              </div>
            </div>

            <div v-if="selectedApproach === index" class="mt-3 pt-3 border-t">
              <div class="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span class="text-green-600">✓ 优点:</span>
                  <ul class="mt-1 space-y-1">
                    <li v-for="pro in approach.pros" :key="pro" class="text-gray-600">{{ pro }}</li>
                  </ul>
                </div>
                <div>
                  <span class="text-red-600">✗ 缺点:</span>
                  <ul class="mt-1 space-y-1">
                    <li v-for="con in approach.cons" :key="con" class="text-gray-600">{{ con }}</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="flex justify-between pt-4">
        <Button variant="outline" @click="$emit('cancel')">
          <X class="w-4 h-4 mr-2" />
          取消
        </Button>
        <div class="space-x-2">
          <Button variant="outline" @click="$emit('retry')">
            <RefreshCw class="w-4 h-4 mr-2" />
            重新分析
          </Button>
          <Button @click="confirm" :disabled="selectedApproach === null">
            <CheckCircle class="w-4 h-4 mr-2" />
            确认并继续
          </Button>
        </div>
      </div>
    </div>

    <!-- 分析中状态 -->
    <div v-else-if="isAnalyzing" class="text-center py-8">
      <div class="inline-flex items-center">
        <Loader2 class="w-6 h-6 animate-spin mr-3" />
        <span class="text-lg">AI正在分析问题，请稍候...</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { CheckCircle, Loader2, RefreshCw, Search, X } from "lucide-vue-next";
import { ref, watch } from "vue";

interface AnalysisResult {
	problem_summary: string;
	key_questions: string[];
	suggested_approaches: Array<{
		name: string;
		description: string;
		pros: string[];
		cons: string[];
		complexity: string;
		suitable_for: string;
	}>;
}

const props = defineProps<{
	analysisResult: AnalysisResult | null;
	isAnalyzing: boolean;
}>();

const emit = defineEmits(["confirm", "cancel", "retry"]);

const selectedApproach = ref<number | null>(null);
const userAnswers = ref<string[]>([]);

const selectApproach = (index: number) => {
	selectedApproach.value = index;
};

const confirm = () => {
	emit("confirm", {
		selectedApproach: selectedApproach.value,
		userAnswers: userAnswers.value,
	});
};

// Reset state when analysis result changes
watch(
	() => props.analysisResult,
	() => {
		selectedApproach.value = null;
		userAnswers.value = [];
	},
);
</script>

<style scoped>
.approach-card {
  border: 2px solid #e5e7eb;
  transition: all 0.3s ease;
}

.approach-card:hover {
  border-color: #3b82f6;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.stage-content {
  min-height: 400px;
}
</style>

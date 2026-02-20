<script setup lang="ts">
import { ref } from "vue";
import { useI18n } from "vue-i18n";
import { validateOpenalexEmail } from "@/apis/apiKeyApi";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
	Collapsible,
	CollapsibleContent,
	CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { ChevronRight, BookOpen, CheckCircle, XCircle } from "lucide-vue-next";

const { t } = useI18n();

const props = defineProps<{
	email: string;
}>();

const emit = defineEmits<{
	(e: "update:email", value: string): void;
}>();

const isOpen = ref(false);
const validating = ref(false);
const validationResult = ref<{ valid: boolean; message: string } | null>(null);

function updateEmail(value: string | number) {
	emit("update:email", String(value));
}

async function handleValidate() {
	if (!props.email) return;
	validating.value = true;
	validationResult.value = null;

	try {
		const res = await validateOpenalexEmail({ email: props.email });
		validationResult.value = res.data;
	} catch {
		validationResult.value = {
			valid: false,
			message: t("apiDialog.verifyServiceFailed"),
		};
	} finally {
		validating.value = false;
	}
}
</script>

<template>
  <section>
    <Collapsible v-model:open="isOpen">
      <CollapsibleTrigger
        class="flex items-center justify-between w-full p-3.5 rounded-xl border border-border/40 bg-card/30 hover:bg-accent/20 transition-colors duration-150 cursor-pointer"
      >
        <div class="flex items-center gap-3">
          <div class="flex items-center justify-center w-9 h-9 rounded-lg bg-orange-500/10 shrink-0">
            <BookOpen class="h-4 w-4 text-orange-600 dark:text-orange-400" />
          </div>
          <div class="text-left">
            <div class="flex items-center gap-1.5">
              <span class="text-[13px] font-medium">{{ t('apiDialog.scholarSearch') }}</span>
              <span class="text-[11px] text-muted-foreground/50 px-1.5 py-0.5 rounded-md bg-muted/50">{{ t('apiDialog.optional') }}</span>
            </div>
            <p class="text-[11px] text-muted-foreground/60 leading-tight mt-0.5">OpenAlex Polite Pool</p>
          </div>
        </div>
        <ChevronRight
          class="h-4 w-4 text-muted-foreground/40 transition-transform duration-200 shrink-0"
          :class="{ 'rotate-90': isOpen }"
        />
      </CollapsibleTrigger>

      <CollapsibleContent>
        <div class="mt-3 p-4 rounded-xl border border-border/30 bg-muted/10 space-y-4">
          <p class="text-[12px] text-muted-foreground/70 leading-relaxed">
            {{ t('apiDialog.scholarDesc') }}
          </p>

          <div class="space-y-2.5">
            <Label for="openalex-email" class="text-[13px] font-medium">
              {{ t('apiDialog.openalexLabel') }}
            </Label>
            <div class="flex gap-2">
              <Input
                id="openalex-email"
                :model-value="email"
                @update:model-value="updateEmail"
                placeholder="your@email.com"
                type="email"
                class="h-9 text-[13px] flex-1 rounded-lg"
              />
              <Button
                variant="outline"
                size="sm"
                class="h-9 px-4 text-xs shrink-0 rounded-lg"
                :disabled="!email || validating"
                @click="handleValidate"
              >
                {{ validating ? t('apiDialog.validating') : t('apiDialog.validate') }}
              </Button>
            </div>
            <p class="text-[11px] text-muted-foreground/50 leading-relaxed">
              {{ t('apiDialog.openalexHint') }}
            </p>
          </div>

          <!-- 验证结果 -->
          <div
            v-if="validationResult"
            :class="[
              'flex items-center gap-2 text-[12px] px-3.5 py-2.5 rounded-lg',
              validationResult.valid
                ? 'bg-emerald-500/5 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20'
                : 'bg-red-500/5 text-red-600 dark:text-red-400 border border-red-500/20',
            ]"
          >
            <CheckCircle v-if="validationResult.valid" class="h-3.5 w-3.5 shrink-0" />
            <XCircle v-else class="h-3.5 w-3.5 shrink-0" />
            <span>{{ validationResult.message }}</span>
          </div>
        </div>
      </CollapsibleContent>
    </Collapsible>
  </section>
</template>

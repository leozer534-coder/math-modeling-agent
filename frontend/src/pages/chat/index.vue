<script setup lang="ts">
import AppSidebar from '@/components/layout/AppSidebar.vue'
import UserStepper from '@/components/common/UserStepper.vue'
import ModelingExamples from '@/components/chat/ModelingExamples.vue'
import { onMounted } from 'vue'
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from '@/components/ui/sidebar'
import { getHelloWorld } from '@/apis/commonApi'
import { useI18n } from 'vue-i18n'
import { Brain, Code2, FileText, Workflow, Sparkles } from 'lucide-vue-next'

const { t } = useI18n()

onMounted(() => {
  getHelloWorld().catch(() => {
    if (import.meta.env.DEV) console.error('后端服务未就绪')
  })
})
</script>

<template>
  <SidebarProvider>
    <AppSidebar />
    <SidebarInset class="bg-gradient-to-b from-background to-secondary/30">
      <!-- 顶部导航栏 -->
      <header class="flex h-14 shrink-0 items-center gap-2 px-5 sticky top-0 z-10 bg-background/60 backdrop-blur-md border-b border-border/40">
        <SidebarTrigger class="-ml-1 text-muted-foreground/70 hover:text-foreground transition-colors" />
      </header>

      <!-- 主内容区域 -->
      <div class="flex-1 overflow-y-auto">
        <div class="flex flex-col items-center px-6 sm:px-10 pt-[8vh] pb-12">
          <div class="w-full max-w-4xl mx-auto flex flex-col items-center">
            
            <!-- 欢迎标题区域 -->
            <div class="text-center mb-10 max-w-2xl animate-fade-in-up">
              <div class="flex items-center justify-center gap-2 mb-4">
                 <div class="bg-primary/10 text-primary p-2 rounded-xl">
                    <Sparkles class="w-6 h-6" />
                 </div>
              </div>
              <h1 class="text-[40px] font-bold tracking-tight text-foreground mb-4 leading-tight">
                {{ t('chatHome.welcomeTitle') }}
                <span class="bg-clip-text text-transparent bg-gradient-to-r from-primary to-blue-600">
                   MathModel Agent
                </span>
              </h1>
              <p class="text-[17px] text-muted-foreground/80 leading-relaxed max-w-xl mx-auto">
                {{ t('chatHome.welcomeDesc') }}
              </p>
            </div>

            <!-- Agent 能力指示器 (Pill 风格) -->
            <div class="flex items-center justify-center gap-3 mb-10 flex-wrap animate-fade-in-up" style="animation-delay: 0.1s">
              <div class="group flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-border/60 shadow-sm hover:shadow-md transition-all duration-300 cursor-default">
                <div class="p-1 rounded-full bg-blue-50 text-blue-600 group-hover:bg-blue-100 transition-colors">
                   <Workflow class="w-3.5 h-3.5" />
                </div>
                <span class="text-[13px] font-medium text-foreground/80">{{ t('chatHome.agentCoordinator') }}</span>
              </div>
              <div class="group flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-border/60 shadow-sm hover:shadow-md transition-all duration-300 cursor-default">
                <div class="p-1 rounded-full bg-purple-50 text-purple-600 group-hover:bg-purple-100 transition-colors">
                   <Brain class="w-3.5 h-3.5" />
                </div>
                <span class="text-[13px] font-medium text-foreground/80">{{ t('chatHome.agentModeler') }}</span>
              </div>
              <div class="group flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-border/60 shadow-sm hover:shadow-md transition-all duration-300 cursor-default">
                <div class="p-1 rounded-full bg-emerald-50 text-emerald-600 group-hover:bg-emerald-100 transition-colors">
                   <Code2 class="w-3.5 h-3.5" />
                </div>
                <span class="text-[13px] font-medium text-foreground/80">{{ t('chatHome.agentCoder') }}</span>
              </div>
              <div class="group flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-border/60 shadow-sm hover:shadow-md transition-all duration-300 cursor-default">
                <div class="p-1 rounded-full bg-amber-50 text-amber-600 group-hover:bg-amber-100 transition-colors">
                   <FileText class="w-3.5 h-3.5" />
                </div>
                <span class="text-[13px] font-medium text-foreground/80">{{ t('chatHome.agentWriter') }}</span>
              </div>
            </div>

            <!-- 核心交互区域 -->
            <div class="w-full max-w-2xl animate-fade-in-up" style="animation-delay: 0.2s">
               <UserStepper />
            </div>

            <!-- 底部提示 -->
            <div class="text-center text-[13px] text-muted-foreground/40 mt-8 mb-8 animate-fade-in-up" style="animation-delay: 0.3s">
              {{ t('chatHome.bottomHint') }}
            </div>

            <!-- 样例区域 -->
            <div class="w-full max-w-3xl animate-fade-in-up" style="animation-delay: 0.4s">
               <ModelingExamples />
            </div>
            
          </div>
        </div>
      </div>
    </SidebarInset>
  </SidebarProvider>
</template>

<style scoped>
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.animate-fade-in-up {
  animation: fadeInUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  opacity: 0;
}
</style>

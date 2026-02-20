<script lang="ts">
export const description = 'A login page with form and image.'
</script>

<script setup lang="ts">
import LoginForm from '@/components/auth/LoginForm.vue'
</script>

<template>
  <div class="relative flex min-h-svh flex-col items-center justify-center bg-background overflow-hidden">
    <!-- 背景装饰 -->
    <div class="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-primary/[0.03] via-transparent to-transparent" />

    <!-- Logo -->
    <a
      href="#"
      class="relative z-10 flex items-center gap-2.5 self-center mb-10 group"
    >
      <div class="flex h-8 w-8 items-center justify-center rounded-xl bg-foreground text-background shadow-sm transition-transform duration-200 group-hover:scale-105">
        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M18 6L6 18" /><path d="M8 6h10v10" />
        </svg>
      </div>
      <span class="text-[15px] font-semibold tracking-tight text-foreground">MathModelAgent</span>
    </a>

    <!-- 主体卡片 -->
    <div class="relative z-10 w-full max-w-sm md:max-w-[880px] mx-4">
      <LoginForm />
    </div>
  </div>
</template>

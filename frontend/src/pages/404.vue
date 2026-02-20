<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { ArrowLeft, Home } from "lucide-vue-next";
import { useRouter } from "vue-router";

const router = useRouter();

const goHome = () => router.push("/");
const goBack = () => router.back();
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-background">
    <div class="text-center space-y-6 px-4">
      <div class="text-8xl font-bold text-primary/20">404</div>
      <h1 class="text-2xl font-semibold text-foreground">页面未找到</h1>
      <p class="text-muted-foreground max-w-md mx-auto">
        抱歉，您访问的页面不存在或已被移除。
      </p>
      <div class="flex items-center justify-center gap-3">
        <Button variant="outline" @click="goBack">
          <ArrowLeft class="w-4 h-4 mr-2" />
          返回上页
        </Button>
        <Button @click="goHome">
          <Home class="w-4 h-4 mr-2" />
          回到首页
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { SUPPORTED_LOCALES, getLocale, setLocale } from "@/locales";
import type { LocaleCode } from "@/locales";
import { useUserStore } from "@/stores/user";
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter } from "vue-router";

import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuGroup,
	DropdownMenuItem,
	DropdownMenuLabel,
	DropdownMenuSeparator,
	DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
	SidebarMenu,
	SidebarMenuButton,
	SidebarMenuItem,
	useSidebar,
} from "@/components/ui/sidebar";
import SettingsSheet from "@/components/settings/SettingsSheet.vue";
import {
	BadgeCheck,
	ChevronsUpDown,
	Coins,
	Globe,
	KeyRound,
	LogIn,
	LogOut,
} from "lucide-vue-next";
import { ref } from "vue";

const router = useRouter();
const userStore = useUserStore();
const { isMobile } = useSidebar();
const { t } = useI18n();

const isSettingsOpen = ref(false);

const isLoggedIn = computed(() => userStore.isLoggedIn);
const currentUser = computed(() => userStore.user);
const credits = computed(() => userStore.credits);

// 当前语言
const currentLocale = computed(() => getLocale());

// 切换语言
function handleSwitchLocale() {
	const next: LocaleCode = currentLocale.value === "zh-CN" ? "en-US" : "zh-CN";
	setLocale(next);
}

// 当前语言显示名称
const currentLocaleName = computed(() => {
	return (
		SUPPORTED_LOCALES.find((l) => l.code === currentLocale.value)?.name ?? ""
	);
});

const displayName = computed(() => {
	if (!currentUser.value) return t("user.guest");
	return currentUser.value.nickname || currentUser.value.email.split("@")[0];
});

const displayEmail = computed(() => {
	return currentUser.value?.email || t("user.clickToLogin");
});

const avatarFallback = computed(() => {
	if (!currentUser.value) return "G";
	const name = currentUser.value.nickname || currentUser.value.email;
	return name.charAt(0).toUpperCase();
});

const openSettings = () => {
	isSettingsOpen.value = true;
};

const handleLogout = () => {
	userStore.logout();
	router.push("/login");
};

const handleLogin = () => {
	router.push("/login");
};
</script>

<template>
  <SidebarMenu>
    <SidebarMenuItem>
      <DropdownMenu>
        <DropdownMenuTrigger as-child>
          <SidebarMenuButton size="lg"
            class="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground">
            <Avatar class="h-8 w-8 rounded-lg">
              <AvatarFallback class="rounded-lg bg-primary/10 text-primary">
                {{ avatarFallback }}
              </AvatarFallback>
            </Avatar>
            <div class="grid flex-1 text-left text-sm leading-tight">
              <span class="truncate font-semibold">{{ displayName }}</span>
              <span class="truncate text-xs">{{ displayEmail }}</span>
            </div>
            <ChevronsUpDown class="ml-auto size-4" />
          </SidebarMenuButton>
        </DropdownMenuTrigger>
        <DropdownMenuContent class="w-[--reka-dropdown-menu-trigger-width] min-w-56 rounded-lg"
          :side="isMobile ? 'bottom' : 'right'" align="end" :side-offset="4">
          <DropdownMenuLabel class="p-0 font-normal">
            <div class="flex items-center gap-2 px-1 py-1.5 text-left text-sm">
              <Avatar class="h-8 w-8 rounded-lg">
                <AvatarFallback class="rounded-lg bg-primary/10 text-primary">
                  {{ avatarFallback }}
                </AvatarFallback>
              </Avatar>
              <div class="grid flex-1 text-left text-sm leading-tight">
                <span class="truncate font-semibold">{{ displayName }}</span>
                <span class="truncate text-xs">{{ displayEmail }}</span>
              </div>
            </div>
          </DropdownMenuLabel>

          <template v-if="isLoggedIn">
            <DropdownMenuSeparator />
            <DropdownMenuGroup>
              <DropdownMenuItem class="cursor-default">
                <Coins class="text-warning" />
                <span>{{ t('user.credits') }}: <strong>{{ credits }}</strong></span>
              </DropdownMenuItem>
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            <DropdownMenuGroup>
              <DropdownMenuItem @click="openSettings">
                <KeyRound />
                {{ t('user.apiKey') }}
              </DropdownMenuItem>
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            <DropdownMenuGroup>
              <DropdownMenuItem>
                <BadgeCheck />
                {{ t('user.accountSettings') }}
              </DropdownMenuItem>
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            <DropdownMenuGroup>
              <DropdownMenuItem @click="handleSwitchLocale">
                <Globe />
                {{ t('nav.language') }}: {{ currentLocaleName }}
              </DropdownMenuItem>
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            <DropdownMenuItem @click="handleLogout">
              <LogOut />
              {{ t('user.logout') }}
            </DropdownMenuItem>
          </template>

          <template v-else>
            <DropdownMenuSeparator />
            <DropdownMenuItem @click="handleLogin">
              <LogIn />
              {{ t('user.loginOrRegister') }}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuGroup>
              <DropdownMenuItem @click="openSettings">
                <KeyRound />
                {{ t('user.apiKey') }}
              </DropdownMenuItem>
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            <DropdownMenuGroup>
              <DropdownMenuItem @click="handleSwitchLocale">
                <Globe />
                {{ t('nav.language') }}: {{ currentLocaleName }}
              </DropdownMenuItem>
            </DropdownMenuGroup>
          </template>
        </DropdownMenuContent>
      </DropdownMenu>
    </SidebarMenuItem>
  </SidebarMenu>
  <SettingsSheet v-model:open="isSettingsOpen" />
</template>

import { createI18n } from "vue-i18n";
import enUS from "./en-US";
import zhCN from "./zh-CN";

// 支持的语言列表
export const SUPPORTED_LOCALES = [
	{ code: "zh-CN", name: "简体中文", flag: "🇨🇳" },
	{ code: "en-US", name: "English", flag: "🇺🇸" },
] as const;

export type LocaleCode = (typeof SUPPORTED_LOCALES)[number]["code"];

// localStorage 存储键名
const LOCALE_STORAGE_KEY = "mathmodel-locale";

/**
 * 获取用户首选语言
 * 优先级: localStorage > 浏览器语言 > 默认中文
 */
function getDefaultLocale(): LocaleCode {
	// 1. 从 localStorage 读取
	const stored = localStorage.getItem(LOCALE_STORAGE_KEY);
	if (stored && SUPPORTED_LOCALES.some((l) => l.code === stored)) {
		return stored as LocaleCode;
	}

	// 2. 从浏览器语言推断
	const browserLang = navigator.language;
	if (browserLang.startsWith("en")) {
		return "en-US";
	}

	// 3. 默认中文
	return "zh-CN";
}

const i18n = createI18n({
	legacy: false, // 使用 Composition API 模式
	locale: getDefaultLocale(),
	fallbackLocale: "zh-CN",
	messages: {
		"zh-CN": zhCN,
		"en-US": enUS,
	},
});

/**
 * 切换语言并持久化
 */
export function setLocale(locale: LocaleCode) {
	i18n.global.locale.value = locale;
	localStorage.setItem(LOCALE_STORAGE_KEY, locale);
	// 更新 html lang 属性，提升无障碍性
	document.documentElement.setAttribute("lang", locale);
}

/**
 * 获取当前语言
 */
export function getLocale(): LocaleCode {
	return i18n.global.locale.value as LocaleCode;
}

export default i18n;

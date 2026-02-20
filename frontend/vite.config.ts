import path from "node:path";
import vue from "@vitejs/plugin-vue";
import autoprefixer from "autoprefixer";
import tailwind from "tailwindcss";
import { defineConfig } from "vite";

export default defineConfig({
	css: {
		postcss: {
			plugins: [tailwind(), autoprefixer()],
		},
	},
	plugins: [vue()],
	server: {
		host: "0.0.0.0",
		port: 5173,
		proxy: {
			"/auth": {
				target: "http://localhost:8001",
				changeOrigin: true,
			},
			"/ws": {
				target: "http://localhost:8001",
				changeOrigin: true,
				ws: true,
			},
			"/static": {
				target: "http://localhost:8001",
				changeOrigin: true,
			},
			"/files": {
				target: "http://localhost:8001",
				changeOrigin: true,
			},
			"/interactive": {
				target: "http://localhost:8001",
				changeOrigin: true,
			},
			"/modeling": {
				target: "http://localhost:8001",
				changeOrigin: true,
			},
			"/health": {
				target: "http://localhost:8001",
				changeOrigin: true,
			},
			"/docs": {
				target: "http://localhost:8001",
				changeOrigin: true,
			},
			"/openapi.json": {
				target: "http://localhost:8001",
				changeOrigin: true,
			},
			"/validate-api-key": {
				target: "http://localhost:8001",
				changeOrigin: true,
			},
			"/save-api-config": {
				target: "http://localhost:8001",
				changeOrigin: true,
			},
			"/validate-openalex-email": {
				target: "http://localhost:8001",
				changeOrigin: true,
			},
			"/config": {
				target: "http://localhost:8001",
				changeOrigin: true,
			},
			"/status": {
				target: "http://localhost:8001",
				changeOrigin: true,
			},
			"/track": {
				target: "http://localhost:8001",
				changeOrigin: true,
			},
			"/example": {
				target: "http://localhost:8001",
				changeOrigin: true,
			},
			"/download_url": {
				target: "http://localhost:8001",
				changeOrigin: true,
			},
			"/download_all_url": {
				target: "http://localhost:8001",
				changeOrigin: true,
			},
			"/open_folder": {
				target: "http://localhost:8001",
				changeOrigin: true,
			},
		},
	},
	resolve: {
		alias: {
			"@": path.resolve(__dirname, "./src"),
		},
	},
});

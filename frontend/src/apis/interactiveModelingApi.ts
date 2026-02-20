import request from "@/utils/request";
/**
 * 交互式建模 API 接口封装
 * 复用全局 HTTP 客户端，自动注入认证 Token 和错误处理
 */
import type { AxiosResponse } from "axios";

// ===== 请求类型 =====

/** 用户操作请求参数 */
export interface UserActionRequest {
	task_id: string | null;
	action: string;
	feedback?: Record<string, unknown>;
	message?: string;
}

// ===== 响应类型 =====

/** 启动建模任务响应 */
export interface StartModelingResponse {
	task_id: string;
	status: string;
	message?: string;
}

/** 通用操作响应（暂停、恢复、取消、用户操作等） */
export interface ActionResponse {
	status: string;
	message: string;
}

/** 任务状态响应 */
export interface TaskStatusResponse {
	task_id: string;
	current_stage: string;
	status: string;
	progress?: number;
	[key: string]: unknown;
}

/** 任务历史记录项 */
export interface TaskHistoryItem {
	timestamp: string;
	stage: string;
	action: string;
	detail?: string;
}

/** 任务历史响应 */
export type TaskHistoryResponse = TaskHistoryItem[];

// ===== 超时配置 =====

/** 建模任务需要较长超时时间（5分钟） */
const LONG_TIMEOUT = 300000;

// ===== API 函数 =====

/**
 * 启动交互式建模任务
 */
export function startModeling(
	formData: FormData,
): Promise<AxiosResponse<StartModelingResponse>> {
	return request.post<StartModelingResponse>(
		"/interactive/start-modeling",
		formData,
		{
			headers: { "Content-Type": "multipart/form-data" },
			timeout: LONG_TIMEOUT,
		},
	);
}

/**
 * 发送用户操作（确认、修改、取消、回退、重试等）
 */
export function sendUserAction(
	actionData: UserActionRequest,
): Promise<AxiosResponse<ActionResponse>> {
	return request.post<ActionResponse>("/interactive/user-action", actionData, {
		timeout: LONG_TIMEOUT,
	});
}

/**
 * 获取任务状态
 */
export function getTaskStatus(
	taskId: string,
): Promise<AxiosResponse<TaskStatusResponse>> {
	return request.get<TaskStatusResponse>(`/interactive/task-status/${taskId}`);
}

/**
 * 获取任务历史记录
 */
export function getTaskHistory(
	taskId: string,
): Promise<AxiosResponse<TaskHistoryResponse>> {
	return request.get<TaskHistoryResponse>(
		`/interactive/task-history/${taskId}`,
	);
}

/**
 * 暂停任务
 */
export function pauseTask(
	taskId: string,
): Promise<AxiosResponse<ActionResponse>> {
	return request.post<ActionResponse>(`/interactive/pause-task/${taskId}`);
}

/**
 * 恢复任务
 */
export function resumeTask(
	taskId: string,
): Promise<AxiosResponse<ActionResponse>> {
	return request.post<ActionResponse>(`/interactive/resume-task/${taskId}`);
}

/**
 * 取消任务
 */
export function cancelTask(
	taskId: string,
): Promise<AxiosResponse<ActionResponse>> {
	return request.delete<ActionResponse>(`/interactive/cancel-task/${taskId}`);
}

/**
 * 下载任务结果
 */
export function downloadResults(taskId: string): Promise<AxiosResponse<Blob>> {
	return request.get<Blob>(`/interactive/download-results/${taskId}`, {
		responseType: "blob",
	});
}

/**
 * 轮询任务状态（WebSocket 不可用时的降级方案）
 * @param taskId 任务 ID
 * @param callback 每次轮询到状态后的回调
 * @param intervalMs 轮询间隔，默认 2000ms
 * @returns 取消函数，调用后停止轮询（组件卸载时应调用）
 */
export function pollTaskStatus(
	taskId: string,
	callback?: (status: TaskStatusResponse) => void,
	intervalMs = 2000,
): () => void {
	let cancelled = false;

	const poll = async () => {
		if (cancelled) return;
		try {
			const { data: status } = await getTaskStatus(taskId);
			if (cancelled) return;
			if (callback) {
				callback(status);
			}

			// 如果任务未完成，继续轮询
			if (
				status.current_stage !== "completed" &&
				status.current_stage !== "failed"
			) {
				if (!cancelled) {
					setTimeout(poll, intervalMs);
				}
			}
		} catch (error) {
			if (import.meta.env.DEV) {
				console.error("轮询任务状态失败:", error);
			}
			// 请求失败时也继续轮询（除非已取消）
			if (!cancelled) {
				setTimeout(poll, intervalMs);
			}
		}
	};

	poll();
	return () => {
		cancelled = true;
	};
}

// 向后兼容：导出命名空间对象，供现有组件通过 interactiveModelingApi.xxx() 调用
export const interactiveModelingApi = {
	startModeling,
	sendUserAction,
	getTaskStatus,
	getTaskHistory,
	pauseTask,
	resumeTask,
	cancelTask,
	downloadResults,
	pollMessages: pollTaskStatus,
};

export default interactiveModelingApi;

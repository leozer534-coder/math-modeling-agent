import request from "@/utils/request";

export interface TaskItem {
    id: string;
    title: string;
    status: string;
    created_at: string | null;
    completed_at: string | null;
}

/**
 * 获取当前用户的历史任务列表
 */
export function getUserTasks() {
    return request.get<TaskItem[]>("/auth/tasks");
}

/**
 * 获取指定任务的历史消息
 */
export function getTaskMessages(taskId: string) {
    return request.get<any[]>(`/task/${taskId}/messages`);
}

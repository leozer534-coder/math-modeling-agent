import request from "@/utils/request";

export function submitModelingTask(
	problem: {
		ques_all: string;
		comp_template?: string;
		format_output?: string;
		workflow_mode?: string;
	},
	files?: File[],
) {
	const formData = new FormData();
	// 添加问题数据
	formData.append("ques_all", problem.ques_all);
	formData.append("comp_template", problem.comp_template || "CHINA");
	formData.append("format_output", problem.format_output || "Markdown");

	if (problem.workflow_mode) {
		formData.append("workflow_mode", problem.workflow_mode);
	}

	// 添加文件（如果有）
	if (files && files.length > 0) {
		for (const file of files) {
			formData.append("files", file);
		}
	}

	// 无论是否有文件，都发送请求
	return request.post<{
		task_id: string;
		status: string;
	}>("/modeling", formData, {
		headers: {
			"Content-Type": "multipart/form-data",
		},
		timeout: 30000,
	});
}

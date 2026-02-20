import os
import re
from app.utils.data_recorder import DataRecorder
from app.schemas.A2A import WriterResponse
from app.schemas.enums import CompTemplate
from app.utils.log_util import logger
import json
import uuid


class UserOutput:
    def __init__(
        self,
        work_dir: str,
        ques_count: int,
        data_recorder: DataRecorder | None = None,
        comp_template: CompTemplate | None = None,
    ):
        self.work_dir = work_dir
        self.res: dict[str, dict] = {
            # "eda": {
            #     "response_content": "",
            #     "footnotes": "",
            # },
            # "ques1": {
            #     "response_content": "",
            #     "footnotes": "",
            # },
        }
        self.data_recorder = data_recorder
        self.cost_time = 0.0
        self.initialized = True
        self.ques_count: int = ques_count
        self.comp_template: CompTemplate | None = comp_template
        self.footnotes = {}
        self.metrics_store: dict[str, dict[str, float]] = {}
        self.comparison_entries: list[dict] = []
        self.model_comparison_data: str = ""
        self._init_seq()

    def _init_seq(self):
        # 动态顺序获取拼接res value，正确拼接顺序
        ques_str = [f"ques{i}" for i in range(1, self.ques_count + 1)]

        # 修改：调整章节顺序，确保符合论文结构
        # 与 Flows._get_flow_suffix 和 get_write_flows() 对齐
        base_seq = [
            "firstPage",  # 标题、摘要、关键词
            "RepeatQues",  # 一、问题重述
            "analysisQues",  # 二、问题分析
            "modelAssumption",  # 三、模型假设
            "symbol",  # 四、符号说明和数据预处理
            "eda",  # 四、数据预处理（EDA部分）
            *ques_str,  # 五、模型的建立与求解（问题1、2...）
            "sensitivity_analysis",  # 六、模型的分析与检验
            "model_comparison",  # 六、多模型对比分析
        ]

        # MCM/ICM (AMERICAN) 模板额外包含 innovation_benchmark 章节
        if self.comp_template == CompTemplate.AMERICAN:
            base_seq.append("innovation_benchmark")  # Strengths and Weaknesses

        base_seq.extend([
            "judge",  # 七、模型的评价（CHINA）/ Conclusions（AMERICAN）
            "conclusion",  # 八、结论与建议（CHINA）/ Memo（AMERICAN）
        ])

        self.seq = base_seq

    def set_res(self, key: str, writer_response: WriterResponse):
        self.res[key] = {
            "response_content": writer_response.response_content,
            "footnotes": writer_response.footnotes,
        }

    def get_res(self):
        return self.res

    def get_model_build_solve(self) -> str:
        """获取各子问题的模型求解结果摘要，输出 LLM 友好的自然语言格式。

        将各子问题的写作结果提取 response_content 字段，
        格式化为编号章节形式，避免直接输出 Python 对象表示。

        Returns:
            格式化的求解摘要文本，无结果时返回提示信息。
        """
        ques_items = [
            (key, value)
            for key, value in self.res.items()
            if re.match(r"^ques\d+$", key)
        ]

        if not ques_items:
            return "暂无模型求解结果"

        parts: list[str] = []
        for key, value in ques_items:
            # 提取 response_content 字段（Writer 写入的实际内容）
            if isinstance(value, dict):
                content = value.get("response_content", "")
            else:
                content = str(value)

            # 生成可读的问题编号标签（ques1 -> 问题1）
            ques_num = key.replace("ques", "")
            label = f"问题{ques_num}"

            if content:
                parts.append(f"【{label}求解结果】\n{content}")
            else:
                parts.append(f"【{label}求解结果】\n暂无结果")

        return "\n\n".join(parts)

    def replace_references_with_uuid(self, text: str) -> str:
        # 匹配引用内容，格式为 {[^数字]: 引用内容}
        # 修改正则表达式，匹配大括号包裹的引用格式
        references = re.findall(r"\{\[\^(\d+)\]:\s*(.*?)\}", text, re.DOTALL)

        for ref_num, ref_content in references:
            # 清理引用内容，去除末尾的空格和点号
            ref_content = ref_content.strip().rstrip(".")

            # 检查当前引用内容是否已经存在于footnotes中
            existing_uuid = None
            for uuid_key, footnote_data in self.footnotes.items():
                if footnote_data["content"] == ref_content:
                    existing_uuid = uuid_key
                    break

            if existing_uuid:
                # 如果已存在，使用现有的UUID
                text = re.sub(
                    rf"\{{\[\^{ref_num}\]:.*?\}}",
                    f"[{existing_uuid}]",
                    text,
                    flags=re.DOTALL,
                )
            else:
                # 如果不存在，创建新的UUID和footnote条目
                new_uuid = str(uuid.uuid4())
                self.footnotes[new_uuid] = {
                    "content": ref_content,
                }
                text = re.sub(
                    rf"\{{\[\^{ref_num}\]:.*?\}}",
                    f"[{new_uuid}]",
                    text,
                    flags=re.DOTALL,
                )

        return text

    def sort_text_with_footnotes(self, replace_res: dict) -> dict:
        sort_res = {}
        ref_index = 1

        for seq_key in self.seq:
            if seq_key not in replace_res:
                # 跳过未写入的章节
                continue
            text = replace_res[seq_key]["response_content"]
            # 找到[uuid]
            uuid_list = re.findall(r"\[([a-f0-9-]{36})\]", text)
            # 去重并保留首次出现顺序，避免同一 UUID 多次出现导致 ref_index 跳跃
            uuid_list = list(dict.fromkeys(uuid_list))
            for uid in uuid_list:
                if uid not in self.footnotes:
                    # UUID 未在 footnotes 中注册，保留原文并记录警告
                    logger.warning(
                        "sort_text_with_footnotes: UUID %s 未在 footnotes 中注册，跳过替换",
                        uid,
                    )
                    continue
                text = text.replace(f"[{uid}]", f"[^{ref_index}]")
                if self.footnotes[uid].get("number") is None:
                    self.footnotes[uid]["number"] = ref_index

                ref_index += 1
            sort_res[seq_key] = {
                "response_content": text,
            }

        return sort_res

    def append_footnotes_to_text(self, text: str) -> str:
        if not self.footnotes:
            return text
        text += "\n\n ## 参考文献"
        # 过滤掉没有 number 的条目（未在正文中出现的引用）
        numbered_footnotes = [
            (uid, data) for uid, data in self.footnotes.items()
            if "number" in data
        ]
        sorted_footnotes = sorted(numbered_footnotes, key=lambda x: x[1]["number"])
        for _, footnote in sorted_footnotes:
            text += f"\n\n[^{footnote['number']}]: {footnote['content']}"
        return text

    def get_result_to_save(self) -> str:
        """将所有已写入的章节按 seq 顺序拼接为完整论文文本。

        对 seq 中未被 set_res 写入的章节
        会自动跳过，避免 KeyError 崩溃。
        """
        replace_res = {}

        for key, value in self.res.items():
            new_text = self.replace_references_with_uuid(value["response_content"])
            replace_res[key] = {
                "response_content": new_text,
            }

        sort_res = self.sort_text_with_footnotes(replace_res)

        # 仅拼接已写入的章节，跳过 seq 中未写入的 key
        full_res_1 = "\n\n".join(
            sort_res[key]["response_content"]
            for key in self.seq
            if key in sort_res
        )

        full_res = self.append_footnotes_to_text(full_res_1)
        return full_res

    def set_metrics(self, key: str, metrics: dict[str, float]) -> None:
        """存储子任务的评估指标。

        Args:
            key: 子任务标识，如 'ques1', 'ques2' 等。
            metrics: 评估指标字典，键为指标名，值为数值。
        """
        self.metrics_store[key] = metrics

    def get_metrics(self, key: str) -> dict[str, float]:
        """获取子任务的评估指标。

        Args:
            key: 子任务标识。

        Returns:
            该子任务的指标字典，不存在时返回空字典。
        """
        return self.metrics_store.get(key, {})

    def get_all_metrics(self) -> dict[str, dict[str, float]]:
        """获取所有子任务的评估指标。

        Returns:
            所有子任务指标的副本字典。
        """
        return self.metrics_store.copy()

    def generate_comparison_summary(self) -> str:
        """生成多模型对比摘要文本。

        将所有子任务的评估指标汇总为 Markdown 表格格式，
        供写作阶段引用。

        Returns:
            格式化的对比摘要文本，无指标数据时返回空字符串。
        """
        if not self.metrics_store:
            return ""

        # 收集所有指标名称并排序，确保表头一致
        metric_names = sorted(set(
            m for metrics in self.metrics_store.values()
            for m in metrics.keys()
        ))

        if not metric_names:
            return ""

        lines = ["## 模型评估指标汇总\n"]
        lines.append("| 子任务 | " + " | ".join(metric_names) + " |")

        # 表头分隔行
        lines.append("| --- | " + " | ".join(["---"] * len(metric_names)) + " |")

        for key, metrics in self.metrics_store.items():
            row = f"| {key} | " + " | ".join(
                f"{metrics.get(m, '-')}" if isinstance(metrics.get(m), (int, float)) else "-"
                for m in metric_names
            ) + " |"
            lines.append(row)

        return "\n".join(lines)

    def get_chapter_summary(self, key: str, max_length: int = 300) -> str:
        """获取指定章节的简短摘要（截取前 max_length 字符）。

        Args:
            key: 章节标识，如 'ques1', 'symbol' 等。
            max_length: 最大截取长度。

        Returns:
            章节内容摘要，章节不存在时返回空字符串。
        """
        if key not in self.res:
            return ""
        content = self.res[key].get("response_content", "")
        if not content:
            return ""
        if len(content) <= max_length:
            return content
        return content[:max_length] + "..."

    def get_completed_chapter_summaries(
        self, max_per_chapter: int = 200, max_total: int = 2000
    ) -> str:
        """获取所有已完成章节的简短摘要，按 seq 顺序拼接。

        用于在写作阶段注入前序章节上下文，保持论文连贯性和术语一致性。

        Args:
            max_per_chapter: 每个章节摘要的最大字符数。
            max_total: 全部摘要的总字符数上限。

        Returns:
            格式化的章节摘要文本，无已完成章节时返回空字符串。
        """
        parts: list[str] = []
        current_total = 0
        for key in self.seq:
            if key not in self.res:
                continue
            summary = self.get_chapter_summary(key, max_per_chapter)
            if not summary:
                continue
            entry = f"【{key}】{summary}"
            if current_total + len(entry) > max_total:
                # 已达总量上限，停止添加
                break
            parts.append(entry)
            current_total += len(entry)
        return "\n".join(parts)

    def save_result(
        self,
    ):
        with open(os.path.join(self.work_dir, "res.json"), "w", encoding="utf-8") as f:
            json.dump(self.res, f, ensure_ascii=False, indent=4)

        res_path = os.path.join(self.work_dir, "res.md")
        with open(res_path, "w", encoding="utf-8") as f:
            f.write(self.get_result_to_save())

"""
数据预览阶段 - 扫描工作目录中的数据文件并生成摘要

职责:
  1. 扫描 work_dir 中的 csv/xlsx/xls/tsv 文件
  2. 读取基础信息（列名、类型、缺失值、统计量、前 5 行）
  3. 生成数据摘要字符串，写入 ctx.artifacts["data_summary"]
  4. 此阶段为可选阶段，失败不中断主工作流
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pandas as pd

from app.core.workflow.stages.artifact_keys import ArtifactKeys
from app.core.workflow.stages.stage_constants import (
    DATA_PREVIEW_MAX_FILE_SIZE,
    DATA_SUMMARY_MAX_LENGTH,
)
from app.utils.log_util import logger


if TYPE_CHECKING:
    from app.core.workflow.pipeline import PipelineContext


class DataPreviewStage:
    """数据预览阶段（可选）"""

    @property
    def name(self) -> str:
        return "data_preview"

    async def execute(self, ctx: PipelineContext) -> None:
        """扫描数据文件并生成摘要"""
        await ctx.send_progress("正在预览数据文件...", 18)

        supported_exts = {".csv", ".xlsx", ".xls", ".tsv"}
        work_dir = ctx.work_dir

        try:
            all_files = os.listdir(work_dir)
        except OSError as e:
            logger.warning("无法读取工作目录: %s", e)
            ctx.artifacts[ArtifactKeys.DATA_SUMMARY] = ""
            return

        data_files = [
            f
            for f in all_files
            if os.path.splitext(f)[1].lower() in supported_exts
        ]

        if not data_files:
            logger.info("工作目录中未发现数据文件")
            ctx.artifacts[ArtifactKeys.DATA_SUMMARY] = ""
            return

        summary_parts: list[str] = []
        for filename in data_files:
            filepath = os.path.join(work_dir, filename)
            try:
                file_size = os.path.getsize(filepath)
                read_full = file_size < DATA_PREVIEW_MAX_FILE_SIZE

                ext = os.path.splitext(filename)[1].lower()
                nrows = None if read_full else 1000

                if ext in (".csv",):
                    df = pd.read_csv(filepath, nrows=nrows)
                elif ext == ".tsv":
                    df = pd.read_csv(filepath, sep="\t", nrows=nrows)
                else:
                    df = pd.read_excel(filepath, nrows=nrows)

                summary = f"### 文件: {filename}\n"
                row_note = (
                    "（完整数据）"
                    if read_full
                    else f"（仅预览前1000行，实际 {file_size / 1024 / 1024:.1f}MB）"
                )
                summary += (
                    f"- 行数: {len(df)}{row_note}, "
                    f"列数: {len(df.columns)}\n"
                )
                summary += f"- 列名: {list(df.columns)}\n"
                summary += "- 数据类型:\n"
                for col, dtype in df.dtypes.items():
                    summary += f"  - {col}: {dtype}\n"

                missing = df.isnull().sum()
                if missing.sum() > 0:
                    summary += "- 缺失值统计:\n"
                    for col, count in missing.items():
                        if count > 0:
                            pct = count / len(df) * 100
                            summary += f"  - {col}: {count} ({pct:.1f}%)\n"
                else:
                    summary += "- 缺失值: 无\n"

                numeric_cols = df.select_dtypes(include="number").columns
                if len(numeric_cols) > 0:
                    desc = df[numeric_cols[:10]].describe()
                    label = (
                        "数值列基础统计（前10列）"
                        if len(numeric_cols) > 10
                        else "数值列基础统计"
                    )
                    summary += f"- {label}:\n{desc.to_string()}\n"

                summary += f"- 前5行预览:\n{df.head().to_string()}\n"
                summary_parts.append(summary)

            except Exception as e:
                logger.warning("读取文件 %s 失败: %s", filename, e)
                summary_parts.append(
                    f"### 文件: {filename}\n- 读取失败: {str(e)[:100]}\n"
                )

        data_summary = "\n".join(summary_parts)
        if len(data_summary) > DATA_SUMMARY_MAX_LENGTH:
            data_summary = data_summary[:DATA_SUMMARY_MAX_LENGTH] + "\n... (已截断)"

        ctx.artifacts[ArtifactKeys.DATA_SUMMARY] = data_summary

        logger.info(
            "数据预览完成，发现 %d 个数据文件，摘要长度: %d",
            len(data_files),
            len(data_summary),
        )
        await ctx.send_progress(
            f"数据预览完成，发现 {len(data_files)} 个数据文件", 19
        )

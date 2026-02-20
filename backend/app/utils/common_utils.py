import os
import datetime
import uuid
import tomllib
from pathlib import Path
from app.schemas.enums import CompTemplate, FormatOutPut
from app.utils.log_util import logger
import re
import pypandoc
from app.config.setting import settings

# 工作目录基准路径（backend/ 目录），避免依赖进程 CWD
_PROJECT_BASE = Path(__file__).resolve().parent.parent.parent  # -> backend/app/utils -> backend/app -> backend


def create_task_id() -> str:
    """生成任务ID"""
    # 生成时间戳和随机标识符
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    random_id = uuid.uuid4().hex[:8]
    return f"{timestamp}-{random_id}"


def create_work_dir(task_id: str) -> str:
    """创建任务工作目录并返回绝对路径。"""
    work_dir = _PROJECT_BASE / "project" / "work_dir" / task_id

    try:
        work_dir.mkdir(parents=True, exist_ok=True)
        return str(work_dir)
    except Exception as e:
        # 捕获并记录创建目录时的异常
        logger.error("创建工作目录失败: %s", e)
        raise


def get_work_dir(task_id: str) -> str:
    """获取任务工作目录的绝对路径。"""
    work_dir = _PROJECT_BASE / "project" / "work_dir" / task_id
    if work_dir.exists():
        return str(work_dir)
    else:
        logger.error("工作目录不存在: %s", work_dir)
        raise FileNotFoundError(f"工作目录不存在: {work_dir}")


def get_config_template(
    comp_template: CompTemplate = CompTemplate.CHINA,
    format_output: FormatOutPut = FormatOutPut.Markdown,
) -> dict:
    """根据竞赛模板类型和输出格式加载对应的配置模板。

    Args:
        comp_template: 竞赛模板类型，支持 CHINA 和 AMERICAN
        format_output: 输出格式，支持 Markdown 和 LaTeX

    Returns:
        模板配置字典

    Raises:
        ValueError: 传入不支持的模板类型时抛出
    """
    _config_dir = _PROJECT_BASE / "app" / "config"

    # 兼容 str 和 Enum 两种类型
    fmt_value = format_output.value if hasattr(format_output, 'value') else str(format_output)

    if comp_template == CompTemplate.CHINA:
        return load_toml(str(_config_dir / "md_template.toml"))
    elif comp_template == CompTemplate.AMERICAN:
        # 如果选择 LaTeX 输出格式，优先加载 LaTeX 版模板
        if fmt_value == "LaTeX":
            latex_path = _config_dir / "mcm_latex_template.toml"
            if latex_path.exists():
                return load_toml(str(latex_path))
            else:
                logger.warning(
                    "AMERICAN LaTeX 模板文件不存在: %s，回退到 Markdown 模板", latex_path
                )
        # Markdown 格式或 LaTeX 模板不存在时，加载默认美赛模板
        mcm_path = _config_dir / "mcm_template.toml"
        if mcm_path.exists():
            return load_toml(str(mcm_path))
        else:
            logger.warning(
                "AMERICAN 模板文件不存在: %s，回退到 CHINA 模板", mcm_path
            )
            return load_toml(str(_config_dir / "md_template.toml"))
    else:
        raise ValueError(f"不支持的竞赛模板类型: {comp_template}")


def load_toml(path: str) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def load_markdown(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def get_current_files(folder_path: str, file_type: str = "all") -> list[str]:
    """获取指定目录下的文件列表，可按类型过滤。

    Args:
        folder_path: 目标文件夹路径
        file_type: 文件类型过滤，支持 "all", "md", "ipynb", "data", "image"

    Returns:
        匹配的文件名列表，不支持的 file_type 返回空列表
    """
    files = os.listdir(folder_path)
    if file_type == "all":
        return files
    elif file_type == "md":
        return [file for file in files if file.endswith(".md")]
    elif file_type == "ipynb":
        return [file for file in files if file.endswith(".ipynb")]
    elif file_type == "data":
        return [
            file for file in files if file.endswith(".xlsx") or file.endswith(".csv")
        ]
    elif file_type == "image":
        return [
            file for file in files if file.endswith(".png") or file.endswith(".jpg")
        ]
    else:
        return []


# 判断content是否包含图片 xx.png,对其处理为    ![filename](http://localhost:8000/files/tasks/20250428-200915-ebc154d4/filename.jpg)
def transform_link(task_id: str, content: str) -> str:
    """将 Markdown 图片的相对路径替换为带 task_id 的静态资源绝对 URL（使用带认证的 secure_files_router API）。"""
    # task_id 格式校验：仅允许字母、数字、下划线、连字符
    if not re.match(r"^[\w-]+$", task_id):
        logger.warning("task_id 包含非法字符: %s", task_id)
        return content  # 不做替换，返回原文
    content = re.sub(
        r"!\[(.*?)\]\((.*?\.(?:png|jpg|jpeg|gif|bmp|webp))\)",
        lambda match: f"![{match.group(1)}]({settings.SERVER_HOST}/files/tasks/{task_id}/{match.group(2)})",
        content,
    )
    return content


# TODO: fix 公式显示
def md_2_docx(task_id: str):
    work_dir = get_work_dir(task_id)
    md_path = os.path.join(work_dir, "res.md")
    docx_path = os.path.join(work_dir, "res.docx")

    extra_args = [
        "--resource-path",
        str(work_dir),
        "--standalone",
    ]

    pypandoc.convert_file(
        source_file=md_path,
        to="docx",
        outputfile=docx_path,
        format="markdown+tex_math_dollars",
        extra_args=extra_args,
    )
    logger.info("转换完成: %s", docx_path)


def split_footnotes(text: str) -> tuple[str, list[tuple[str, str]]]:
    main_text = re.sub(
        r"\n\[\^\d+\]:.*?(?=\n\[\^|\n\n|\Z)", "", text, flags=re.DOTALL
    ).strip()

    # 匹配脚注定义
    footnotes = re.findall(r"\[\^(\d+)\]:\s*(.+?)(?=\n\[\^|\n\n|\Z)", text, re.DOTALL)
    logger.debug("split_footnotes 完整输出: main_text=%s, footnotes=%s", main_text, footnotes)
    logger.info("split_footnotes: main_text 长度=%d, footnotes 数量=%d", len(main_text), len(footnotes))
    return main_text, footnotes


def _read_csv_with_fallback(
    filepath: str, nrows: int = 5000, sep: str = ","
) -> "pd.DataFrame":
    """尝试多种编码读取 CSV 文件。

    按 utf-8 -> gbk -> gb2312 -> latin-1 的顺序尝试解码，
    latin-1 作为兜底编码不会抛出 UnicodeDecodeError，但可能产生乱码。

    Args:
        filepath: CSV 文件路径
        nrows: 最大读取行数，用于采样摘要
        sep: 列分隔符

    Returns:
        解析后的 DataFrame

    Raises:
        最后一个非编码类异常（如文件不存在）
    """
    import pandas as pd

    encodings = ("utf-8", "gbk", "gb2312", "latin-1")
    last_error: Exception | None = None
    for enc in encodings:
        try:
            return pd.read_csv(filepath, nrows=nrows, encoding=enc, sep=sep)
        except (UnicodeDecodeError, UnicodeError) as e:
            last_error = e
            continue
        except Exception as e:
            # 非编码类错误（如文件不存在、解析错误），直接抛出
            raise e
    # 所有编码都失败（理论上 latin-1 不会失败，此为防御性兜底）
    raise last_error  # type: ignore[misc]


def generate_data_summary(work_dir: str, max_chars: int = 5000) -> str:
    """扫描工作目录中的数据文件并生成文本摘要。

    不依赖 Pipeline 上下文，可在任何工作流中独立使用。
    复用 DataPreviewStage 的核心逻辑，为 Modeler 提供数据感知能力。

    Args:
        work_dir: 工作目录路径
        max_chars: 摘要最大字符数

    Returns:
        数据文件的文本摘要，无数据文件时返回空字符串
    """
    import pandas as pd

    supported_exts = {".csv", ".xlsx", ".xls", ".tsv"}
    max_file_size = 50 * 1024 * 1024  # 50MB
    # 摘要场景下统一采样行数，无需全量读取
    sample_nrows = 5000

    try:
        all_files = os.listdir(work_dir)
    except OSError:
        return ""

    data_files = [
        f for f in all_files
        if os.path.splitext(f)[1].lower() in supported_exts
    ]

    if not data_files:
        return ""

    summary_parts: list[str] = []
    for filename in data_files:
        filepath = os.path.join(work_dir, filename)
        try:
            file_size = os.path.getsize(filepath)
            if file_size > max_file_size:
                summary_parts.append(
                    f"### 文件: {filename}\n"
                    f"- 文件过大 ({file_size / 1024 / 1024:.1f}MB > "
                    f"{max_file_size / 1024 / 1024:.0f}MB 上限)，跳过预览\n"
                )
                continue
            nrows = sample_nrows

            ext = os.path.splitext(filename)[1].lower()
            if ext in (".csv",):
                df = _read_csv_with_fallback(filepath, nrows=nrows)
            elif ext == ".tsv":
                df = _read_csv_with_fallback(filepath, nrows=nrows, sep="\t")
            else:
                df = pd.read_excel(filepath, nrows=nrows)

            part = f"### 文件: {filename}\n"
            row_note = f"（采样前{nrows}行，实际 {file_size / 1024 / 1024:.1f}MB）"
            part += f"- 维度: {len(df)} 行 × {len(df.columns)} 列{row_note}\n"
            part += f"- 列名: {list(df.columns)}\n"

            # 前 3 行样例数据
            part += f"- 样例数据（前3行）:\n{df.head(3).to_string()}\n"

            # 数据类型概要
            type_counts = df.dtypes.value_counts()
            part += f"- 类型分布: {dict(type_counts)}\n"

            # 缺失值
            missing = df.isnull().sum()
            missing_cols = missing[missing > 0]
            if len(missing_cols) > 0:
                part += f"- 缺失值列: {len(missing_cols)} 列\n"
                for col, count in missing_cols.head(5).items():
                    pct = count / len(df) * 100
                    part += f"  - {col}: {count} ({pct:.1f}%)\n"
                if len(missing_cols) > 5:
                    part += f"  - ... 还有 {len(missing_cols) - 5} 列有缺失值\n"
            else:
                part += "- 缺失值: 无\n"

            # 数值列统计（精简版）
            numeric_cols = df.select_dtypes(include="number").columns
            if len(numeric_cols) > 0:
                desc = df[numeric_cols[:5]].describe().loc[["mean", "std", "min", "max"]]
                part += f"- 数值列统计（前5列）:\n{desc.to_string()}\n"

            # 偏度和峰度（帮助 Modeler 判断数据分布特征）
            if len(numeric_cols) > 0:
                try:
                    skew_data = df[numeric_cols[:5]].skew()
                    kurt_data = df[numeric_cols[:5]].kurtosis()
                    part += f"- 偏度: {dict(skew_data.round(2))}\n"
                    part += f"- 峰度: {dict(kurt_data.round(2))}\n"
                except Exception:
                    pass

            # Top-5 相关性（帮助 Modeler 识别关键特征关系）
            corr_pairs: list[tuple[str, str, float, float]] = []
            if len(numeric_cols) >= 2:
                try:
                    import numpy as np

                    corr_matrix = df[numeric_cols].corr()
                    for i in range(len(corr_matrix.columns)):
                        for j in range(i + 1, len(corr_matrix.columns)):
                            val = corr_matrix.iloc[i, j]
                            if pd.notna(val):
                                corr_pairs.append((
                                    corr_matrix.columns[i],
                                    corr_matrix.columns[j],
                                    round(abs(val), 3),
                                    round(val, 3),
                                ))
                    corr_pairs.sort(key=lambda x: x[2], reverse=True)
                    if corr_pairs:
                        top_n = min(5, len(corr_pairs))
                        part += f"- Top-{top_n} 相关性:\n"
                        for col1, col2, abs_val, val in corr_pairs[:top_n]:
                            part += f"  - {col1} ↔ {col2}: {val}\n"
                except Exception:
                    pass

            # 日期列检测（帮助 Modeler 判断是否为时间序列问题）
            date_cols: list[str] = []
            try:
                object_cols = df.select_dtypes(include=["object", "datetime"]).columns
                for col in object_cols[:10]:  # 最多检查10列
                    if df[col].dtype == "datetime64[ns]":
                        date_cols.append(col)
                        continue
                    # 尝试解析字符串列为日期
                    try:
                        sample = df[col].dropna().head(20)
                        if len(sample) > 0:
                            parsed = pd.to_datetime(sample, errors="coerce")
                            success_rate = parsed.notna().sum() / len(sample)
                            if success_rate > 0.8:
                                date_cols.append(col)
                    except Exception:
                        pass
                if date_cols:
                    part += f"- 疑似日期列: {date_cols}（可能为时间序列数据）\n"
            except Exception:
                pass

            # 类别列基数（帮助 Modeler 判断分类特征）
            cat_cols = df.select_dtypes(include=["object", "category"]).columns
            if len(cat_cols) > 0:
                try:
                    cat_info: dict[str, int] = {}
                    for col in cat_cols[:8]:  # 最多8列
                        nunique = df[col].nunique()
                        cat_info[col] = nunique
                    part += f"- 类别列基数: {cat_info}\n"
                    # 低基数列展示具体取值
                    for col, n in cat_info.items():
                        if n <= 10:
                            values = df[col].dropna().unique().tolist()[:10]
                            part += f"  - {col} 取值: {values}\n"
                except Exception:
                    pass

            # 数据特征自动推断
            try:
                inferences: list[str] = []
                if date_cols:
                    inferences.append("时间序列数据")
                if len(numeric_cols) > len(df.columns) * 0.7:
                    inferences.append("以数值特征为主")
                if len(missing_cols) > len(df.columns) * 0.3:
                    inferences.append("缺失值较多，需重点处理")
                if len(cat_cols) > 0 and any(
                    df[c].nunique() <= 5
                    for c in cat_cols[:5]
                    if c in df.columns
                ):
                    inferences.append("含分类标签（可能为分类问题）")
                if len(numeric_cols) >= 2:
                    high_corr = [p for p in corr_pairs if p[2] > 0.8]
                    if high_corr:
                        inferences.append(
                            f"存在{len(high_corr)}对高相关特征（>0.8），注意多重共线性"
                        )
                if inferences:
                    part += f"- 数据特征推断: {', '.join(inferences)}\n"
            except Exception:
                pass

            summary_parts.append(part)

        except Exception as e:
            summary_parts.append(f"### 文件: {filename}\n- 读取失败: {str(e)[:80]}\n")

    result = "\n".join(summary_parts)
    if len(result) > max_chars:
        result = result[:max_chars] + "\n... (已截断)"
    return result

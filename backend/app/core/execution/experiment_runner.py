"""
Experiment Runner - 实验运行器
==============================

功能：
1. 统一执行协议
2. 运行环境快照
3. 输入输出版本化
"""

import hashlib
import json
import platform
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.schemas.contracts import (
    EnvironmentSpec,
    InputSpec,
    OutputSpec,
    RunManifest,
    create_run_manifest,
)
from app.utils.log_util import logger


@dataclass
class ExperimentConfig:
    problem_id: str
    experiment_name: str
    seeds: Dict[str, int] = field(default_factory=lambda: {"numpy": 42, "random": 42})
    timeout_seconds: int = 3600
    capture_outputs: bool = True
    save_artifacts: bool = True
    artifact_dir: Optional[str] = None


@dataclass
class ExperimentOutput:
    name: str
    data: Any
    output_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExperimentResult:
    run_id: str
    config: ExperimentConfig
    manifest: RunManifest
    outputs: List[ExperimentOutput]
    metrics: Dict[str, float]
    logs: List[str]
    success: bool
    error: Optional[str] = None
    started_at: str = ""
    completed_at: str = ""


class ExperimentRunner:
    def __init__(
        self,
        base_artifact_dir: str = "./experiments",
    ):
        self.base_artifact_dir = Path(base_artifact_dir)
        self._active_runs: Dict[str, ExperimentResult] = {}

    async def run_experiment(
        self,
        config: ExperimentConfig,
        experiment_func: Callable[..., Any],
        inputs: Optional[Dict[str, Any]] = None,
    ) -> ExperimentResult:
        run_id = f"exp_{uuid.uuid4().hex[:12]}"
        started_at = datetime.now().isoformat()

        manifest = create_run_manifest(
            run_id=run_id,
            problem_id=config.problem_id,
            interpreter="local",
        )
        manifest["seeds"] = config.seeds

        self._set_random_seeds(config.seeds)

        if inputs:
            manifest["inputs"] = self._process_inputs(inputs)

        logs: List[str] = []
        outputs: List[ExperimentOutput] = []
        metrics: Dict[str, float] = {}
        error: Optional[str] = None
        success = True

        logs.append(
            f"[{datetime.now().isoformat()}] Starting experiment: {config.experiment_name}"
        )

        try:
            import asyncio

            if asyncio.iscoroutinefunction(experiment_func):
                result = await asyncio.wait_for(
                    experiment_func(inputs or {}),
                    timeout=config.timeout_seconds,
                )
            else:
                result = experiment_func(inputs or {})

            if isinstance(result, dict):
                if "outputs" in result:
                    for out in result["outputs"]:
                        outputs.append(
                            ExperimentOutput(
                                name=out.get("name", "output"),
                                data=out.get("data"),
                                output_type=out.get("type", "unknown"),
                                metadata=out.get("metadata", {}),
                            )
                        )
                if "metrics" in result:
                    metrics = result["metrics"]

            logs.append(
                f"[{datetime.now().isoformat()}] Experiment completed successfully"
            )

        except asyncio.TimeoutError:
            error = f"Experiment timed out after {config.timeout_seconds}s"
            success = False
            logs.append(f"[{datetime.now().isoformat()}] ERROR: {error}")
        except Exception as e:
            error = str(e)
            success = False
            logs.append(f"[{datetime.now().isoformat()}] ERROR: {error}")

        completed_at = datetime.now().isoformat()
        manifest["completed_at"] = completed_at
        manifest["status"] = "completed" if success else "failed"
        manifest["metrics"] = metrics
        manifest["error"] = error

        if config.save_artifacts and outputs:
            manifest["outputs"] = self._save_artifacts(run_id, outputs, config)

        experiment_result = ExperimentResult(
            run_id=run_id,
            config=config,
            manifest=manifest,
            outputs=outputs,
            metrics=metrics,
            logs=logs,
            success=success,
            error=error,
            started_at=started_at,
            completed_at=completed_at,
        )

        self._active_runs[run_id] = experiment_result
        return experiment_result

    def create_environment_snapshot(self) -> EnvironmentSpec:
        try:
            pip_result = subprocess.run(
                [sys.executable, "-m", "pip", "freeze"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            pip_freeze = (
                pip_result.stdout.strip().split("\n")
                if pip_result.returncode == 0
                else []
            )
        except Exception as e:
            logger.warning("pip freeze 获取失败，使用空列表: %s", e)
            pip_freeze = []

        return EnvironmentSpec(
            python_version=sys.version,
            pip_freeze=pip_freeze[:100],
            platform=platform.platform(),
            interpreter="local",
            image_id=None,
        )

    def _set_random_seeds(self, seeds: Dict[str, int]) -> None:
        try:
            import random

            import numpy as np

            if "random" in seeds:
                random.seed(seeds["random"])
            if "numpy" in seeds:
                np.random.seed(seeds["numpy"])
        except ImportError:
            pass

    def _process_inputs(self, inputs: Dict[str, Any]) -> List[InputSpec]:
        input_specs: List[InputSpec] = []

        for name, value in inputs.items():
            if isinstance(value, (str, Path)) and Path(value).exists():
                path = Path(value)
                with open(path, "rb") as f:
                    content = f.read()
                    file_hash = hashlib.sha256(content).hexdigest()

                input_specs.append(
                    InputSpec(
                        name=name,
                        path=str(path),
                        hash=file_hash,
                        size_bytes=len(content),
                        type=path.suffix.lstrip(".") or "unknown",
                    )
                )
            else:
                serialized = json.dumps(value, default=str).encode()
                input_specs.append(
                    InputSpec(
                        name=name,
                        path="memory",
                        hash=hashlib.sha256(serialized).hexdigest(),
                        size_bytes=len(serialized),
                        type="json",
                    )
                )

        return input_specs

    def _save_artifacts(
        self,
        run_id: str,
        outputs: List[ExperimentOutput],
        config: ExperimentConfig,
    ) -> List[OutputSpec]:
        artifact_dir = Path(config.artifact_dir or self.base_artifact_dir) / run_id
        artifact_dir.mkdir(parents=True, exist_ok=True)

        output_specs: List[OutputSpec] = []

        for output in outputs:
            try:
                if output.output_type == "figure":
                    filename = f"{output.name}.png"
                elif output.output_type == "dataframe":
                    filename = f"{output.name}.csv"
                else:
                    filename = f"{output.name}.json"

                filepath = artifact_dir / filename

                if output.output_type == "json" or output.output_type == "dict":
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(
                            output.data, f, ensure_ascii=False, indent=2, default=str
                        )
                elif output.output_type == "dataframe":
                    if hasattr(output.data, "to_csv"):
                        output.data.to_csv(filepath, index=False)
                elif output.output_type == "figure":
                    if hasattr(output.data, "savefig"):
                        output.data.savefig(filepath)
                else:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(str(output.data))

                with open(filepath, "rb") as f:
                    content = f.read()
                    file_hash = hashlib.sha256(content).hexdigest()

                output_specs.append(
                    OutputSpec(
                        name=output.name,
                        path=str(filepath),
                        hash=file_hash,
                        type=output.output_type,
                        created_at=datetime.now().isoformat(),
                    )
                )

            except Exception as e:
                logger.warning("Failed to save artifact %s: %s", output.name, e)

        return output_specs

    def get_run(self, run_id: str) -> Optional[ExperimentResult]:
        return self._active_runs.get(run_id)

    def list_runs(self) -> List[str]:
        return list(self._active_runs.keys())

    def compare_runs(
        self,
        run_ids: List[str],
    ) -> Dict[str, Any]:
        runs = [
            self._active_runs.get(rid) for rid in run_ids if rid in self._active_runs
        ]

        if len(runs) < 2:
            return {"error": "Need at least 2 valid runs to compare"}

        comparison: Dict[str, Any] = {
            "runs": [r.run_id for r in runs if r],
            "metrics_comparison": {},
            "success_rate": sum(1 for r in runs if r and r.success) / len(runs),
        }

        all_metrics: set = set()
        for run in runs:
            if run:
                all_metrics.update(run.metrics.keys())

        for metric in all_metrics:
            values = [r.metrics.get(metric) for r in runs if r and metric in r.metrics]
            if values:
                comparison["metrics_comparison"][metric] = {
                    "values": values,
                    "min": min(values),
                    "max": max(values),
                    "mean": sum(values) / len(values),
                }

        return comparison


experiment_runner = ExperimentRunner()


async def run_experiment(
    problem_id: str,
    experiment_name: str,
    experiment_func: Callable[..., Any],
    inputs: Optional[Dict[str, Any]] = None,
    seeds: Optional[Dict[str, int]] = None,
) -> ExperimentResult:
    config = ExperimentConfig(
        problem_id=problem_id,
        experiment_name=experiment_name,
        seeds=seeds or {"numpy": 42, "random": 42},
    )
    return await experiment_runner.run_experiment(config, experiment_func, inputs)

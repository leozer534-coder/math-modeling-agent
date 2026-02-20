from app.config.setting import settings
from app.core.llm.llm import LLM


class LLMFactory:
    task_id: str

    def __init__(self, task_id: str, agent_configs: dict | None = None) -> None:
        self.task_id = task_id
        self._agent_configs = agent_configs

    def _get_config(self, agent_key: str) -> tuple[str, str, str]:
        """获取指定 agent 的 (api_key, model, base_url) 配置。

        优先使用 agent_configs（来自前端保存的配置），
        缺失时回退到全局 settings。
        """
        if self._agent_configs and agent_key in self._agent_configs:
            cfg = self._agent_configs[agent_key]
            return (
                cfg.get("api_key", ""),
                cfg.get("model", ""),
                cfg.get("base_url", ""),
            )

        # 回退到全局 settings
        key_upper = agent_key.upper()
        return (
            getattr(settings, f"{key_upper}_API_KEY", ""),
            getattr(settings, f"{key_upper}_MODEL", ""),
            getattr(settings, f"{key_upper}_BASE_URL", ""),
        )

    def get_all_llms(self) -> tuple[LLM, LLM, LLM, LLM]:
        agents = ("coordinator", "modeler", "coder", "writer")
        llms = []
        for agent_key in agents:
            api_key, model, base_url = self._get_config(agent_key)
            llms.append(
                LLM(
                    api_key=api_key,
                    model=model,
                    base_url=base_url,
                    task_id=self.task_id,
                )
            )
        return tuple(llms)  # type: ignore[return-value]


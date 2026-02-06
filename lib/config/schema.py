"""Configuration schema using Pydantic."""

from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings


class TelegramConfig(BaseModel):
    """Telegram channel configuration."""
    enabled: bool = False
    token: str = ""  # Bot token from @BotFather
    allow_from: list[str] = Field(default_factory=list)  # Allowed user IDs or usernames
    proxy: str | None = None  # HTTP/SOCKS5 proxy URL


class ChannelsConfig(BaseModel):
    """Configuration for chat channels."""
    model_config = ConfigDict(extra="ignore")

    telegram: TelegramConfig = Field(default_factory=TelegramConfig)


class AgentDefaults(BaseModel):
    """Default agent configuration."""
    workspace: str = "~/.nanobot/workspace"
    model: str = "anthropic/claude-opus-4-5"
    max_tokens: int = 8192
    temperature: float = 0.7
    max_tool_iterations: int = 20


class AgentsConfig(BaseModel):
    """Agent configuration."""
    defaults: AgentDefaults = Field(default_factory=AgentDefaults)


class ProviderConfig(BaseModel):
    """LLM provider configuration."""
    api_key: str = ""
    api_base: str | None = None


class ProvidersConfig(BaseModel):
    """Configuration for LLM providers."""
    model_config = ConfigDict(extra="ignore")

    openrouter: ProviderConfig = Field(default_factory=ProviderConfig)
    vllm: ProviderConfig = Field(default_factory=ProviderConfig)
    moonshot: ProviderConfig = Field(default_factory=ProviderConfig)


class WebSearchConfig(BaseModel):
    """Web search tool configuration."""
    api_key: str = ""  # Brave Search API key
    max_results: int = 5


class WebToolsConfig(BaseModel):
    """Web tools configuration."""
    search: WebSearchConfig = Field(default_factory=WebSearchConfig)


class ExecToolConfig(BaseModel):
    """Shell exec tool configuration."""
    timeout: int = 60


class ToolsConfig(BaseModel):
    """Tools configuration."""
    web: WebToolsConfig = Field(default_factory=WebToolsConfig)
    exec: ExecToolConfig = Field(default_factory=ExecToolConfig)
    restrict_to_workspace: bool = False  # If true, restrict all tool access to workspace directory


class Config(BaseSettings):
    """Root configuration for nanobot."""
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    channels: ChannelsConfig = Field(default_factory=ChannelsConfig)
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)

    @property
    def workspace_path(self) -> Path:
        """Get expanded workspace path."""
        return Path(self.agents.defaults.workspace).expanduser()

    def _match_provider(self, model: str | None = None) -> ProviderConfig | None:
        """Match a provider based on model name or configured api_base."""
        model = (model or self.agents.defaults.model).lower()
        providers = {
            "openrouter": self.providers.openrouter,
            "moonshot": self.providers.moonshot,
            "kimi": self.providers.moonshot,
        }
        for keyword, provider in providers.items():
            if keyword in model and provider.api_key:
                return provider
        # vLLM: match if api_base is configured (model name usually won't contain "vllm")
        if self.providers.vllm.api_base and self.providers.vllm.api_key:
            return self.providers.vllm
        return None

    def get_api_key(self, model: str | None = None) -> str | None:
        """Get API key for the given model (or default model). Falls back to first available key."""
        matched = self._match_provider(model)
        if matched:
            return matched.api_key
        for provider in [
            self.providers.openrouter,
            self.providers.moonshot,
            self.providers.vllm,
        ]:
            if provider.api_key:
                return provider.api_key
        return None

    def get_api_base(self, model: str | None = None) -> str | None:
        """Get API base URL based on model name or configured provider."""
        model = (model or self.agents.defaults.model).lower()
        if "openrouter" in model:
            return self.providers.openrouter.api_base or "https://openrouter.ai/api/v1"
        # vLLM: return api_base if configured (model name usually won't contain "vllm")
        if self.providers.vllm.api_base:
            return self.providers.vllm.api_base
        return None

    class Config:
        env_prefix = "NANOBOT_"
        env_nested_delimiter = "__"

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class InboundProtocol(Enum):
    SOCKS = "socks"
    HTTP = "http"


class OutboundProtocol(Enum):
    VLESS = "vless"


class LogLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class InboundConfig:
    """Configuration for an inbound listener.

    Attributes:
        port: TCP port to listen on (1025-65534).
        protocol: The inbound protocol (InboundProtocol.SOCKS or InboundProtocol.HTTP).
        listen: Address to bind the listener to (e.g., "127.0.0.1").
        settings: Protocol-specific settings dictionary.
    """

    port: int = 1080
    protocol: InboundProtocol = InboundProtocol.SOCKS
    listen: str = "127.0.0.1"
    settings: Dict[str, Any] = {}

    def __post_init__(self):
        """Validate the port after initialization.

        Raises:
            ValueError: If the configured port is outside the allowed range.
        """
        if not (1024 < self.port < 65535):
            raise ValueError("Port must be between 1025 and 65534")


@dataclass
class OutboundConfig:
    """Configuration for an outbound connection.

    Attributes:
        protocol: The outbound protocol (e.g., OutboundProtocol.VLESS).
        settings: Protocol-specific configuration dictionary.
        stream_settings: Optional transport-level settings, such as TLS options.
    """

    protocol: OutboundProtocol
    settings: Dict[str, Any]
    stream_settings: Optional[Dict[str, Any]] = None


class ClientConfig:
    """Builder for client configuration.

    Collects inbound and outbound configurations and produces the final
    configuration dictionary used by the application.
    """

    def __init__(
        self,
        config_path: str = "config.json",
    ):
        """Initialize a ClientConfig instance.

        Args:
            config_path: Optional path to the configuration file
        """
        self.config_path = Path(config_path)
        self.inbound_configs: List[InboundConfig] = []
        self.outbound_configs: List[OutboundConfig] = []
        self.log_level: LogLevel = LogLevel.WARNING

    def set_log_level(self, log_level: Union[LogLevel, str]) -> "ClientConfig":
        """Set the global log level for the built configuration.

        Args:
            log_level: The log level as a LogLevel enum or a string (e.g., "warning", "info").

        Returns:
            The current ClientConfig instance (for chaining).

        Raises:
            ValueError: If an unknown log level string is provided.
        """
        if isinstance(log_level, str):
            try:
                log_level = LogLevel(log_level)
            except ValueError:
                raise ValueError(f"Unknown log level: {log_level}")
        self.log_level = log_level
        return self

    def add_inbound(self, inbound_config: InboundConfig) -> "ClientConfig":
        """Add a single inbound configuration and populate protocol defaults.

        The method applies sensible default `settings` for supported protocols
        (SOCKS and HTTP) and appends the configuration to `inbound_configs`.

        Args:
            inbound_config: The inbound configuration to validate and add.

        Returns:
            The current ClientConfig instance (for method chaining).

        Raises:
            ValueError: If `inbound_config` contains invalid values.
        """
        if inbound_config.protocol == InboundProtocol.SOCKS:
            inbound_config.settings.update(
                {
                    "auth": "noauth",
                    "udp": True,
                    "ip": inbound_config.listen,
                }
            )
        elif inbound_config.protocol == InboundProtocol.HTTP:
            inbound_config.settings.update(
                {
                    "timeout": 0,
                    "allowTransparent": False,
                }
            )

        self.inbound_configs.append(inbound_config)

        return self

    def add_inbounds(self, inbound_configs: List[InboundConfig]) -> "ClientConfig":
        """Add multiple inbound configurations.

        Args:
            inbound_configs: Iterable of InboundConfig instances to add.

        Returns:
            The current ClientConfig instance.
        """
        for inbound_config in inbound_configs:
            self.add_inbound(inbound_config)
        return self

    def add_vless_outbound(
        self,
        address: str,
        port: int,
        uuid: str,
        flow: str = "xtls-rprx-vision",
        security: str = "none",
    ) -> "ClientConfig":
        """Create and append a VLESS outbound configuration.

        Args:
            address: Remote address of the VLESS server.
            port: Remote TCP port (1025-65535).
            uuid: User UUID for authentication.
            flow: Optional flow parameter for VLESS users.
            security: Transport security mode; if "tls", TLS settings are added.

        Returns:
            The current ClientConfig instance.

        Raises:
            ValueError: If provided arguments are invalid (e.g., port out of range).
        """
        outbound_config = OutboundConfig(
            protocol=OutboundProtocol.VLESS,
            settings={
                "vnext": [
                    {
                        "address": address,
                        "port": port,
                        "users": [{"id": uuid, "flow": flow, "encryption": security}],
                    }
                ]
            },
        )

        if security == "tls":
            outbound_config.stream_settings = {
                "network": "tcp",
                "security": "tls",
                "tlsSettings": {
                    "allowInsecure": False,
                    "serverName": address,
                },
            }

        self.outbound_configs.append(outbound_config)

        return self

    def validate(self):
        """Validate the current configuration.

        Raises:
            ValueError: If there are no inbounds or no outbounds defined.
        """
        if not self.inbound_configs:
            raise ValueError("Inbound configuration is not set")
        if not self.outbound_configs:
            raise ValueError("Outbound configuration is not set")

    def build_config(self) -> Dict[str, Any]:
        """Assemble and return the final configuration dictionary.

        The returned dictionary follows the expected structure for the
        consuming application and includes `log`, `inbounds`, `outbounds`, and
        `routing` sections.

        Returns:
            A dict representing the full configuration.

        Raises:
            ValueError: If there are no inbounds or no outbounds defined.
        """
        self.validate()
        config: Dict[str, Any] = {
            "log": {"loglevel": self.log_level.value},
            "inbounds": [],
            "outbounds": [],
            "routing": {
                "domainStrategy": "IPIfNonMatch",
                "rules": [
                    {"type": "field", "outboundTag": "direct", "ip": ["geoip:private"]}
                ],
            },
        }

        for inbound in self.inbound_configs:
            config["inbounds"].append(
                {
                    "port": inbound.port,
                    "listen": inbound.listen,
                    "protocol": inbound.protocol.value,
                    "settings": inbound.settings,
                }
            )

        for outbound in self.outbound_configs:
            outbound_dict: Dict[str, Any] = {
                "protocol": outbound.protocol.value,
                "settings": outbound.settings,
            }
            if outbound.stream_settings:
                outbound_dict["streamSettings"] = outbound.stream_settings
            config["outbounds"].append(outbound_dict)

        return config

    def save(self):
        """Save the built configuration to the specified file path."""
        config_dict = self.build_config()
        with self.config_path.open("w", encoding="utf-8") as f:
            json.dump(config_dict, f, indent=4)

    def load(self) -> Dict[str, Any]:
        """Load configuration from the specified file path.

        Returns:
            A dict representing the loaded configuration."""
        with self.config_path.open("r", encoding="utf-8") as f:
            config_dict = json.load(f)
        return config_dict

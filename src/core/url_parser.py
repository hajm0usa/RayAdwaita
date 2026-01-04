import urllib.parse
from typing import Dict


class V2rayParser:

    def __init__(self):
        pass

    @staticmethod
    def parse(url: str):
        url = url.strip()

        if url.startswith("vless://"):
            return V2rayParser._parse_vless(url)

        return None

    @staticmethod
    def _parse_vless(url: str) -> Dict:

        url = url.replace("vless://", "")

        if "#" in url:
            url, remarks = url.split("#", 1)
            remarks = urllib.parse.unquote(remarks)
        else:
            remarks = "VLESS"

        if "?" in url:
            server_part, params_part = url.split("?", 1)
            params = dict(urllib.parse.parse_qsl(params_part))
        else:
            server_part = url
            params = {}

        uuid, server_and_port = server_part.split("@", 1)
        server, port = server_and_port.rsplit(":", 1)
        port = int(port)

        config = {
            "name": remarks,
            "protocol": "vless",
            "serverr": server,
            "port": port,
            "uuid": uuid,
            "enctyption": params.get("enctyption", "none"),
            "flow": params.get("flow", ""),
            "network": params.get("network", "tcp"),
            "security": params.get("security", "none"),
        }

        if config["network"] == "tcp":
            config["tcp"] = {"header_type": params.get("headerType", "none")}
        elif config["network"] == "ws":
            config["ws"] = {"path": params.get("path", "/"), "host": params.get("host")}
        elif config["network"] == "grpc":
            config["grpc"] = {"service_name": params.get("serviceName", "")}

        if config["security"] in ["tls", "reality"]:
            config["tls"] = {
                "server_name": params.get("sni", server),
                "fingerprint": params.get("fp", "chrome"),
                "alpn": params.get("alpn", "").split(",") if params.get("alpn") else [],
            }

            if config["security"] == "reality":
                config["reality"] = {
                    "public_key": params.get("pbk", ""),
                    "short_id": params.get("sid", ""),
                    "spider_x": params.get("spx", ""),
                }

        return config

    @staticmethod
    def _build_vless(config: Dict):
        outbound = {
            "protocol": "vless",
            "settings": {
                "vnext": [
                    {
                        "address": config["server"],
                        "port": config["port"],
                        "users": [
                            {
                                "id": config["uuid"],
                                "encryption": config["encryption"],
                                "flow": config.get("flow", ""),
                            }
                        ],
                    }
                ]
            },
            "streamSettings": {
                "network": config["network"],
                "security": config["security"],
            },
        }

        if config["network"] == "tcp":
            outbound["streamSettings"]["tcpSettings"] = {
                "header": {"type": config.get("tcp", {}).get("header_type", "none")}
            }
        elif config["network"] == "ws":
            ws_config = config.get("ws", {})
            outbound["streamSettings"]["wsSettings"] = {
                "path": ws_config.get("path", "/"),
                "headers": (
                    {"Host": ws_config.get("host", "")} if ws_config.get("host") else {}
                ),
            }
        elif config["network"] == "grpc":
            grpc_config = config.get("grpc", {})
            outbound["streamSettings"]["grpcSettings"] = {
                "serviceName": grpc_config.get("service_name", "")
            }

        if config["security"] in ["tls", "reality"]:
            tls_config = config.get("tls", {})

            if config["security"] == "tls":
                outbound["streamSettings"]["tlsSettings"] = {
                    "serverName": tls_config.get("server_name", config["server"]),
                    "fingerprint": tls_config.get("fingerprint", "chrome"),
                    "alpn": tls_config.get("alpn", []),
                }
            elif config["security"] == "reality":
                reality_config = config.get("reality", {})
                outbound["streamSettings"]["realitySettings"] = {
                    "serverName": tls_config.get("server_name", config["server"]),
                    "fingerprint": tls_config.get("fingerprint", "chrome"),
                    "publicKey": reality_config.get("public_key", ""),
                    "shortId": reality_config.get("short_id", ""),
                    "spiderX": reality_config.get("spider_x", ""),
                }

        return outbound

    @staticmethod
    def build_config(parsed_config: Dict, inbound_port: int = 1080) -> Dict:

        protocol = parsed_config["protocol"]

        if protocol == "vless":
            outbound = V2rayParser._build_vless(parsed_config)

        return {
            "log": {"loglevel": "warning"},
            "inbounds": [
                {
                    "port": inbound_port,
                    "protocol": "socks",
                    "settings": {"auth": "noauth", "udp": True},
                    "sniffing": {"enabled": True, "destOverride": ["http", "tls"]},
                }
            ],
            "outbounds": [
                outbound,
                {"protocol": "freedom", "tag": "direct"},
                {"protocol": "blackhole", "tag": "block"},
            ],
            "routing": {
                "rules": [
                    {"type": "field", "ip": ["geoip:private"], "outboundTag": "direct"}
                ]
            },
        }

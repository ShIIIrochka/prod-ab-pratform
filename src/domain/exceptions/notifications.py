from dataclasses import dataclass


@dataclass
class ChannelConfigNotFoundError(Exception):
    message: str = "Channel config not found"

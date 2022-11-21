from dataclasses import dataclass, field
from abc import ABC
from datetime import date
from common.const import Status


# @dataclass
class BaseInfo(ABC):
    """Base Info about anime"""
    name: str
    jp_name: str
    mal_score: str
    status: Status
    aired: date
    episodes: str
    discription: str
    genres: list
    is_for_adult: bool
    url_link: str


class Season(BaseInfo):
    """Anime Season Info"""
    name: str
    link: str

    def __init__(self, name: str, link: str) -> None:
        self.name = name
        self.url_link = link

    def __str__(self) -> str:
        return f'"Name":{self.name},"Link":{self.link}'


class Anime(BaseInfo):
    """Anime Info"""
    seasons: list[Season]

    def __init__(self, seasons=None) -> None:
        self.seasons = seasons

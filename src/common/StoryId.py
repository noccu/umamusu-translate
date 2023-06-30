from dataclasses import dataclass, astuple, asdict
from pathlib import Path

@dataclass
class StoryId:
    type: str = "story"
    set: str = None
    setLen = 5
    group: str = None
    groupLen = 2
    id: str = None
    idLen = 4
    idx: str = None
    idxLen = 3
    idOnlyGroup = ("lyrics", "preview")

    def __post_init__(self):
        if self.type in self.idOnlyGroup:
            if not self.id and self.idx:
                self.id = self.idx
            self.idx = None
            self.group = None
            self.set = None

    def __str__(self) -> str:
        """Return the joined numeric parts, as written in tlFiles"""
        return "".join(x for x in astuple(self)[1:] if x is not None)

    @classmethod
    def parse(cls, text_type, s):
        if text_type in cls.idOnlyGroup:
            return cls(type=text_type, id=s)
        elif len(s) > 9 and text_type == "home":
            return cls(type=text_type, set=s[:5], group=s[5:7], id=s[7:11], idx=s[11:])
        else:
            return cls(type=text_type, group=s[:2], id=s[2:6], idx=s[6:])

    @classmethod
    def parseFromPath(cls, text_type: str, path: str):
        """Given a text type (story, lyrics, etc.) and a game data filepath,
        extract and return the group, id, and index."""
        if text_type == "home":
            path = path[-16:]
            return cls(
                type=text_type,
                set=path[:5],
                group=path[6:8],
                id=path[9:13],
                idx=path[13:],
            )
        elif text_type == "lyrics":
            return cls(type=text_type, id=path[-11:-7])
        elif text_type == "preview":
            return cls(type=text_type, id=path[-4:])
        else:  # story and storyrace
            path = path[-9:]
            return cls(type=text_type, group=path[:2], id=path[2:6], idx=path[6:9])

    @classmethod
    def queryfy(cls, storyId: "StoryId"):
        """Returns a new StoryId with attributes usable in SQL"""
        parts = asdict(storyId)
        for k, v in parts.items():
            if v is None:
                parts[k] = "_" * getattr(storyId, f"{k}Len", 0)
        return cls(*parts.values())

    @classmethod
    def fromLegacy(cls, group, id, idx):
        return cls(group=group, id=id, idx=idx)

    def asLegacy(self):
        return self.group, self.id, self.idx

    def asTuple(self, validOnly=False):
        if validOnly:
            # Faster with the list comp for some extra mem cost, apparently
            return tuple([x for x in astuple(self) if x is not None])
        else:
            return astuple(self)

    def asPath(self, includeIdx=False):
        offset = None if includeIdx else -1
        return Path().joinpath(*self.asTuple(validOnly=True)[1:offset])  # ignore type for now

    def getFilenameIdx(self):
        if self.type in self.idOnlyGroup:
            return self.id
        elif self.idx:
            return self.idx
        else:
            raise AttributeError

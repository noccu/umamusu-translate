import os
from pathlib import Path, PurePath

import UnityPy
from UnityPy.files import ObjectReader

from ..constants import GAME_ASSET_ROOT
from . import TranslationFile


class GameBundle:
    editMark = b"\x08\x04"

    def __init__(self, path, load=True, bType="story") -> None:
        self.bundlePath = Path(path)
        self.bundleName = self.bundlePath.stem
        self.bundleType = bType
        self.exists = self.bundlePath.exists()
        self.data = None
        self.patchData: bytes = b""
        self._autoloaded = load
        self._patchedState = None
        self.patchedTime = None

        if load:
            self.load()

    def markPatched(self, tlFile: TranslationFile):
        m = tlFile.data.get("modified", b"")
        if m:
            m = m.to_bytes(5, byteorder="big", signed=False)
            # Have a nice day and good training if you're reading this in the year 15xxx somewhere :spemini:
        self.patchData = m + self.editMark

    @property
    def isPatched(self):
        return self.readPatchState()

    @isPatched.setter
    def isPatched(self, v):
        self._patchedState = v

    def readPatchState(self, customPath=None):
        if not customPath and self._patchedState is not None:
            return self._patchedState
        try:
            with open(customPath or self.bundlePath, "rb") as f:
                f.seek(-7, os.SEEK_END)
                modified = f.read(5)
                mark = f.read(2)
                if mark == self.editMark:
                    self._patchedState = True
                    # Exception handling removed as I don't see how it would except
                    # The actual issue is it could not be a timestamp... todo?
                    modified = int.from_bytes(modified, byteorder="big")
                    self.patchedTime = modified
                else:
                    self._patchedState = False
        except Exception:
            self._patchedState = False
        return self._patchedState

    def getAssetData(self, pathId: int):
        if a := self.assets.get(pathId):
            return a.read_typetree()
        else:
            return None

    def load(self):
        # UnityPy does not error and loads empty files
        if not self.exists:
            raise FileNotFoundError

        self.data = UnityPy.load(str(self.bundlePath))
        if self._autoloaded:
            self.readPatchState()
        self.rootAsset: ObjectReader = next(iter(self.data.container.values())).get_obj()
        self.assets: dict[str, ObjectReader] = self.rootAsset.assets_file.files
        return self

    def save(self, dstFolder: Path = None, dstName: str = None):
        if not self.data:
            return

        b = self.data.file.save() + self.patchData
        fn = dstName or self.data.file.name
        fp = ((dstFolder / fn[0:2]) if dstFolder else self.bundlePath.parent) / fn
        fp.parent.mkdir(parents=True, exist_ok=True)
        with open(fp, "wb") as f:
            f.write(b)
        self.isPatched = True

    @classmethod
    def fromName(cls, name, **kwargs):
        """Create a bundle by hash/name from the default game dir. kwargs passed to constructor"""
        bundlePath = PurePath(GAME_ASSET_ROOT, name[0:2], name)
        return cls(bundlePath, **kwargs)

    @staticmethod
    def createPath(dstFolder, dstName):
        return PurePath(dstFolder, dstName[0:2], dstName)

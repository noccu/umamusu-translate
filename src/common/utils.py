from datetime import datetime, timezone

import regex


def isParseableInt(x):
    try:
        int(x)
        return True
    except ValueError:
        return False


def isJapanese(text):
    # Should be cached according to docs
    return regex.search(
        r"[\p{scx=Katakana}\p{scx=Hiragana}\p{Han}\p{InHalfwidth_and_Fullwidth_Forms}\p{General_Punctuation}]{3,}",
        text,
    )


def isEnglish(text):
    return regex.fullmatch(
        r"[^\p{scx=Katakana}\p{scx=Hiragana}\p{Han}\p{InHalfwidth_and_Fullwidth_Forms}。]+",
        text,
    )


def currentTimestamp():
    return int(datetime.now(timezone.utc).timestamp())


def timestampToDate(ts):
    return datetime.fromtimestamp(ts)

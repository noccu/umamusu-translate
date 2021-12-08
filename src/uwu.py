# Based on code by Marcy Brook https://mxmbrook.co.uk/tools/uwu
# He is vewy sowwy

import re

replacements = [
    (r"[rl]", "w"),
    (r"youw", "ur"),
    (r"you", "u"),
    (r"awe(?![a-z])", "r"),
    (r"ove", "uv"),
    (r"(n)([aeiou])", r"\1y\2")
]

def uwuify(text: str):
    for pat, rep in replacements:
        text = re.sub(pat, rep, text)
    return text

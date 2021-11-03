import os
def searchFiles(IMPORT_GROUP, IMPORT_ID):
    found = list()
    for root, dirs, files in os.walk("translations/"):
        depth = len(dirs[0]) if dirs else 3
        if IMPORT_GROUP and depth == 2:
            dirs[:] = [d for d in dirs if d == IMPORT_GROUP]
        elif IMPORT_ID and depth == 4:
            dirs[:] = [d for d in dirs if d == IMPORT_ID]
        found.extend(os.path.join(root, file) for file in files)
    return found
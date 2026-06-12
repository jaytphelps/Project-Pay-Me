import hashlib

def hash_lines(lines):
    hasher = hashlib.sha256()
    for line in lines:
        hasher.update(line.encode())
    return hasher.hexdigest()
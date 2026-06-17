from __future__ import annotations

def tokenize_source(source: str) -> list[str]:
    lines = source.split("\n")
    tokens: list[str] = []

    for line in lines:
        comment_pos = line.find("\\")
        if comment_pos != -1:
            line = line[:comment_pos]

        line = line.replace('s"', ' s" ').replace('S"', ' s" ')
        line_tokens = line.strip().split()

        processed_tokens: list[str] = []
        in_string = False
        for token in line_tokens:
            if token.lower() == 's"':
                processed_tokens.append('S"')
                in_string = True
            elif in_string and token.endswith('"'):
                processed_tokens.append(token[:-1])
                processed_tokens.append('"')
                in_string = False
            elif in_string:
                processed_tokens.append(token)
            else:
                processed_tokens.append(token.upper())

        tokens.extend(processed_tokens)

    return [token for token in tokens if token]

def parseArgs(str):
    args = []
    capturing = 0
    start = 0

    pos = 0
    for c in str:
        if c == "'":
            if not capturing:
                capturing = 1
                start = pos + 1
            else:
                capturing = 0
                args.append(str[start:pos])

        pos +=1

    return args
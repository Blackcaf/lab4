s" What is your name?" TYPE CR

s" Hello, " TYPE

BEGIN
    KEY DUP
    10 <>
WHILE
    DUP EMIT
REPEAT

2DROP

s" !" TYPE
HALT

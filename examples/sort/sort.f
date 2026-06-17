CREATE NUMBERS ALLOT 51
VARIABLE I_VAR
VARIABLE J_VAR
VARIABLE V_J
VARIABLE V_J1

: CR 10 EMIT ;
: DIGIT>CHAR 48 + ;
: U.SIMPLE DUP 10 < IF DIGIT>CHAR EMIT ELSE 10 /MOD SWAP U.SIMPLE DIGIT>CHAR EMIT THEN ;
: PRINT-NUMBER U.SIMPLE 32 EMIT ;

VARIABLE PARSE_ACCUM

: PARSE-INT
    0 PARSE_ACCUM !
    BEGIN
        KEY DUP 48 <
    WHILE
        DROP
        KEY DUP 48 <
    REPEAT

    BEGIN
        DUP 48 >= OVER 57 <= AND
    WHILE
        48 -
        PARSE_ACCUM @ 10 * +
        PARSE_ACCUM !
        KEY
    REPEAT
    DROP
    PARSE_ACCUM @
;

: READ_ARRAY
    PARSE-INT NUMBERS !
    0 I_VAR !
    BEGIN
        I_VAR @ NUMBERS @ <
    WHILE
        NUMBERS I_VAR @ 4 * 4 + +
        PARSE-INT SWAP !
        I_VAR @ 1+ I_VAR !
    REPEAT
;

: PRINT_ARRAY
    0 I_VAR !
    BEGIN
        I_VAR @ NUMBERS @ <
    WHILE
        NUMBERS I_VAR @ 4 * 4 + + @ PRINT-NUMBER
        I_VAR @ 1+ I_VAR !
    REPEAT
    CR
;

: BUBBLE_SORT
    0 I_VAR !
    BEGIN
        I_VAR @ NUMBERS @ 1- <
    WHILE
        0 J_VAR !
        BEGIN
            J_VAR @ NUMBERS @ I_VAR @ - 1- <
        WHILE
            NUMBERS J_VAR @ 4 * 4 + + @  V_J !
            NUMBERS J_VAR @ 4 * 4 + + 4 + @  V_J1 !

            V_J @ V_J1 @ > IF
                V_J1 @  NUMBERS J_VAR @ 4 * 4 + + !
                V_J @   NUMBERS J_VAR @ 4 * 4 + + 4 + !
            THEN
            J_VAR @ 1+ J_VAR !
        REPEAT
        I_VAR @ 1+ I_VAR !
    REPEAT
;

READ_ARRAY
BUBBLE_SORT
PRINT_ARRAY
HALT

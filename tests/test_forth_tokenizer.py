from core.forth_tokenizer import tokenize_source

def test_tokenizer_strips_comments_and_uppercases_tokens():
    source = "1 dup \\ comment\n2 swap"
    tokens = tokenize_source(source)
    assert tokens == ["1", "DUP", "2", "SWAP"]

def test_tokenizer_keeps_string_content_case():
    source = 's" HeLLo World" TYPE'
    tokens = tokenize_source(source)
    assert tokens == ['S"', "HeLLo", "World", '"', "TYPE"]

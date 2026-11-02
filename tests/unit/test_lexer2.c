
#include <stdio.h>
#include <stddef.h>

#include "aster/lexer.h"

typedef struct {
    TokenType type;
    size_t start;
    size_t length;
} ExpectedToken;


static int test_tokens(
    const char *name,
    const char *source,
    const ExpectedToken expected[],
    size_t expected_count,
    int expect_eof
) {
    Lexer lexer;
    lexer_init(&lexer, source);

    for (size_t i = 0; i < expected_count; i++) {
        Token token = lexer_next_token(&lexer);

        if (token.type != expected[i].type) {
            printf("[FAIL] %s: token %zu, expected type %d, got %d\n",
                   name, i, expected[i].type, token.type);
            return 0;
        }

        if (token.start != expected[i].start ||
            token.length != expected[i].length) {
            printf("[FAIL] %s: token %zu, position mismatch "
                   "(expected %zu:%zu, got %zu:%zu)\n",
                   name, i,
                   expected[i].start, expected[i].length,
                   token.start, token.length);
            return 0;
        }
    }

    if (expect_eof) {
        Token token = lexer_next_token(&lexer);

        if (token.type != TOKEN_EOF) {
            printf("[FAIL] %s: expected EOF, got %d\n",
                   name, token.type);
            return 0;
        }
    }

    printf("[PASS] %s\n", name);
    return 1;
}


typedef struct {
    TokenType type;
    size_t start;
    size_t length;
    size_t line;
    size_t column;
} ExpectedPosition;


static int test_positions(
    const char *name,
    const char *source,
    const ExpectedPosition expected[],
    size_t expected_count
) {
    Lexer lexer;
    lexer_init(&lexer, source);

    for (size_t i = 0; i < expected_count; i++) {
        Token token = lexer_next_token(&lexer);

        if (token.type != expected[i].type ||
            token.start != expected[i].start ||
            token.length != expected[i].length ||
            token.line != expected[i].line ||
            token.column != expected[i].column) {

            printf("[FAIL] %s: token %zu\n", name, i);
            printf("  Expected: type=%d, start=%zu, length=%zu, "
                   "line=%zu, column=%zu\n",
                   expected[i].type,
                   expected[i].start,
                   expected[i].length,
                   expected[i].line,
                   expected[i].column);

            printf("  Got:      type=%d, start=%zu, length=%zu, "
                   "line=%zu, column=%zu\n",
                   token.type,
                   token.start,
                   token.length,
                   token.line,
                   token.column);

            return 0;
        }
    }

    printf("[PASS] %s\n", name);
    return 1;
}


static int test_error_recovery(void)
{
    const char *name = "Error recovery";

    Lexer lexer;
    lexer_init(&lexer, "@ int");

    Token error = lexer_next_token(&lexer);

    if (error.type != TOKEN_ERROR ||
        error.start != 0 ||
        error.length != 1) {
        printf("[FAIL] %s: invalid token was not detected\n", name);
        return 0;
    }

    Token next = lexer_next_token(&lexer);

    if (next.type != TOKEN_INT ||
        next.start != 2 ||
        next.length != 3) {
        printf("[FAIL] %s: lexer failed to continue after error\n", name);
        return 0;
    }

    Token eof = lexer_next_token(&lexer);

    if (eof.type != TOKEN_EOF) {
        printf("[FAIL] %s: expected EOF\n", name);
        return 0;
    }

    printf("[PASS] %s\n", name);
    return 1;
}


int main(void)
{
    int passed = 0;
    int total = 0;

    /* Basic tokens */
    const ExpectedToken basic[] = {
        {TOKEN_INT,        0, 3},
        {TOKEN_IDENTIFIER, 4, 3},
        {TOKEN_EQUAL,      8, 1},
        {TOKEN_INTEGER,   10, 2},
        {TOKEN_SEMICOLON, 12, 1}
    };

    total++;
    passed += test_tokens(
        "Basic tokens",
        "int age = 16;",
        basic,
        sizeof(basic) / sizeof(basic[0]),
        1
    );

    /* Number literals */
    const ExpectedToken numbers[] = {
        {TOKEN_INTEGER,       0, 3},
        {TOKEN_FLOAT_LITERAL, 4, 4},
        {TOKEN_FLOAT_LITERAL, 9, 3}
    };

    total++;
    passed += test_tokens(
        "Number literals",
        "123 3.14 1e3",
        numbers,
        sizeof(numbers) / sizeof(numbers[0]),
        1
    );

    /* Operators */
    const ExpectedToken operators[] = {
        {TOKEN_EQUAL,          0, 1},
        {TOKEN_EQUAL_EQUAL,    2, 2},
        {TOKEN_BANG_EQUAL,     5, 2},
        {TOKEN_LESS,           8, 1},
        {TOKEN_LESS_EQUAL,    10, 2},
        {TOKEN_GREATER,       13, 1},
        {TOKEN_GREATER_EQUAL, 15, 2}
    };

    total++;
    passed += test_tokens(
        "All comparison operators",
        "= == != < <= > >=",
        operators,
        sizeof(operators) / sizeof(operators[0]),
        1
    );

    /* Arithmetic operators */
    const ExpectedToken arithmetic[] = {
        {TOKEN_PLUS,    0, 1},
        {TOKEN_MINUS,   2, 1},
        {TOKEN_STAR,    4, 1},
        {TOKEN_SLASH,   6, 1},
        {TOKEN_PERCENT, 8, 1}
    };

    total++;
    passed += test_tokens(
        "Arithmetic operators",
        "+ - * / %",
        arithmetic,
        sizeof(arithmetic) / sizeof(arithmetic[0]),
        1
    );

    /* Consecutive operators */
    const ExpectedToken consecutive[] = {
        {TOKEN_EQUAL_EQUAL, 0, 2},
        {TOKEN_EQUAL,       2, 1}
    };

    total++;
    passed += test_tokens(
        "Consecutive operators",
        "===",
        consecutive,
        sizeof(consecutive) / sizeof(consecutive[0]),
        1
    );

    /* String with escape */
    const ExpectedToken string[] = {
        {TOKEN_STRING, 0, 14}
    };

    total++;
    passed += test_tokens(
        "String with escape",
        "\"Hello\\nWorld\"",
        string,
        sizeof(string) / sizeof(string[0]),
        1
    );

    /* Hex escape */
    const ExpectedToken hex_string[] = {
        {TOKEN_STRING, 0, 6}
    };

    total++;
    passed += test_tokens(
        "Hex escape",
        "\"\\x41\"",
        hex_string,
        sizeof(hex_string) / sizeof(hex_string[0]),
        1
    );

    /* Invalid escape */
    const ExpectedToken invalid_escape[] = {
        {TOKEN_ERROR, 0, 3}
    };

    total++;
    passed += test_tokens(
        "Invalid escape",
        "\"\\q\"",
        invalid_escape,
        sizeof(invalid_escape) / sizeof(invalid_escape[0]),
        0
    );

    /* Invalid exponent */
    const ExpectedToken invalid_exponent[] = {
        {TOKEN_ERROR, 0, 3}
    };

    total++;
    passed += test_tokens(
        "Invalid exponent",
        "1e+",
        invalid_exponent,
        sizeof(invalid_exponent) / sizeof(invalid_exponent[0]),
        1
    );

    /* Standalone exclamation mark */
    const ExpectedToken invalid_operator[] = {
        {TOKEN_ERROR, 0, 1}
    };

    total++;
    passed += test_tokens(
        "Invalid operator",
        "!",
        invalid_operator,
        sizeof(invalid_operator) / sizeof(invalid_operator[0]),
        1
    );

    /* Unterminated string */
    const ExpectedToken unterminated_string[] = {
        {TOKEN_ERROR, 0, 6}
    };

    total++;
    passed += test_tokens(
        "Unterminated string",
        "\"Hello",
        unterminated_string,
        sizeof(unterminated_string) / sizeof(unterminated_string[0]),
        1
    );

    /* Invalid hexadecimal escape */
    const ExpectedToken invalid_hex[] = {
        {TOKEN_ERROR, 0, 3}
    };

    total++;
    passed += test_tokens(
        "Invalid hex escape",
        "\"\\xGG\"",
        invalid_hex,
        sizeof(invalid_hex) / sizeof(invalid_hex[0]),
        0
    );

    /* Invalid Unicode code point */
    const ExpectedToken invalid_unicode[] = {
        {TOKEN_ERROR, 0, 11}
    };

    total++;
    passed += test_tokens(
        "Invalid Unicode escape",
        "\"\\U00110000\"",
        invalid_unicode,
        sizeof(invalid_unicode) / sizeof(invalid_unicode[0]),
        0
    );

    /* Empty string */
    const ExpectedToken empty_string[] = {
        {TOKEN_STRING, 0, 2}
    };

    total++;
    passed += test_tokens(
        "Empty string",
        "\"\"",
        empty_string,
        sizeof(empty_string) / sizeof(empty_string[0]),
        1
    );

    /* Multiple whitespace */
    const ExpectedToken whitespace[] = {
        {TOKEN_INT,        0, 3},
        {TOKEN_IDENTIFIER, 7, 3}
    };

    total++;
    passed += test_tokens(
        "Multiple whitespace",
        "int    age",
        whitespace,
        sizeof(whitespace) / sizeof(whitespace[0]),
        1
    );


    /* LF line ending */
    const ExpectedPosition lf_positions[] = {
        {TOKEN_INT,        0, 3, 1, 1},
        {TOKEN_IDENTIFIER, 6, 3, 2, 3}
    };

    total++;
    passed += test_positions(
        "LF line positions",
        "int\n  age",
        lf_positions,
        sizeof(lf_positions) / sizeof(lf_positions[0])
    );

    /* CRLF line ending */
    const ExpectedPosition crlf_positions[] = {
        {TOKEN_INT,        0, 3, 1, 1},
        {TOKEN_IDENTIFIER, 5, 3, 2, 1}
    };

    total++;
    passed += test_positions(
        "CRLF line positions",
        "int\r\nage",
        crlf_positions,
        sizeof(crlf_positions) / sizeof(crlf_positions[0])
    );

    /* Error recovery */
    total++;
    passed += test_error_recovery();


    printf("\nResults: %d/%d passed\n", passed, total);

    return passed == total ? 0 : 1;
}

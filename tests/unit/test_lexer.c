
#include <stdio.h>
#include <string.h>
#include <assert.h>

#include "aster/lexer.h"

static void assert_token(
    Token token,
    TokenType expected_type,
    const char *source,
    const char *expected_text
) {
    size_t expected_length = strlen(expected_text);

    if (token.type != expected_type ||
        token.length != expected_length ||
        memcmp(source + token.start, expected_text, expected_length) != 0) {

        fprintf(stderr,
            "\n[Lexer Test Failed]\n"
            "Expected type : %d\n"
            "Actual type   : %d\n"
            "Expected text : \"%s\"\n"
            "Actual text   : \"%.*s\"\n"
            "Start         : %zu\n"
            "Length        : %zu\n"
            "Line          : %zu\n"
            "Column        : %zu\n",
            (int)expected_type,
            (int)token.type,
            expected_text,
            (int)token.length,
            source + token.start,
            token.start,
            token.length,
            token.line,
            token.column
        );

        abort();
    }
}

static void test_integer(void)
{
    const char *source = "12345";
    Lexer lexer;

    lexer_init(&lexer, source);

    Token token = lexer_next_token(&lexer);

    assert_token(token, TOKEN_INTEGER, source, "12345");
    assert(lexer_next_token(&lexer).type == TOKEN_EOF);
}

static void test_identifier(void)
{
    const char *source = "player_1";
    Lexer lexer;

    lexer_init(&lexer, source);

    Token token = lexer_next_token(&lexer);

    assert_token(token, TOKEN_IDENTIFIER, source, "player_1");
}

static void test_keyword(void)
{
    const char *source = "int integer";
    Lexer lexer;

    lexer_init(&lexer, source);

    Token token = lexer_next_token(&lexer);
    assert_token(token, TOKEN_INT, source, "int");

    token = lexer_next_token(&lexer);
    assert_token(token, TOKEN_IDENTIFIER, source, "integer");
}

static void test_operators(void)
{
    const char *source = "=;";
    Lexer lexer;

    lexer_init(&lexer, source);

    Token token = lexer_next_token(&lexer);
    assert_token(token, TOKEN_EQUAL, source, "=");

    token = lexer_next_token(&lexer);
    assert_token(token, TOKEN_SEMICOLON, source, ";");
}

static void test_whitespace(void)
{
    const char *source = "  int   age  ";
    Lexer lexer;

    lexer_init(&lexer, source);

    Token token = lexer_next_token(&lexer);
    assert_token(token, TOKEN_INT, source, "int");

    token = lexer_next_token(&lexer);
    assert_token(token, TOKEN_IDENTIFIER, source, "age");

    token = lexer_next_token(&lexer);
    assert(token.type == TOKEN_EOF);
}

static void test_error(void)
{
    const char *source = "@";
    Lexer lexer;

    lexer_init(&lexer, source);

    Token token = lexer_next_token(&lexer);

    assert_token(token, TOKEN_ERROR, source, "@");
}

static void test_empty_source(void)
{
    const char *source = "";
    Lexer lexer;

    lexer_init(&lexer, source);

    Token token = lexer_next_token(&lexer);

    assert(token.type == TOKEN_EOF);
    assert(token.length == 0);
}

static void test_complete_statement(void)
{
    const char *source = "int age = 16;";
    Lexer lexer;

    lexer_init(&lexer, source);

    Token token;

    token = lexer_next_token(&lexer);
    assert_token(token, TOKEN_INT, source, "int");

    token = lexer_next_token(&lexer);
    assert_token(token, TOKEN_IDENTIFIER, source, "age");

    token = lexer_next_token(&lexer);
    assert_token(token, TOKEN_EQUAL, source, "=");

    token = lexer_next_token(&lexer);
    assert_token(token, TOKEN_INTEGER, source, "16");

    token = lexer_next_token(&lexer);
    assert_token(token, TOKEN_SEMICOLON, source, ";");

    token = lexer_next_token(&lexer);
    assert(token.type == TOKEN_EOF);
}

static void test_error_message(void) {
    const char *source = "int age = @;";
    Lexer lexer;

    lexer_init(&lexer, source);

    Token token;

    do {
        token = lexer_next_token(&lexer);
    } while (token.type != TOKEN_ERROR &&
             token.type != TOKEN_EOF);

    assert(token.type == TOKEN_ERROR);
    assert(token.line == 1);
    assert(token.column == 11);
    assert(token.length == 1);
    assert(source[token.start] == '@');

    lexer_print_error(&lexer, &token);
}

static void test_comparison_operators(void)
{
    const char *source = "= == ! != < <= > >=";
    Lexer lexer;

    lexer_init(&lexer, source);

    struct {
        TokenType type;
        const char *text;
        size_t column;
    } expected[] = {
        {TOKEN_EQUAL, "=", 1},
        {TOKEN_EQUAL_EQUAL, "==", 3},
        {TOKEN_ERROR, "!", 6},
        {TOKEN_BANG_EQUAL, "!=", 8},
        {TOKEN_LESS, "<", 11},
        {TOKEN_LESS_EQUAL, "<=", 13},
        {TOKEN_GREATER, ">", 16},
        {TOKEN_GREATER_EQUAL, ">=", 18}
    };

    for (size_t i = 0;
         i < sizeof(expected) / sizeof(expected[0]);
         i++) {

        Token token = lexer_next_token(&lexer);
        if (token.type != expected[i].type) {
            printf(
                "Test failed at index %zu\n"
                "Expected: %d\n"
                "Actual: %d\n"
                "Source position: %zu\n"
                "Token length: %zu\n",
                i,
                expected[i].type,
                token.type,
                token.start,
                token.length
            );
        }

        assert_token(
            token,
            expected[i].type,
            source,
            expected[i].text
        );

        assert(token.line == 1);
        assert(token.column == expected[i].column);
    }

    assert(lexer_next_token(&lexer).type == TOKEN_EOF);
}

int main(void)
{
    test_integer();
    test_identifier();
    test_keyword();
    test_operators();
    test_whitespace();
    test_error();
    test_empty_source();
    test_complete_statement();
    test_error_message();
    test_comparison_operators();

    printf("All Lexer tests passed.\n");

    return 0;
}

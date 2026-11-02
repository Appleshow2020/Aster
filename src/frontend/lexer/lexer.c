#include <string.h>
#include <ctype.h>
#include <stdio.h>
#include "aster/lexer.h"
#include "lexer_internal.h"

void lexer_init(Lexer *lexer, const char *source) {
    lexer->source = source;
    lexer->length = strlen(source);
    lexer->position = 0;
    lexer->start = 0;
    lexer->line = 1;
    lexer->column = 1;
    lexer->start_line = 1;
    lexer->start_column = 1;
}
void lexer_print_error(const Lexer *lexer, const Token *token) {
    if (lexer == NULL || token == NULL || lexer->source == NULL) {
        return;
    }

    if (token->type != TOKEN_ERROR ||
        token->length == 0 || 
        token->start >= lexer->length) {
        return;
    }

    const char *line_start = lexer->source;
    size_t current_line = 1;

    while (current_line < token->line && *line_start != '\0') {
        if (*line_start == '\n') {
            current_line++;
        }
        line_start++;
    }

    const char *line_end = line_start;

    while (*line_end != '\0' && *line_end != '\n' && *line_end != '\r') {
        line_end++;
    }


    unsigned char error_char = (unsigned char)lexer->source[token->start];

     fprintf(stderr, "  File \"<aster>\", line %zu\n    ",
            token->line);

    fwrite(line_start, 1, (size_t)(line_end - line_start), stderr);

    fputc('\n', stderr);
    fputs("    ", stderr);

    for (size_t i = 1; i < token->column; i++) {
        fputc(' ', stderr);
    }

    fputs("^\n", stderr);

    fprintf(
        stderr,
        "SyntaxError: invalid character '%c'\n",
        error_char
    );
}

int lexer_is_at_end(Lexer *lexer) {
    return lexer->position >= lexer->length;
}

char lexer_advance(Lexer *lexer) {
    if (lexer_is_at_end(lexer)) {
        return '\0';
    }
    char current = lexer->source[lexer->position];
    lexer->position++;
    if (current == '\n') {
        lexer->line++;
        lexer->column = 1;
    } else if (current == '\r') {
        // Handle Windows-style line endings (\r\n)
        if (lexer->position < lexer->length && lexer->source[lexer->position] == '\n') {
            lexer->position++; // Skip the '\n' after '\r'
        }
        lexer->line++;
        lexer->column = 1;
    } else {
        lexer->column++;
    } 
    return current;
}

char lexer_peek(Lexer *lexer) {
    if (lexer_is_at_end(lexer)) { return '\0'; }
    return lexer->source[lexer->position];
}

int lexer_match(Lexer *lexer, char expected) {
    if (lexer_is_at_end(lexer)) { return 0; }
    if (lexer_peek(lexer) != expected) {
        return 0;
    }
    lexer_advance(lexer);
    return 1;
}

void lexer_skip_whitespace(Lexer *lexer) {
    while (isspace((unsigned char)lexer_peek(lexer))) {
        lexer_advance(lexer);
    }
}

Token lexer_make_token(Lexer *lexer, TokenType type) {
    Token token;
    token.type = type;
    token.start = lexer->start;
    token.length = lexer->position - lexer->start;
    token.line = lexer->start_line;
    token.column = lexer->start_column;
    return token;
}

Token lexer_next_token(Lexer *lexer)
{
    lexer_skip_whitespace(lexer);

    lexer->start = lexer->position;
    lexer->start_line = lexer->line;
    lexer->start_column = lexer->column;

    if (lexer_is_at_end(lexer)) {
        return lexer_make_token(lexer, TOKEN_EOF);
    }

    char c = lexer_peek(lexer);

    if (isdigit((unsigned char)c)) {
        return lexer_scan_number(lexer);
    }

    if (isalpha((unsigned char)c) || c == '_') {
        return lexer_scan_identifier(lexer);
    }

    if (c == '"') {
       return lexer_scan_string(lexer);
    }
    
    return lexer_scan_operator(lexer);
}
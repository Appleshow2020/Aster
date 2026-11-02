#ifndef ASTER_VECTOR_H
#define ASTER_VECTOR_H

#include <stddef.h>

typedef struct Vector {
    int *items;
    size_t length;
    size_t capacity;
} Vector;

void vector_init(Vector *vector);
int vector_push(Vector *vector, int value);
void vector_free(Vector *vector);

#endif
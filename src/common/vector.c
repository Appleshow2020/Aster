#include <stdlib.h>
#include "include/aster/vector.h"

void vector_init(Vector *vector)
{
    vector->capacity = 4;
    vector->length = 0;
    vector->items = malloc(sizeof(int) * vector->capacity);
}

int vector_push(Vector *vector, int value)
{
    if (vector->length == vector->capacity) {
        size_t new_capacity = vector->capacity * 2;

        int *temp = realloc(
            vector->items,
            sizeof(int) * new_capacity
        );

        if (temp == NULL) {
            return 0;
        }

        vector->items = temp;
        vector->capacity = new_capacity;
    }

    vector->items[vector->length] = value;
    vector->length++;

    return 1;
}

void vector_free(Vector *vector)
{
    free(vector->items);

    vector->items = NULL;
    vector->length = 0;
    vector->capacity = 0;
}
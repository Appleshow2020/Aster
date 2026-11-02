#include <stdio.h>
#include "aster/vector.h"

int main(void)
{
    Vector vector;

    vector_init(&vector);

    vector_push(&vector, 10);
    vector_push(&vector, 20);
    vector_push(&vector, 30);

    for (size_t i = 0; i < vector.length; i++) {
        printf("%d\n", vector.items[i]);
    }

    vector_free(&vector);

    return 0;
}
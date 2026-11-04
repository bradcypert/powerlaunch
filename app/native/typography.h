#ifndef POWERLAUNCH_TYPOGRAPHY_H
#define POWERLAUNCH_TYPOGRAPHY_H
#include <raylib.h>
Font pl_font_init(void);
void pl_font_close(void);
float pl_font_measure(const char *text, int size);
void pl_font_draw(const char *text, float x, float y, int size, Color ink);
#endif

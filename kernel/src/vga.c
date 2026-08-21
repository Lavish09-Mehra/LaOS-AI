// ============================================================
// LavOS 2026 kernel — vga.c
// Text-mode VGA driver (80x25, 16 colors) for the boot splash.
// Writes straight to the memory-mapped buffer at 0xB8000.
// Entry points used elsewhere: init, putc/puts/clear/setcolor,
// puthex, and a boot splash. Freestanding, no standard library.
// ============================================================

#include <stddef.h>
#include <stdint.h>

#define VGA_WIDTH  80
#define VGA_HEIGHT 25
#define VGA_MEMORY ((uint16_t*)0xB8000)
#define VGA_INDEX(row, col) ((row) * VGA_WIDTH + (col))

// --- 16 standard VGA palette colors ----------------------------------
enum vga_color {
    VGA_BLACK = 0, VGA_BLUE, VGA_GREEN, VGA_CYAN, VGA_RED,
    VGA_MAGENTA, VGA_BROWN, VGA_LIGHT_GREY, VGA_DARK_GREY,
    VGA_LIGHT_BLUE, VGA_LIGHT_GREEN, VGA_LIGHT_CYAN, VGA_LIGHT_RED,
    VGA_LIGHT_MAGENTA, VGA_YELLOW, VGA_WHITE
};

static uint16_t* const buffer = VGA_MEMORY;
static uint8_t cursor_color = VGA_LIGHT_GREY;
static size_t row = 0;
static size_t col = 0;

// pack one screen cell: low byte = character, high byte = color
static inline uint16_t vga_entry(char c, uint8_t color)
{
    return (uint16_t)c | ((uint16_t)color << 8);
}

static inline uint8_t vga_color(uint8_t fg, uint8_t bg)
{
    return fg | (bg << 4);
}

void vga_setcolor(uint8_t fg, uint8_t bg)
{
    cursor_color = vga_color(fg, bg);
}

void vga_putchar_at(char c, size_t r, size_t cpos, uint8_t color)
{
    buffer[VGA_INDEX(r, cpos)] = vga_entry(c, color);
}

// move every row up one, clear the last line (row returns to 24)
static void vga_scroll(void)
{
    size_t r, c;
    for (r = 1; r < VGA_HEIGHT; r++)
        for (c = 0; c < VGA_WIDTH; c++)
            buffer[VGA_INDEX(r - 1, c)] = buffer[VGA_INDEX(r, c)];
    for (c = 0; c < VGA_WIDTH; c++)
        buffer[VGA_INDEX(VGA_HEIGHT - 1, c)] = vga_entry(' ', cursor_color);
    row = VGA_HEIGHT - 1;
}

void vga_putchar(char c)
{
    if (c == '\n') {
        row++;
        col = 0;
    } else if (c == '\t') {
        col = (col + 4) & ~(size_t)3;
    } else if (c == '\r') {
        col = 0;
    } else if (c == '\b') {
        if (col > 0)
            col--;
        else if (row > 0) {
            row--;
            col = VGA_WIDTH - 1;
        }
        vga_putchar_at(' ', row, col, cursor_color);
    } else {
        vga_putchar_at(c, row, col, cursor_color);
        col++;
    }
    if (col >= VGA_WIDTH) {
        col = 0;
        row++;
    }
    if (row >= VGA_HEIGHT)
        vga_scroll();
}

void vga_puts(const char* s)
{
    while (*s)
        vga_putchar(*s++);
}

// print a value as hex, e.g. puthex(0xCAFE) -> "CAFE"
void vga_puthex(uint32_t value)
{
    static const char hex[] = "0123456789ABCDEF";
    int shift;
    int started = 0;
    for (shift = 28; shift >= 0; shift -= 4) {
        char nibble = hex[(value >> shift) & 0xF];
        if (nibble != '0' || started || shift == 0) {
            vga_putchar(nibble);
            started = 1;
        }
    }
}

// wipe the screen to blank cells in a given background color
void vga_clear(uint8_t bg)
{
    size_t i;
    for (i = 0; i < VGA_WIDTH * VGA_HEIGHT; i++)
        buffer[i] = vga_entry(' ', vga_color(VGA_LIGHT_GREY, bg));
    row = 0;
    col = 0;
}

void vga_init(void)
{
    cursor_color = vga_color(VGA_LIGHT_GREY, VGA_BLACK);
    vga_clear(VGA_BLACK);
}

// the "wow" moment: centered LavOS banner, colored, 2-line splash
void vga_boot_splash(void)
{
    static const char* banner =
        "     ______    _____   __    __  ______\n"
        "    |    _ |  /     | |  |  |  ||      |\n";
    vga_setcolor(VGA_CYAN, VGA_BLACK);
    vga_puts(banner);
    vga_setcolor(VGA_LIGHT_GREEN, VGA_BLACK);
    vga_puts("LavOS 2026 -- from-scratch kernel\n\n");
    vga_setcolor(VGA_LIGHT_GREY, VGA_BLACK);
    vga_puts("Booting own kernel: vga.. serial.. shell..\n");
}
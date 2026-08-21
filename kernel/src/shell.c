// ============================================================
// LavOS 2026 kernel — shell.c
// Interactive in-kernel command loop, driven by PURE POLLING:
//   - PS/2 keyboard on port 0x60 (scancode set 1)
//   - RTC seconds on CMOS ports 0x70/0x71 (real 1-second clock)
// No interrupts, no IDT — everything works on the bare kernel.
// Commands: help, echo <text>, clear, uptime, about.
// ============================================================

#include <stddef.h>
#include <stdint.h>

// ---- tiny port I/O (freestanding, mirrors serial.c helpers) ---------
static inline void outb(uint16_t port, uint8_t value)
{
    __asm__ __volatile__("outb %0, %1" : : "a"(value), "Nd"(port));
}

static inline uint8_t inb(uint16_t port)
{
    uint8_t value;
    __asm__ __volatile__("inb %1, %0" : "=a"(value) : "Nd"(port));
    return value;
}

// ---- services used from other files --------------------------------
void vga_putchar(char c);
void vga_puts(const char* s);
void vga_clear(uint8_t bg);
void serial_puts(const char* s);

// ---- real-time clock: a monotonic uptime counter, 1-second steps ----
static uint8_t cmos_read(uint8_t reg)
{
    outb(0x70, (uint8_t)(reg | 0x80));    // select register, NMI off
    return inb(0x71);
}

static int rtc_busy(void)
{
    return (cmos_read(0x0A) & 0x80) != 0; // status A bit 7 = update in progress
}

static uint8_t last_rtc_sec = 0xFF;
static unsigned long uptime_s = 0;

static void rtc_tick(void)
{
    uint8_t s;
    if (rtc_busy())
        return;                            // skip mid-update reads (racy)
    s = cmos_read(0x00);                   // register 0x00 = seconds
    if (s != last_rtc_sec) {
        uptime_s += (s + 60 - last_rtc_sec) % 60;   // handles the 59->0 wrap
        last_rtc_sec = s;
    }
}

// ---- PS/2 keyboard: scancode set 1 -> ASCII (no shift handling) ----
static const char SCAN_ASCII[128] = {
    0, 0, '1','2','3','4','5','6','7','8','9','0',
    '-','=','\b','\t',                     // 0x0E = backspace, 0x0F = tab
    'q','w','e','r','t','y','u','i','o','p',
    '[',']','\n',                          // 0x1C = Enter
    0,                                     // ctrl
    'a','s','d','f','g','h','j','k','l',
    ';','\'','`', 0, '\\',
    'z','x','c','v','b','n','m',
    ',','.','/', 0, 0, 0, 0,
    ' '                                    // 0x39 = space
};

// returns ASCII char, or 0 when nothing pressed / key released
static char key_poll(void)
{
    uint8_t status;
    uint8_t scancode;

    status = inb(0x64);                    // keyboard controller status
    if (!(status & 0x01))                  // bit 0: output buffer empty
        return 0;
    scancode = inb(0x60);
    if (scancode & 0x80)                   // key-up events ignored
        return 0;
    if (scancode >= 128)
        return 0;
    return (char)SCAN_ASCII[scancode];
}

// ---- line buffer ----------------------------------------------------
#define LINE_MAX 100
static char line[LINE_MAX];
static size_t line_len = 0;

// ---- tiny string helpers --------------------------------------------
static int str_eq(const char* a, const char* b)
{
    while (*a && *a == *b) { a++; b++; }
    return *a == *b;
}

static void putdec(unsigned long value)
{
    char buf[12];
    int i = 11;
    buf[i--] = '\0';
    do { buf[i--] = (char)('0' + value % 10); value /= 10; } while (value);
    vga_puts(&buf[i + 1]);
}

// ---- command dispatch -------------------------------------------------
static void shell_exec(const char* cmd)
{
    if (str_eq(cmd, "help")) {
        vga_puts("commands: help | echo <text> | clear | uptime | about\n");
    } else if (cmd[0] == 'e' && cmd[1] == 'c' && cmd[2] == 'h' && cmd[3] == 'o' &&
               (cmd[4] == ' ' || cmd[4] == '\0')) {
        vga_puts(cmd[4] == ' ' ? cmd + 5 : "\n");
    } else if (str_eq(cmd, "clear")) {
        vga_clear(0);                      // 0 = black background
    } else if (str_eq(cmd, "uptime")) {
        vga_puts("uptime: ");
        putdec(uptime_s);
        vga_puts(" seconds (RTC)\n");
    } else if (str_eq(cmd, "about")) {
        vga_puts("LavOS 2026 -- hand-written 32-bit kernel\n");
        vga_puts("built with nasm + gcc, boots via GRUB multiboot\n");
    } else {
        vga_puts("unknown command (type 'help')\n");
    }
}

static void shell_enter(void)
{
    line[line_len] = '\0';                 // bound every read by the terminator
    vga_puts("\n");
    serial_puts("[shell] ");
    serial_puts(line);
    serial_puts("\r\n");
    if (line_len)
        shell_exec(line);
    line_len = 0;
}

// ---- the interactive loop (polling only, no interrupts) ---------------
void shell_run(void)
{
    vga_puts("\nLavOS 2026 shell -- type 'help'\n");
    vga_puts("lavos$ ");

    for (;;) {
        char c = key_poll();
        if (c == '\n') {
            shell_enter();
            vga_puts("lavos$ ");
        } else if (c == '\b') {
            if (line_len > 0) {
                line_len--;
                vga_puts("\b \b");         // erase the char on screen
            }
        } else if (c != 0 && line_len < LINE_MAX - 1) {
            line[line_len++] = c;
            vga_putchar(c);
        }
        rtc_tick();                        // keep the clock alive every spin
    }
}
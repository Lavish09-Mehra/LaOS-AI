// ============================================================
// LavOS 2026 kernel — serial.c
// COM1 (0x3F8) serial driver: the kernel talks to the host
// machine over serial while QEMU runs. Used for the "alive"
// heartbeat and debug logs — visible even without a display.
// Speed 115200 to match the grub.cfg serial console setting.
// ============================================================

#include <stdint.h>

#define COM1       0x3F8
#define COM1_LSR   (COM1 + 5)   // line status register
#define COM1_THR   (COM1 + 0)   // transmit holding register
#define LSR_TX_EMPTY 0x20       // bit 5: transmitter is ready

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

static int serial_ready(void)
{
    return (inb(COM1_LSR) & LSR_TX_EMPTY) != 0;
}

void serial_init(void)
{
    outb(COM1 + 1, 0x00);   // disable interrupts
    outb(COM1 + 3, 0x80);   // DLAB on: program the baud rate
    outb(COM1 + 0, 0x01);   // divisor low  -> 115200 baud
    outb(COM1 + 1, 0x00);   // divisor high
    outb(COM1 + 3, 0x03);   // 8 data bits, no parity, 1 stop bit
    outb(COM1 + 2, 0xC7);   // FIFO on, 14-byte threshold
    outb(COM1 + 4, 0x0B);   // RTS/DSR set, IRQs enabled
}

void serial_putc(char c)
{
    while (!serial_ready())
        ;
    outb(COM1_THR, (uint8_t)c);
}

void serial_puts(const char* s)
{
    while (*s)
        serial_putc(*s++);
}

// proof-of-life: written to COM1 right after boot
void serial_heartbeat(void)
{
    serial_puts("[LavOS] kernel alive on COM1\r\n");
}
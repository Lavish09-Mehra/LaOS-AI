// ============================================================
// LavOS 2026 kernel — kmain.c
// C entry point, called by boot.asm after the multiboot header.
// Job: init the VGA driver, draw the boot splash, then hand
// control to the shell (added in the next build step).
// ============================================================

// vga driver entry points (defined in vga.c)
void vga_init(void);
void vga_boot_splash(void);

// serial driver entry points (defined in serial.c)
void serial_init(void);
void serial_heartbeat(void);

// shell entry point (defined in shell.c)
void shell_run(void);

void kmain(void)
{
    vga_init();
    vga_boot_splash();
    serial_init();
    serial_heartbeat();

    /* shell owns the machine from here: parse commands forever */
    shell_run();
}
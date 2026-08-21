/* ============================================================
   LavOS 2026 kernel — linker.ld
   Layout script: decides where every section lands in RAM and
   names _start (from boot.asm) as the entry point.
   GRUB loads the multiboot kernel at 1 MiB; headers come first.
   Link with: i686-elf-ld -T linker.ld <objects> -o kernel.bin
   ============================================================ */

ENTRY(_start)

SECTIONS
{
    /* Load the kernel at 1 MiB, the multiboot/GRUB convention. */
    . = 1M;

    .text BLOCK(4K) : ALIGN(4K)
    {
        *(.multiboot)   /* the GRUB header must land first */
        *(.text)
    }

    .rodata BLOCK(4K) : ALIGN(4K)
    {
        *(.rodata)
    }

    .data BLOCK(4K) : ALIGN(4K)
    {
        *(.data)
    }

    .bss BLOCK(4K) : ALIGN(4K)
    {
        *(COMMON)
        *(.bss)
    }
}
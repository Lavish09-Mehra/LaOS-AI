; ============================================================
; LavOS 2026 kernel — boot.asm
; The FIRST code that runs. In 32-bit protected mode,
; declares the GRUB multiboot header, sets up a 16 KiB stack,
; then calls the C entry point kmain().
; Assemble with: nasm -f elf32 boot.asm -o boot.o
; ============================================================

; --- Multiboot header constants (GRUB validates the checksum) ---
MBALIGN  equ 1 << 0                  ; align loaded modules on page boundaries
MEMINFO  equ 1 << 1                  ; provide the bootloader memory map
FLAGS    equ MBALIGN | MEMINFO
MAGIC    equ 0x1BADB002              ; multiboot magic number
CHECKSUM equ -(MAGIC + FLAGS)        ; magic + flags + checksum must equal 0

section .multiboot
; GRUB looks for this header in the first 8 KiB of the kernel image.
align 4
    dd MAGIC
    dd FLAGS
    dd CHECKSUM

section .text
global _start
extern kmain                  ; defined in kmain.c (linked later)
_start:
    mov esp, stack_top   ; point the CPU stack at our reserved 16 KiB
    cli                  ; interrupts off until kmain initializes them
    call kmain           ; hand control to the C world
.hang:
    cli                  ; if kmain ever returns, park the CPU
    hlt
    jmp .hang

section .bss
align 16
stack_bottom:
    resb 16384           ; 16 KiB of zero-initialized stack space
stack_top:
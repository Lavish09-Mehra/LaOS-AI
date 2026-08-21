# ============================================================
# LavOS 2026 kernel — Makefile
# Build & run our own bootable OS in QEMU.
# `make run`   -> compile, build the .iso, boot it in QEMU
# `make kernel`-> just the ELF kernel.bin (fast debug loop)
# Toolchain: nasm, i686-elf-gcc, grub-mkrescue, qemu (in WSL).
# ============================================================

ASM     := nasm
CC      := i686-elf-gcc
LD      := i686-elf-ld
LDSCRIPT:= linker.ld
GRUB    := grub-mkrescue
QEMU    := qemu-system-i386

ASMFLAGS := -f elf32
CFLAGS   := -ffreestanding -fno-builtin -fno-pie -fno-stack-protector -m32 -Wall -Wextra
LDFLAGS  := -T $(LDSCRIPT) -nostdlib -m elf_i386

BUILD := build
BIN   := $(BUILD)/kernel.bin
ISO   := $(BUILD)/lavos.iso

OBJS := $(BUILD)/boot.o $(BUILD)/kmain.o $(BUILD)/vga.o $(BUILD)/shell.o $(BUILD)/serial.o

.PHONY: all kernel iso run clean

all: kernel

kernel: $(BIN)

# --- per-source build rules ---------------------------------------------
$(BUILD)/%.o: src/%.asm
	@mkdir -p $(BUILD)
	$(ASM) $(ASMFLAGS) $< -o $@

$(BUILD)/%.o: src/%.c
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@

# --- link kernel ------------------------------------------------
$(BIN): $(OBJS)
	$(LD) $(LDFLAGS) $(OBJS) -o $@

# --- bootable .iso (GRUB layout: iso/boot/grub/grub.cfg) --------
iso: $(ISO)
$(ISO): $(BIN) iso/boot/grub/grub.cfg
	@rm -rf $(BUILD)/isodir
	@mkdir -p $(BUILD)/isodir/boot/grub
	cp $(BIN) $(BUILD)/isodir/boot/lavos.bin
	cp iso/boot/grub/grub.cfg $(BUILD)/isodir/boot/grub/grub.cfg
	$(GRUB) -o $(ISO) $(BUILD)/isodir

run: $(ISO)
	$(QEMU) -cdrom $(ISO) -serial stdio

clean:
	rm -rf $(BUILD) $(ISO)
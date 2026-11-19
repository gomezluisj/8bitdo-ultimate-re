// Shared 8BitDo USB HID bootloader protocol helpers (macOS IOKit + Linux hidraw)
// Protocol: report id 5, cmd 3=write, 4=erase, 5=read, 7=reset, 8=identify
#ifndef BOOT_PROTO_H
#define BOOT_PROTO_H

#include <errno.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum {
    VENDOR_8BITDO  = 0x2dc8,
    BOOT_PID       = 0x3208,
    REPORT_ID_BOOT = 5,
    REPORT_SIZE    = 64,
    PAYLOAD_OFFSET = 18,
    WRITE_MAX      = 46,
    READ_MAX       = REPORT_SIZE - PAYLOAD_OFFSET
};

typedef int (*boot_cmd_fn)(void *ctx,
                           uint16_t cmd, uint16_t params, uint16_t len, uint16_t crc,
                           uint32_t total, uint32_t off,
                           const uint8_t *payload, uint16_t plen,
                           uint8_t *resp, int wait_ms);

static inline void set_u16(uint8_t *p, uint16_t v) {
    p[0] = (uint8_t)(v & 0xff);
    p[1] = (uint8_t)(v >> 8);
}

static inline void set_u32(uint8_t *p, uint32_t v) {
    p[0] = (uint8_t)(v & 0xff);
    p[1] = (uint8_t)((v >> 8) & 0xff);
    p[2] = (uint8_t)((v >> 16) & 0xff);
    p[3] = (uint8_t)((v >> 24) & 0xff);
}

static inline uint16_t get_u16(const uint8_t *p) {
    return (uint16_t)p[0] | ((uint16_t)p[1] << 8);
}

static inline uint16_t crc16_modbus(const uint8_t *data, size_t len) {
    uint16_t crc = 0xffff;
    for (size_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (int bit = 0; bit < 8; bit++) {
            crc = (crc & 1) ? (uint16_t)((crc >> 1) ^ 0xa001) : (uint16_t)(crc >> 1);
        }
    }
    return crc;
}

static inline int parse_u32_strict(const char *s, uint32_t *out) {
    if (!s || !*s || s[0] == '-') return -1;
    errno = 0;
    char *end = NULL;
    unsigned long long v = strtoull(s, &end, 0);
    if (errno != 0 || !end || *end != '\0' || v > UINT32_MAX) return -1;
    *out = (uint32_t)v;
    return 0;
}

static inline int expect_ack(const uint8_t *resp, int rlen, uint16_t expected_cmd, const char *label) {
    if (rlen < 8) {
        fprintf(stderr, "%s: short ack (%d bytes):", label, rlen);
        for (int i = 0; i < rlen; i++) fprintf(stderr, " %02x", resp[i]);
        fprintf(stderr, "\n");
        return -1;
    }
    uint16_t rcmd = get_u16(resp + 2);
    uint16_t rparam = get_u16(resp + 4);
    if (rcmd != 0 || rparam != expected_cmd) {
        fprintf(stderr, "%s: unexpected ack cmd=%u param=%u raw:", label, rcmd, rparam);
        for (int i = 0; i < rlen && i < 20; i++) fprintf(stderr, " %02x", resp[i]);
        fprintf(stderr, "\n");
        return -1;
    }
    return 0;
}

static inline int boot_read(boot_cmd_fn cmd_fn, void *ctx, uint32_t addr, uint8_t *out, uint16_t len) {
    if (len > READ_MAX) len = READ_MAX;
    uint8_t resp[REPORT_SIZE + 1];
    memset(resp, 0, sizeof(resp));
    int r = cmd_fn(ctx, 5, 0, len, len, len, addr, NULL, 0, resp, 2000);
    if (r < 0) return -1;
    if (r < (int)(PAYLOAD_OFFSET + len)) {
        fprintf(stderr, "short read @%08x: got %d want %d\n", addr, r, PAYLOAD_OFFSET + len);
        return -1;
    }
    uint16_t rcmd = get_u16(resp + 2);
    uint16_t rparam = get_u16(resp + 4);
    if (rcmd != 0 || rparam != 5) {
        fprintf(stderr, "bad read resp @%08x: cmd=%u param=%u\n", addr, rcmd, rparam);
        return -1;
    }
    memcpy(out, resp + PAYLOAD_OFFSET, len);
    return len;
}

static inline int boot_write(boot_cmd_fn cmd_fn, void *ctx, uint32_t addr,
                             const uint8_t *data, uint32_t len, uint32_t total) {
    uint32_t done = 0;
    while (done < len) {
        uint16_t chunk = (len - done) < WRITE_MAX ? (uint16_t)(len - done) : WRITE_MAX;
        uint16_t crc = crc16_modbus(data + done, chunk);
        uint8_t resp[REPORT_SIZE + 1];
        memset(resp, 0, sizeof(resp));
        int r = cmd_fn(ctx, 3, 0, chunk, crc, total, addr + done,
                       data + done, chunk, resp, 3000);
        if (r < 0) return -1;
        if (expect_ack(resp, r, 3, "write") != 0) return -1;
        done += chunk;
        if ((done & 0xfff) < WRITE_MAX || done == len) {
            printf("wrote %u/%u\r", done, len);
            fflush(stdout);
        }
    }
    printf("\n");
    return 0;
}

static inline int verify_flash(boot_cmd_fn cmd_fn, void *ctx, uint32_t addr,
                               const uint8_t *expected, uint32_t len) {
    uint8_t chunk[READ_MAX];
    uint32_t done = 0;
    while (done < len) {
        uint16_t want = (len - done) < READ_MAX ? (uint16_t)(len - done) : READ_MAX;
        int got = boot_read(cmd_fn, ctx, addr + done, chunk, want);
        if (got <= 0) return -1;
        if (memcmp(chunk, expected + done, (size_t)got) != 0) {
            fprintf(stderr, "\nVERIFY MISMATCH at 0x%08x\n", addr + done);
            return -1;
        }
        done += (uint32_t)got;
        if ((done & 0xfff) < READ_MAX || done == len) {
            printf("verified %u/%u\r", done, len);
            fflush(stdout);
        }
    }
    printf("\n");
    return 0;
}

static inline uint8_t *read_file(const char *path, size_t *out) {
    FILE *f = fopen(path, "rb");
    if (!f) {
        perror(path);
        return NULL;
    }
    if (fseek(f, 0, SEEK_END) != 0) {
        perror(path);
        fclose(f);
        return NULL;
    }
    long l = ftell(f);
    if (l <= 0) {
        fprintf(stderr, "%s: empty or unreadable file\n", path);
        fclose(f);
        return NULL;
    }
    rewind(f);
    uint8_t *d = (uint8_t *)malloc((size_t)l);
    if (!d || fread(d, 1, (size_t)l, f) != (size_t)l) {
        free(d);
        fclose(f);
        return NULL;
    }
    fclose(f);
    *out = (size_t)l;
    return d;
}

static inline int do_backup(boot_cmd_fn cmd_fn, void *ctx, uint32_t addr, uint32_t len, const char *out) {
    FILE *f = fopen(out, "wb");
    if (!f) {
        perror(out);
        return 1;
    }
    uint8_t chunk[READ_MAX];
    uint32_t done = 0;
    while (done < len) {
        uint16_t want = (len - done) < READ_MAX ? (uint16_t)(len - done) : READ_MAX;
        if (boot_read(cmd_fn, ctx, addr + done, chunk, want) <= 0) {
            fclose(f);
            remove(out);
            return 2;
        }
        if (fwrite(chunk, 1, want, f) != want) {
            perror("fwrite");
            fclose(f);
            remove(out);
            return 2;
        }
        done += want;
        if ((done & 0xfff) < READ_MAX || done == len) {
            printf("backup %08x/%08x\r", addr + done, addr + len);
            fflush(stdout);
        }
    }
    if (fclose(f) != 0) {
        perror("fclose");
        remove(out);
        return 2;
    }
    printf("\nbackup ok -> %s\n", out);
    return 0;
}

static inline void boot_print_usage(const char *prog, const char *platform_desc) {
    fprintf(stderr,
        "8BitDo boot tool for %s\n"
        "usage:\n"
        "  %s identify                          - probe boot device, print PID/version\n"
        "  %s dump <addr> <len> <out.bin>       - dump arbitrary flash range\n"
        "  %s backup <out.bin> [len]            - dump app flash (default 0x01018000,+0x20000)\n"
        "  %s flashe <enc_body.bin> <plain.bin> - erase+write enc+verify plain+reset\n",
        platform_desc, prog, prog, prog, prog);
}

static inline int boot_dispatch(int argc, char **argv, boot_cmd_fn cmd_fn, void *ctx) {
    if (!strcmp(argv[1], "identify") && argc == 2) {
        uint8_t resp[REPORT_SIZE + 1];
        memset(resp, 0, sizeof(resp));
        int r = cmd_fn(ctx, 8, 0, 4, 4, 0, 0, NULL, 0, resp, 2000);
        if (r < 0) return 2;
        printf("identify resp (%d bytes):", r);
        for (int i = 0; i < r && i < 24; i++) printf(" %02x", resp[i]);
        printf("\n");
        uint8_t vb[8];
        if (boot_read(cmd_fn, ctx, 0x01017040, vb, 8) > 0) {
            printf("version @0x01017040:");
            for (int i = 0; i < 8; i++) printf(" %02x", vb[i]);
            printf("  (main=%u beta=%u)\n", get_u16(vb), get_u16(vb + 4));
        }
        return 0;
    }
    if (!strcmp(argv[1], "dump") && argc == 5) {
        uint32_t a = 0, l = 0;
        if (parse_u32_strict(argv[2], &a) != 0 || parse_u32_strict(argv[3], &l) != 0 || l == 0) {
            fprintf(stderr, "invalid dump addr/len (must be valid uint32, len > 0)\n");
            return 1;
        }
        return do_backup(cmd_fn, ctx, a, l, argv[4]);
    }
    if (!strcmp(argv[1], "backup") && (argc == 3 || argc == 4)) {
        uint32_t len = 0x20000;
        if (argc == 4 && (parse_u32_strict(argv[3], &len) != 0 || len == 0)) {
            fprintf(stderr, "invalid backup len (must be valid uint32 > 0)\n");
            return 1;
        }
        return do_backup(cmd_fn, ctx, 0x01018000, len, argv[2]);
    }
    if (!strcmp(argv[1], "flashe") && argc == 4) {
        uint32_t addr = 0x01018000;
        size_t elen = 0, plen_len = 0;
        uint8_t resp[REPORT_SIZE + 1];
        memset(resp, 0, sizeof(resp));
        uint8_t *enc = read_file(argv[2], &elen);
        uint8_t *pln = read_file(argv[3], &plen_len);
        if (!enc || !pln || elen == 0 || elen != plen_len) {
            fprintf(stderr, "enc/plain size mismatch, empty, or unreadable\n");
            free(enc);
            free(pln);
            return 1;
        }
        uint32_t ulen = (uint32_t)((elen + 0xfff) & ~0xfffUL);
        printf("flashe: %zu encrypted bytes at %#x (erase %#x)\n", elen, addr, ulen);
        int r = cmd_fn(ctx, 4, 0, 0, 0, ulen, addr, NULL, 0, resp, 120000);
        if (r < 0) {
            fprintf(stderr, "erase timeout; controller left in BOOT mode\n");
            free(enc);
            free(pln);
            return 2;
        }
        if (expect_ack(resp, r, 4, "erase") != 0) {
            free(enc);
            free(pln);
            return 2;
        }
        printf("erase ok, writing encrypted...\n");
        if (boot_write(cmd_fn, ctx, addr, enc, (uint32_t)elen, (uint32_t)elen)) {
            fprintf(stderr, "write failed; controller left in BOOT mode — DO NOT UNPLUG\n");
            free(enc);
            free(pln);
            return 2;
        }
        printf("verifying readback (decrypted) against plaintext...\n");
        if (verify_flash(cmd_fn, ctx, addr, pln, (uint32_t)elen)) {
            fprintf(stderr, "VERIFY FAILED; controller left in BOOT mode — DO NOT UNPLUG, re-run or restore backup\n");
            free(enc);
            free(pln);
            return 2;
        }
        printf("verified. resetting...\n");
        cmd_fn(ctx, 7, 0, 0, 0, 0, 0, NULL, 0, NULL, 0);
        printf("done.\n");
        free(enc);
        free(pln);
        return 0;
    }
    fprintf(stderr, "invalid command or argument count: %s\n", argv[1]);
    return 1;
}

#endif // BOOT_PROTO_H

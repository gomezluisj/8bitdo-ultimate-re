// 8BitDo boot-mode flash tool for Linux (hidraw, zero external deps)
#include <dirent.h>
#include <fcntl.h>
#include <linux/hidraw.h>
#include <poll.h>
#include <sys/ioctl.h>
#include <unistd.h>

#include "boot_proto.h"

typedef struct {
    int fd;
} linux_ctx_t;

static int open_boot_device(void) {
    DIR *d = opendir("/dev");
    if (!d) {
        perror("opendir /dev");
        return -1;
    }
    struct dirent *e;
    char path[300];
    int fd = -1;
    while ((e = readdir(d))) {
        if (strncmp(e->d_name, "hidraw", 6) != 0) continue;
        snprintf(path, sizeof(path), "/dev/%s", e->d_name);
        int f = open(path, O_RDWR | O_CLOEXEC);
        if (f < 0) continue;
        struct hidraw_devinfo info;
        if (ioctl(f, HIDIOCGRAWINFO, &info) == 0 &&
            (uint16_t)info.vendor == VENDOR_8BITDO) {
            char name[128] = {0};
            ioctl(f, HIDIOCGRAWNAME(sizeof(name) - 1), name);
            uint16_t pid = (uint16_t)info.product;
            if (pid == BOOT_PID && fd < 0) {
                printf("[found] %s: VID %04x PID %04x \"%s\"\n", path, (uint16_t)info.vendor, pid, name);
                fd = f;
                continue;
            }
            printf("[skip]  %s: VID %04x PID %04x \"%s\" (not boot PID %04x)\n",
                   path, (uint16_t)info.vendor, pid, name, BOOT_PID);
        }
        close(f);
    }
    closedir(d);
    return fd;
}

static int linux_boot_cmd(void *vctx,
                          uint16_t cmd, uint16_t params, uint16_t len, uint16_t crc,
                          uint32_t total, uint32_t off,
                          const uint8_t *payload, uint16_t plen,
                          uint8_t *resp, int wait_ms) {
    linux_ctx_t *ctx = (linux_ctx_t *)vctx;
    uint8_t rep[REPORT_SIZE + 1];
    memset(rep, 0, sizeof(rep));
    rep[0] = REPORT_ID_BOOT;
    set_u16(rep + 1, cmd);
    set_u16(rep + 3, params);
    set_u16(rep + 5, len);
    set_u16(rep + 7, crc);
    set_u32(rep + 9, total);
    set_u32(rep + 13, off);
    if (payload && plen) {
        if (plen > WRITE_MAX) return -1;
        memcpy(rep + 17, payload, plen);
    }

    ssize_t wr = write(ctx->fd, rep, REPORT_SIZE);
    if (wr < 0) {
        perror("write");
        return -1;
    }
    if (wr != REPORT_SIZE) {
        fprintf(stderr, "short hidraw write: %zd/%d\n", wr, REPORT_SIZE);
        return -1;
    }
    if (!resp || wait_ms <= 0) return 0;

    struct pollfd pf = { .fd = ctx->fd, .events = POLLIN };
    int pr;
    do {
        pr = poll(&pf, 1, wait_ms);
    } while (pr < 0 && errno == EINTR);
    if (pr != 1) {
        fprintf(stderr, "timeout (cmd %u)\n", cmd);
        return -1;
    }
    ssize_t r = read(ctx->fd, resp, REPORT_SIZE + 1);
    if (r <= 0) {
        perror("read");
        return -1;
    }
    return (int)r;
}

int main(int argc, char **argv) {
    if (argc < 2 || !strcmp(argv[1], "-h") || !strcmp(argv[1], "--help")) {
        boot_print_usage(argv[0], "Linux (hidraw)");
        return (argc >= 2) ? 0 : 1;
    }

    int fd = open_boot_device();
    if (fd < 0) {
        fprintf(stderr,
                "no 8BitDo Boot (VID %04x PID %04x) device found. Boot mode: hold LB+RB while plugging USB (check /dev/hidraw* permissions).\n",
                VENDOR_8BITDO, BOOT_PID);
        return 1;
    }

    linux_ctx_t ctx = { .fd = fd };
    int rc = boot_dispatch(argc, argv, linux_boot_cmd, &ctx);
    close(fd);
    return rc;
}

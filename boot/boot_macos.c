// 8BitDo boot-mode flash tool for macOS (IOKit, zero external deps)
#define _DARWIN_C_SOURCE
#include <CoreFoundation/CoreFoundation.h>
#include <IOKit/hid/IOHIDLib.h>
#include <unistd.h>

#include "boot_proto.h"

typedef struct {
    IOHIDDeviceRef device;
    uint8_t buf[REPORT_SIZE + 1];
    CFIndex len;
    int ready;
    IOReturn result;
} macos_ctx_t;

static CFMutableDictionaryRef match_dict_vendor(int vid) {
    CFMutableDictionaryRef dict =
        CFDictionaryCreateMutable(kCFAllocatorDefault, 0,
                                  &kCFTypeDictionaryKeyCallBacks,
                                  &kCFTypeDictionaryValueCallBacks);
    CFNumberRef vid_ref = CFNumberCreate(kCFAllocatorDefault, kCFNumberIntType, &vid);
    CFDictionarySetValue(dict, CFSTR(kIOHIDVendorIDKey), vid_ref);
    CFRelease(vid_ref);
    return dict;
}

static void input_callback(void *context, IOReturn result, void *sender,
                           IOHIDReportType type, uint32_t report_id,
                           uint8_t *report, CFIndex report_len) {
    (void)sender;
    (void)type;
    (void)report_id;
    macos_ctx_t *state = (macos_ctx_t *)context;
    state->result = result;
    if (result != kIOReturnSuccess || !report || report_len <= 0) {
        state->len = 0;
        state->ready = 1;
        return;
    }
    state->len = report_len > REPORT_SIZE ? REPORT_SIZE : report_len;
    memcpy(state->buf, report, (size_t)state->len);
    state->ready = 1;
}

static IOHIDDeviceRef open_boot_device(IOHIDManagerRef *out_manager) {
    IOHIDManagerRef manager = IOHIDManagerCreate(kCFAllocatorDefault, kIOHIDOptionsTypeNone);
    if (!manager) return NULL;
    CFMutableDictionaryRef dict = match_dict_vendor(VENDOR_8BITDO);
    IOHIDManagerSetDeviceMatching(manager, dict);
    CFRelease(dict);
    IOHIDManagerOpen(manager, kIOHIDOptionsTypeNone);
    CFSetRef devices = IOHIDManagerCopyDevices(manager);
    if (!devices || CFSetGetCount(devices) == 0) {
        if (devices) CFRelease(devices);
        IOHIDManagerClose(manager, kIOHIDOptionsTypeNone);
        CFRelease(manager);
        return NULL;
    }
    CFIndex count = CFSetGetCount(devices);
    const void **vals = calloc((size_t)count, sizeof(void *));
    if (!vals) {
        CFRelease(devices);
        IOHIDManagerClose(manager, kIOHIDOptionsTypeNone);
        CFRelease(manager);
        return NULL;
    }
    CFSetGetValues(devices, vals);
    IOHIDDeviceRef chosen = NULL;
    for (CFIndex i = 0; i < count; i++) {
        IOHIDDeviceRef dev = (IOHIDDeviceRef)vals[i];
        CFNumberRef pid_ref = IOHIDDeviceGetProperty(dev, CFSTR(kIOHIDProductIDKey));
        CFStringRef prod_ref = IOHIDDeviceGetProperty(dev, CFSTR(kIOHIDProductKey));
        int pid = 0;
        if (pid_ref) CFNumberGetValue(pid_ref, kCFNumberIntType, &pid);
        char name[128] = {0};
        if (prod_ref) CFStringGetCString(prod_ref, name, sizeof(name), kCFStringEncodingUTF8);
        if (pid == BOOT_PID && !chosen) {
            printf("[found] VID %04x PID %04x \"%s\"\n", VENDOR_8BITDO, pid, name);
            chosen = dev;
        } else {
            printf("[skip]  VID %04x PID %04x \"%s\" (not boot PID %04x)\n",
                   VENDOR_8BITDO, pid, name, BOOT_PID);
        }
    }
    free(vals);
    if (!chosen) {
        CFRelease(devices);
        IOHIDManagerClose(manager, kIOHIDOptionsTypeNone);
        CFRelease(manager);
        return NULL;
    }
    CFRetain(chosen);
    CFRelease(devices);
    IOReturn open_result = IOHIDDeviceOpen(chosen, kIOHIDOptionsTypeNone);
    if (open_result != kIOReturnSuccess) {
        fprintf(stderr, "IOHIDDeviceOpen failed: 0x%08x\n", open_result);
        CFRelease(chosen);
        IOHIDManagerClose(manager, kIOHIDOptionsTypeNone);
        CFRelease(manager);
        return NULL;
    }
    IOHIDDeviceScheduleWithRunLoop(chosen, CFRunLoopGetCurrent(), kCFRunLoopDefaultMode);
    *out_manager = manager;
    return chosen;
}

static int macos_boot_cmd(void *vctx,
                          uint16_t cmd, uint16_t params, uint16_t len, uint16_t crc,
                          uint32_t total, uint32_t off,
                          const uint8_t *payload, uint16_t plen,
                          uint8_t *resp, int wait_ms) {
    macos_ctx_t *state = (macos_ctx_t *)vctx;
    uint8_t report[REPORT_SIZE];
    memset(report, 0, sizeof(report));
    report[0] = REPORT_ID_BOOT;
    set_u16(report + 1, cmd);
    set_u16(report + 3, params);
    set_u16(report + 5, len);
    set_u16(report + 7, crc);
    set_u32(report + 9, total);
    set_u32(report + 13, off);
    if (payload && plen) {
        if (plen > WRITE_MAX) return -1;
        memcpy(report + 17, payload, plen);
    }

    state->ready = 0;
    state->len = 0;
    state->result = kIOReturnSuccess;
    memset(state->buf, 0, sizeof(state->buf));

    IOReturn result = IOHIDDeviceSetReport(state->device, kIOHIDReportTypeOutput, REPORT_ID_BOOT,
                                           report, sizeof(report));
    if (result != kIOReturnSuccess) {
        fprintf(stderr, "IOHIDDeviceSetReport failed: 0x%08x\n", result);
        return -1;
    }
    if (!resp || wait_ms <= 0) return 0;

    int ticks = (wait_ms + 9) / 10;
    for (int i = 0; i < ticks && !state->ready; i++) {
        CFRunLoopRunInMode(kCFRunLoopDefaultMode, 0.01, true);
    }
    if (!state->ready) {
        fprintf(stderr, "timeout (cmd %u)\n", cmd);
        return -1;
    }
    if (state->result != kIOReturnSuccess || state->len <= 0) {
        fprintf(stderr, "input report error (cmd %u, result=0x%08x, len=%ld)\n",
                cmd, state->result, (long)state->len);
        return -1;
    }
    memcpy(resp, state->buf, (size_t)state->len);
    return (int)state->len;
}

int main(int argc, char **argv) {
    if (argc < 2 || !strcmp(argv[1], "-h") || !strcmp(argv[1], "--help")) {
        boot_print_usage(argv[0], "macOS (IOKit)");
        return (argc >= 2) ? 0 : 1;
    }

    IOHIDManagerRef manager = NULL;
    IOHIDDeviceRef device = open_boot_device(&manager);
    if (!device) {
        fprintf(stderr,
                "no 8BitDo Boot (VID %04x PID %04x) device found. Boot mode: hold LB+RB while plugging USB.\n",
                VENDOR_8BITDO, BOOT_PID);
        return 1;
    }

    macos_ctx_t ctx;
    memset(&ctx, 0, sizeof(ctx));
    ctx.device = device;
    uint8_t input_buffer[REPORT_SIZE];
    memset(input_buffer, 0, sizeof(input_buffer));
    IOHIDDeviceRegisterInputReportCallback(device, input_buffer, sizeof(input_buffer),
                                           input_callback, &ctx);

    int rc = boot_dispatch(argc, argv, macos_boot_cmd, &ctx);

    IOHIDDeviceUnscheduleFromRunLoop(device, CFRunLoopGetCurrent(), kCFRunLoopDefaultMode);
    IOHIDDeviceClose(device, kIOHIDOptionsTypeNone);
    CFRelease(device);
    IOHIDManagerClose(manager, kIOHIDOptionsTypeNone);
    CFRelease(manager);
    return rc;
}

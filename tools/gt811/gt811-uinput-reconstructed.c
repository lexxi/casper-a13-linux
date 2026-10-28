/*
 * Casper A13 / Goodix GT811 userspace single-touch -> Linux uinput bridge.
 *
 * RECONSTRUCTED source (2026-10-28): based on the verified device behavior
 * and earlier development notes. Not an exact copy of the original local file.
 * Original Android firmware/module/configuration are NOT included.
 *
 * Diagnostic: --debug prints raw 8-byte reports and state changes to stderr.
 * Must initialize panel separately before starting this process.
 */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <linux/i2c-dev.h>
#include <linux/i2c.h>
#include <linux/input.h>
#include <linux/uinput.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <time.h>
#include <unistd.h>

#define I2C_DEVICE "/dev/i2c-1"
#define INPUT_DEVICE "/dev/uinput"
#define GT811_ADDR 0x5d
#define STATUS_REG 0x0721
#define SCREEN_W 800
#define SCREEN_H 480
#define INTERVAL_NS 20000000L

static volatile sig_atomic_t running = 1;

static void on_signal(int sig) { (void)sig; running = 0; }

static int read_touch(int fd, uint8_t data[8])
{
    uint8_t addr[] = { (uint8_t)(STATUS_REG >> 8),
                       (uint8_t)(STATUS_REG & 0xff) };
    struct i2c_msg msgs[2];
    memset(msgs, 0, sizeof(msgs));
    msgs[0].addr = GT811_ADDR;
    msgs[0].flags = 0;
    msgs[0].len = sizeof(addr);
    msgs[0].buf = addr;
    msgs[1].addr = GT811_ADDR;
    msgs[1].flags = I2C_M_RD;
    msgs[1].len = 8;
    msgs[1].buf = data;
    struct i2c_rdwr_ioctl_data transfer = { .msgs = msgs, .nmsgs = 2 };
    return ioctl(fd, I2C_RDWR, &transfer) == 2 ? 0 : -1;
}

static int emit(int fd, uint16_t type, uint16_t code, int32_t value)
{
    struct input_event event;
    memset(&event, 0, sizeof(event));
    event.type = type;
    event.code = code;
    event.value = value;
    return write(fd, &event, sizeof(event)) == (ssize_t)sizeof(event) ? 0 : -1;
}

static int make_uinput(int fd)
{
    struct uinput_user_dev dev;
    memset(&dev, 0, sizeof(dev));
    snprintf(dev.name, sizeof(dev.name), "Casper Goodix GT811 Touchscreen");
    dev.id.bustype = BUS_I2C;
    /* Virtual userspace device; do not claim a registered hardware vendor ID. */
    dev.id.vendor = 0;
    dev.id.product = 0x0811;
    dev.id.version = 1;
    dev.absmin[ABS_X] = 0;
    dev.absmax[ABS_X] = SCREEN_W;
    dev.absmin[ABS_Y] = 0;
    dev.absmax[ABS_Y] = SCREEN_H;

    if (ioctl(fd, UI_SET_EVBIT, EV_KEY) < 0 ||
        ioctl(fd, UI_SET_EVBIT, EV_ABS) < 0 ||
        ioctl(fd, UI_SET_KEYBIT, BTN_TOUCH) < 0 ||
        ioctl(fd, UI_SET_ABSBIT, ABS_X) < 0 ||
        ioctl(fd, UI_SET_ABSBIT, ABS_Y) < 0)
        return -1;
#ifdef UI_SET_PROPBIT
    if (ioctl(fd, UI_SET_PROPBIT, INPUT_PROP_DIRECT) < 0)
        perror("UI_SET_PROPBIT(INPUT_PROP_DIRECT)");
#endif
    if (write(fd, &dev, sizeof(dev)) != (ssize_t)sizeof(dev))
        return -1;
    return ioctl(fd, UI_DEV_CREATE);
}

int main(int argc, char **argv)
{
    int debug = argc == 2 && strcmp(argv[1], "--debug") == 0;
    if (argc > 1 && !debug) {
        fprintf(stderr, "Usage: %s [--debug]\n", argv[0]);
        return 2;
    }
    signal(SIGINT, on_signal);
    signal(SIGTERM, on_signal);

    int i2c = open(I2C_DEVICE, O_RDWR);
    if (i2c < 0) { perror(I2C_DEVICE); return 1; }
    int ui = open(INPUT_DEVICE, O_WRONLY | O_NONBLOCK);
    if (ui < 0) { perror(INPUT_DEVICE); close(i2c); return 1; }
    if (make_uinput(ui) < 0) {
        perror("uinput setup");
        close(ui);
        close(i2c);
        return 1;
    }

    fprintf(stderr, "Casper GT811 uinput driver started%s\n", debug ? " [DEBUG]" : "");
    fprintf(stderr, "Polling: 20 ms; Display: 800x480\n");
    int last_down = 0, last_x = -1, last_y = -1;
    uint8_t last_raw[8] = {0};
    int have_last_raw = 0;
    struct timespec period = { .tv_sec = 0, .tv_nsec = INTERVAL_NS };

    while (running) {
        uint8_t data[8];
        if (read_touch(i2c, data) < 0) {
            if (debug) perror("GT811 I2C read");
            nanosleep(&period, NULL);
            continue;
        }
        if (data[0] == 0x20 && data[1] == 0xf0) {
            fprintf(stderr, "GT811 uninitialized? (20 F0); run panel init first\n");
            break;
        }
        int changed = !have_last_raw || memcmp(data, last_raw, 8) != 0;
        if (debug && (changed || (last_down && data[0] == 0))) {
            fprintf(stderr, "RAW %02X %02X %02X %02X %02X %02X %02X %02X down_bit=%d\n",
                    data[0], data[1], data[2], data[3],
                    data[4], data[5], data[6], data[7], !!(data[0]&1));
        }
        memcpy(last_raw, data, 8);
        have_last_raw = 1;

        /* IMPORTANT: first-bit == 0 may mean 'no NEW data', not finger-up.
         * This legacy interpretation is deliberately preserved for diagnosis.
         * Do not introduce an arbitrary debounce until raw signaling is known. */
        int down = !!(data[0] & 1);
        int raw_x = ((int)data[2] << 8) | data[3];
        int raw_y = ((int)data[4] << 8) | data[5];
        if (down && (raw_x > SCREEN_H || raw_y > SCREEN_W))
            down = 0;
        int x = SCREEN_W - raw_y;
        int y = raw_x;

        if (down != last_down) {
            if (emit(ui, EV_KEY, BTN_TOUCH, down) < 0) break;
        }
        if (down) {
            if (!last_down || x != last_x) {
                if (emit(ui, EV_ABS, ABS_X, x) < 0) break;
            }
            if (!last_down || y != last_y) {
                if (emit(ui, EV_ABS, ABS_Y, y) < 0) break;
            }
        }
        if (down != last_down ||
            (down && (x != last_x || y != last_y))) {
            if (emit(ui, EV_SYN, SYN_REPORT, 0) < 0) break;
        }
        last_down = down;
        if (down) { last_x = x; last_y = y; }
        nanosleep(&period, NULL);
    }
    if (last_down) {
        emit(ui, EV_KEY, BTN_TOUCH, 0);
        emit(ui, EV_SYN, SYN_REPORT, 0);
    }
    ioctl(ui, UI_DEV_DESTROY);
    close(ui);
    close(i2c);
    fprintf(stderr, "GT811 stopped\n");
    return 0;
}

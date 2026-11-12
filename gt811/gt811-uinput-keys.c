/*
 * Casper TAB-WB72 / Allwinner A13 / Goodix GT811
 * Userspace I2C -> Linux uinput bridge, with six capacitive bezel keys.
 *
 * Experimental derivative of gt811-uinput-ack.c (reconstructed 2026-10-28).
 * Tested hardware observations: Debian 13, Linux 6.12 #5, I2C-1 at 0x5d,
 * PG11 falling-edge IRQ, status register 0x0721, ACK command 80 00.
 *
 * The six bezel keys were measured as coordinate-like GT811 reports:
 * raw_x ~= 475, raw_y ~= 60/196/327/460/582/720.
 * These are NOT reported in a separate key bitfield on this firmware.
 * Do not install as the default until display-edge false positives are tested.
 *
 * The first report locks a contact to SCREEN or KEY until finger-up.
 * It never changes a screen touch into a key during a drag.
 */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <linux/gpio.h>
#include <linux/i2c-dev.h>
#include <linux/i2c.h>
#include <linux/input.h>
#include <linux/uinput.h>
#include <poll.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
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
#define INTERVAL_NS 5000000L
#define GT811_REPORT_LEN 34

/* Experimental conservative zones around the six measured key centers. */
#define KEY_RAW_X_MIN 470
#define KEY_RAW_X_MAX 479
#define KEY_RAW_Y_TOLERANCE 18

struct casper_key {
    int raw_y;
    unsigned short code;
    const char *name;
};

static const struct casper_key casper_keys[] = {
    {  60, KEY_MENU,       "MENU" },
    { 196, KEY_BACK,       "BACK" },
    { 327, KEY_SEARCH,     "SEARCH" },
    { 460, KEY_HOME,       "HOME" },
    { 582, KEY_VOLUMEDOWN, "VOLUMEDOWN" },
    { 720, KEY_VOLUMEUP,   "VOLUMEUP" }
};

#define KEY_COUNT (sizeof(casper_keys) / sizeof(casper_keys[0]))

static volatile sig_atomic_t running = 1;
static void on_signal(int sig) { (void)sig; running = 0; }

static int read_touch(int fd, uint8_t data[GT811_REPORT_LEN])
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
    msgs[1].len = GT811_REPORT_LEN;
    msgs[1].buf = data;
    struct i2c_rdwr_ioctl_data transfer = { .msgs = msgs, .nmsgs = 2 };
    return ioctl(fd, I2C_RDWR, &transfer) == 2 ? 0 : -1;
}

/* Original GT811 end-of-report acknowledgment, as in the working bridge. */
static int gt811_end_cmd(int fd)
{
    uint8_t cmd[2] = { 0x80, 0x00 };
    struct i2c_msg msg = {
        .addr = GT811_ADDR,
        .flags = 0,
        .len = sizeof(cmd),
        .buf = cmd
    };
    struct i2c_rdwr_ioctl_data transfer = { .msgs = &msg, .nmsgs = 1 };
    return ioctl(fd, I2C_RDWR, &transfer) == 1 ? 0 : -1;
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

static int sync_input(int fd)
{
    return emit(fd, EV_SYN, SYN_REPORT, 0);
}

/* Return the index of a key, or -1 if not inside a measured key zone. */
static int detect_casper_key(int raw_x, int raw_y)
{
    if (raw_x < KEY_RAW_X_MIN || raw_x > KEY_RAW_X_MAX)
        return -1;
    for (size_t i = 0; i < KEY_COUNT; ++i) {
        int delta = raw_y - casper_keys[i].raw_y;
        if (delta >= -KEY_RAW_Y_TOLERANCE &&
            delta <= KEY_RAW_Y_TOLERANCE)
            return (int)i;
    }
    return -1;
}

static int make_uinput(int fd)
{
    struct uinput_user_dev dev;
    memset(&dev, 0, sizeof(dev));
    snprintf(dev.name, sizeof(dev.name), "Casper Goodix GT811 Touchscreen");
    dev.id.bustype = BUS_I2C;
    dev.id.vendor = 0;
    dev.id.product = 0x0811;
    dev.id.version = 2;
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

    for (size_t i = 0; i < KEY_COUNT; ++i)
        if (ioctl(fd, UI_SET_KEYBIT, casper_keys[i].code) < 0)
            return -1;

#ifdef UI_SET_PROPBIT
    if (ioctl(fd, UI_SET_PROPBIT, INPUT_PROP_DIRECT) < 0)
        perror("UI_SET_PROPBIT(INPUT_PROP_DIRECT)");
#endif
    if (write(fd, &dev, sizeof(dev)) != (ssize_t)sizeof(dev))
        return -1;
    return ioctl(fd, UI_DEV_CREATE);
}

enum contact_kind { CONTACT_NONE, CONTACT_SCREEN, CONTACT_KEY };

int main(int argc, char **argv)
{
    int debug = 0, irq_mode = 0;
    for (int a = 1; a < argc; ++a) {
        if (strcmp(argv[a], "--debug") == 0)
            debug = 1;
        else if (strcmp(argv[a], "--irq") == 0)
            irq_mode = 1;
        else {
            fprintf(stderr, "Usage: %s [--debug] [--irq]\n", argv[0]);
            return 2;
        }
    }
    signal(SIGINT, on_signal);
    signal(SIGTERM, on_signal);

    int i2c = open(I2C_DEVICE, O_RDWR);
    if (i2c < 0) {
        perror(I2C_DEVICE);
        return 1;
    }
    int ui = open(INPUT_DEVICE, O_WRONLY | O_NONBLOCK);
    if (ui < 0) {
        perror(INPUT_DEVICE);
        close(i2c);
        return 1;
    }

    int created = 0, irq_fd = -1, exit_code = 0;
    if (make_uinput(ui) < 0) {
        perror("uinput setup");
        exit_code = 1;
        goto cleanup;
    }
    created = 1;

    if (irq_mode) {
        int chip = open("/dev/gpiochip0", O_RDONLY);
        if (chip < 0) {
            perror("open gpiochip0");
            exit_code = 1;
            goto cleanup;
        }
        struct gpio_v2_line_request req = {0};
        req.offsets[0] = 203; /* PG11 on this platform */
        req.num_lines = 1;
        snprintf(req.consumer, sizeof(req.consumer), "gt811-uinput");
        req.config.flags = GPIO_V2_LINE_FLAG_INPUT |
                           GPIO_V2_LINE_FLAG_EDGE_FALLING;
        if (ioctl(chip, GPIO_V2_GET_LINE_IOCTL, &req) < 0) {
            perror("GPIO_V2_GET_LINE_IOCTL");
            close(chip);
            exit_code = 1;
            goto cleanup;
        }
        irq_fd = req.fd;
        close(chip);
    }

    fprintf(stderr, "Casper GT811 uinput keys test started%s\n",
            debug ? " [DEBUG]" : "");
    fprintf(stderr, "Mode: %s; Display: 800x480\n",
            irq_mode ? "PG11 falling-edge IRQ" : "5 ms polling");

    enum contact_kind kind = CONTACT_NONE;
    int active_key = -1, last_x = -1, last_y = -1;
    unsigned long poll_count = 0;
    struct timespec period = { .tv_sec = 0, .tv_nsec = INTERVAL_NS };

    while (running) {
        if (irq_mode) {
            struct pollfd pfd = { .fd = irq_fd, .events = POLLIN };
            int pr = poll(&pfd, 1, 1000);
            if (pr < 0) {
                if (errno == EINTR) continue;
                perror("GPIO poll");
                exit_code = 1;
                break;
            }
            if (pr == 0) continue;
            if (!(pfd.revents & POLLIN)) {
                fprintf(stderr, "Unexpected GPIO revents=0x%x\n", pfd.revents);
                exit_code = 1;
                break;
            }
            struct gpio_v2_line_event ev;
            if (read(irq_fd, &ev, sizeof(ev)) != (ssize_t)sizeof(ev)) {
                perror("GPIO event read");
                exit_code = 1;
                break;
            }
            if (debug)
                fprintf(stderr, "IRQ seq=%u t_ms=%llu\n", ev.seqno,
                        (unsigned long long)(ev.timestamp_ns / 1000000ULL));
        }

        uint8_t data[GT811_REPORT_LEN];
        ++poll_count;
        if (read_touch(i2c, data) < 0) {
            if (debug) perror("GT811 I2C read");
            if (!irq_mode) nanosleep(&period, NULL);
            continue;
        }
        if (data[0] == 0x20 && data[1] == 0xf0) {
            fprintf(stderr, "GT811 uninitialized? (20 F0); run panel init first\n");
            exit_code = 1;
            break;
        }

        if (debug) {
            fprintf(stderr, "POLL %lu RAW", poll_count);
            for (int j = 0; j < GT811_REPORT_LEN; ++j)
                fprintf(stderr, " %02X", data[j]);
            fprintf(stderr, "\n");
        }

        /* Acknowledge every successfully read report as the working driver does. */
        if (gt811_end_cmd(i2c) < 0 && debug)
            perror("GT811 end command");

        int down = !!(data[0] & 1);
        int raw_x = ((int)data[2] << 8) | data[3];
        int raw_y = ((int)data[4] << 8) | data[5];

        /*
         * Retain the existing single-touch validity range.
         * If a contact starts in a key zone, suppress BTN_TOUCH entirely.
         * If a contact starts as SCREEN, never reinterpret it as a KEY.
         */
        if (down && (raw_x > SCREEN_H || raw_y > SCREEN_W))
            down = 0;

        if (!down) {
            if (kind == CONTACT_KEY && active_key >= 0) {
                if (emit(ui, EV_KEY, casper_keys[active_key].code, 0) < 0 ||
                    sync_input(ui) < 0) {
                    exit_code = 1;
                    break;
                }
                if (debug) fprintf(stderr, "KEY UP %s\n",
                                   casper_keys[active_key].name);
            } else if (kind == CONTACT_SCREEN) {
                if (emit(ui, EV_KEY, BTN_TOUCH, 0) < 0 ||
                    sync_input(ui) < 0) {
                    exit_code = 1;
                    break;
                }
            }
            kind = CONTACT_NONE;
            active_key = -1;
        } else if (kind == CONTACT_NONE) {
            int index = detect_casper_key(raw_x, raw_y);
            if (index >= 0) {
                kind = CONTACT_KEY;
                active_key = index;
                if (emit(ui, EV_KEY, casper_keys[index].code, 1) < 0 ||
                    sync_input(ui) < 0) {
                    exit_code = 1;
                    break;
                }
                if (debug) fprintf(stderr, "KEY DOWN %s raw=(%d,%d)\n",
                                   casper_keys[index].name, raw_x, raw_y);
            } else {
                kind = CONTACT_SCREEN;
                int x = raw_y, y = raw_x;
                if (emit(ui, EV_KEY, BTN_TOUCH, 1) < 0 ||
                    emit(ui, EV_ABS, ABS_X, x) < 0 ||
                    emit(ui, EV_ABS, ABS_Y, y) < 0 ||
                    sync_input(ui) < 0) {
                    exit_code = 1;
                    break;
                }
                last_x = x;
                last_y = y;
            }
        } else if (kind == CONTACT_SCREEN) {
            int x = raw_y, y = raw_x;
            if (x != last_x || y != last_y) {
                if ((x != last_x && emit(ui, EV_ABS, ABS_X, x) < 0) ||
                    (y != last_y && emit(ui, EV_ABS, ABS_Y, y) < 0) ||
                    sync_input(ui) < 0) {
                    exit_code = 1;
                    break;
                }
                last_x = x;
                last_y = y;
            }
        } /* CONTACT_KEY: stay held until next finger-up packet */

        if (!irq_mode) nanosleep(&period, NULL);
    }

    /* Avoid leaving keys or touch held if SIGTERM stops the bridge. */
    if (kind == CONTACT_KEY && active_key >= 0) {
        emit(ui, EV_KEY, casper_keys[active_key].code, 0);
        sync_input(ui);
    } else if (kind == CONTACT_SCREEN) {
        emit(ui, EV_KEY, BTN_TOUCH, 0);
        sync_input(ui);
    }

cleanup:
    if (irq_fd >= 0) close(irq_fd);
    if (created) ioctl(ui, UI_DEV_DESTROY);
    close(ui);
    close(i2c);
    fprintf(stderr, "GT811 keys bridge stopped\n");
    return exit_code;
}

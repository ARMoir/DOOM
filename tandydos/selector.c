/*
 * DOOM.EXE - 16-bit DOS 8086 selector for the specialized renderers.
 * Each MZ-format renderer ships as an .OVL instead of a second .EXE.
 * DOS EXEC loads the selected overlay; no launcher remains resident.
 */
#include <ctype.h>
#include <dos.h>
#include <errno.h>
#include <process.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_ARGS 32
enum video_mode { VIDEO_AUTO, VIDEO_TANDY, VIDEO_TANDY_HI, VIDEO_CGA, VIDEO_VGA };

static int same(const char *a, const char *b)
{
    while (*a && *b) {
        if (toupper((unsigned char)*a) != toupper((unsigned char)*b))
            return 0;
        ++a;
        ++b;
    }
    return *a == 0 && *b == 0;
}

static enum video_mode parse_mode(const char *arg)
{
    if (same(arg, "auto")) return VIDEO_AUTO;
    if (same(arg, "tandy") || same(arg, "tga") ||
        same(arg, "tandy-fast")) return VIDEO_TANDY;
    if (same(arg, "tandyhi") || same(arg, "tgh") ||
        same(arg, "tandy-high") || same(arg, "tandy-full"))
        return VIDEO_TANDY_HI;
    if (same(arg, "cga")) return VIDEO_CGA;
    if (same(arg, "vga")) return VIDEO_VGA;
    return (enum video_mode)-1;
}

static int has_vga(void)
{
    union REGS r;
    /* BIOS video display combination code, available on MCGA/VGA. */
    r.w.ax = 0x1a00;
    r.h.bl = 0;
    int86(0x10, &r, &r);
    if (r.h.al != 0x1a) return 0;
    /* 07/08 = VGA; 0A/0B/0C = MCGA. All support mode 13h. */
    return r.h.bl == 7 || r.h.bl == 8 ||
           r.h.bl == 10 || r.h.bl == 11 || r.h.bl == 12;
}

static int has_tandy(void)
{
    /* Tandy 1000 signatures from Doom8088's existing detector.
       PCjr model FD is deliberately excluded (different memory map). */
    const unsigned char __far *model = (const unsigned char __far *)
                                      MK_FP(0xffff, 0x000e);
    const unsigned char __far *tandy = (const unsigned char __far *)
                                      MK_FP(0xfc00, 0x0000);
    return *model == 0xff && *tandy == 0x21;
}

static enum video_mode detect_video(void)
{
    if (has_vga()) return VIDEO_VGA;
    if (has_tandy()) return VIDEO_TANDY;
    return VIDEO_CGA;
}

static const char *overlay_for(enum video_mode mode)
{
    switch (mode) {
        case VIDEO_TANDY: return "DOOMTGA.OVL";
        case VIDEO_TANDY_HI: return "DOOMTGH.OVL";
        case VIDEO_CGA: return "DOOMCGA.OVL";
        case VIDEO_VGA: return "DOOMVGA.OVL";
        default: return 0;
    }
}

static const char *wad_for(enum video_mode mode)
{
    switch (mode) {
        case VIDEO_TANDY:
        case VIDEO_TANDY_HI: return "DOOMT16.WAD";
        case VIDEO_CGA: return "DOOM4.WAD";
        case VIDEO_VGA: return "DOOM1.WAD";
        default: return 0;
    }
}

static const char *mode_name(enum video_mode mode)
{
    switch (mode) {
        case VIDEO_TANDY: return "Tandy 16-color (fast)";
        case VIDEO_TANDY_HI: return "Tandy 16-color (detail)";
        case VIDEO_CGA: return "CGA 4-color";
        case VIDEO_VGA: return "VGA 256-color";
        default: return "unknown";
    }
}

static void help(void)
{
    puts("DOOM for DOS / 8086 / Tandy 1000 / CGA / VGA");
    puts("Usage: DOOM [display switch] [game arguments]");
    puts("  (no switch)    Detect VGA, then Tandy; otherwise CGA");
    puts("  -tandy         Tandy 160x200 / 16 colors, fast");
    puts("  -tandyhi       Tandy 160x200 / 16 colors, detailed");
    puts("  -cga           Force CGA 320x200 / 4 colors");
    puts("  -vga           Force VGA 320x200 / 256 colors");
    puts("  -video MODE    auto / tandy / tandyhi / cga / vga");
    puts("  -auto          Enable automatic detection");
    puts("  -detect        Report detected mode and exit");
    puts("  -sound MODE    auto / tandy / pc (independent of video)");
    puts("  -textures MODE classic / clean (Tandy only)");
    puts("  -ambient       Enable optional short PSG demo music");
    puts("  -nomusic       Sound effects only (default)");
    puts("  -nosfx         Disable effects; use -ambient for music");
    puts("  -nosound       Disable music and effects");
    puts("  -help          Show this help");
    puts("Example: DOOM -tandy -timedemo demo3 -quick");
    puts("Other options are passed to the selected game engine.");
}

int main(int argc, char **argv)
{
    enum video_mode override = VIDEO_AUTO;
    enum video_mode detected, selected, parsed;
    const char *overlay, *wad;
    const char *launch_args[MAX_ARGS + 1];
    int i, count = 1, detect_only = 0, clean = 0;
    FILE *fp;

    for (i = 1; i < argc; ++i) {
        const char *arg = argv[i];
        if (same(arg, "-help") || same(arg, "/?") || same(arg, "-h")) {
            help();
            return 0;
        }
        if (same(arg, "-detect")) {
            detect_only = 1;
            continue;
        }
        if (same(arg, "-video")) {
            if (++i >= argc || (parsed = parse_mode(argv[i])) == (enum video_mode)-1) {
                fputs("Invalid video mode after -video. Run DOOM -help.\n", stderr);
                return 2;
            }
            override = parsed;
            continue;
        }
        if (same(arg, "-auto")) {
            override = VIDEO_AUTO;
            continue;
        }
        if (same(arg, "-tandy") || same(arg, "-tandyhi") ||
            same(arg, "-cga") || same(arg, "-vga") ||
            same(arg, "-tandy-full") || same(arg, "-tandy-fast")) {
            override = parse_mode(arg + 1);
            continue;
        }
        if (same(arg, "-textures")) {
            if (++i >= argc || (!same(argv[i],"classic") && !same(argv[i],"clean"))) {
                fputs("Use -textures classic or clean.\n", stderr); return 2;
            }
            if (count + 2 >= MAX_ARGS) return 2;
            clean = same(argv[i], "clean");
            launch_args[count++] = "-textures";
            launch_args[count++] = argv[i];
            continue;
        }
        if (count >= MAX_ARGS) {
            fputs("Too many DOOM command-line arguments.\n", stderr);
            return 2;
        }
        launch_args[count++] = arg;
    }
    detected = detect_video();
    selected = override == VIDEO_AUTO ? detected : override;
    if (detect_only) {
        printf("Detected video: %s\n", mode_name(detected));
        printf("Detected sound: %s\n",
               has_tandy() ? "Tandy PSG (ROM signature)" : "PC speaker");
        if (selected != detected)
            printf("Override: %s\n", mode_name(selected));
        return 0;
    }
    if (clean && selected != VIDEO_TANDY && selected != VIDEO_TANDY_HI) {
        fputs("-textures clean requires Tandy graphics.\n",stderr); return 2;
    }
    overlay = overlay_for(selected);
    wad = clean ? "DOOMTC.WAD" : wad_for(selected);
    fp = fopen(overlay, "rb");
    if (!fp) {
        fprintf(stderr, "Missing %s in current directory.\n", overlay);
        return 3;
    }
    fclose(fp);
    fp = fopen(wad, "rb");
    if (!fp) {
        fprintf(stderr, "Missing %s for %s.\n", wad, mode_name(selected));
        return 3;
    }
    fclose(fp);
    launch_args[0] = overlay;
    launch_args[count] = 0;
    printf("Video: %s%s\n", mode_name(selected),
           override == VIDEO_AUTO ? " (auto)" : " (forced)");
    if (selected == VIDEO_TANDY || selected == VIDEO_TANDY_HI)
        printf("Textures: %s\n", clean ? "clean" : "classic");
    fflush(stdout);
    /* DOS MZ loader will recognize the executable header inside .OVL. */
    execv(overlay, launch_args);
    fprintf(stderr, "Could not start %s (DOS error %d).\n", overlay, errno);
    return 4;
}

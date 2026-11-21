/*
 * Tandy PSG sound backend for DOOM on a 7 MHz 8088/V20.
 *
 * Hardware I/O and cached register programming follow the existing
 * TandyAMP approach (MIT); no DOS service, heap alloc, or float in IRQ.
 * Converts existing 140 Hz Muse PC-speaker effect dividers into PSG
 * notes, uses three independently prioritized voices plus noise.
 * Background melody is ORIGINAL placeholder music, not the commercial
 * DOOM soundtrack. Music yields immediately to any sound effect.
 *
 * Driver uses the existing 140 Hz task manager priority 1, the same
 * rate used by the PC-speaker path. Port 0xC0 is touched ONLY when
 * Tandy mode is selected by auto-detection or explicit -sound tandy.
 */
#include <conio.h>
#include <dos.h>
#include <stdint.h>
#include <string.h>

#include "compiler.h"
#include "doomdef.h"
#include "doomtype.h"
#include "w_wad.h"
#include "a_taskmn.h"
#include "a_tandyfx.h"

#define TFX_PORT 0xc0
#define TFX_TIMER_PRIORITY 1
#define TFX_RATE 140
#define TFX_VOICES 3
#define TFX_MAX_SAMPLES 146
#define MUSIC_STEPS 16
#define MUSIC_TICKS_PER_STEP 28

typedef struct {
    uint16_t samples[TFX_MAX_SAMPLES];
    uint16_t length, position;
    uint8_t active, attenuation;
} tfx_voice_t;

typedef struct {
    uint16_t length;
    uint16_t data[];
} tfx_muse_t;

static tfx_voice_t voices[TFX_VOICES];
static uint16_t old_tone[TFX_VOICES];
static uint8_t old_attenuation[TFX_VOICES];
static uint8_t last_noise_attenuation;
static uint8_t noise_remaining, noise_length, noise_level, noise_priority;
static uint8_t music_playing, music_loop, music_step, music_clock;
static uint8_t music_track, music_volume = 15;
static uint8_t installed;

/* Original, minimal 3-part minor-key underscore, not Doom's MIDI/MUS.
 * PSG 10-bit clock dividers at nominal 3.579 MHz; 0 denotes a rest.
 * This costs no runtime MIDI parsing or sample mixing on the EX.
 */
static const uint16_t music_notes[3][MUSIC_STEPS] = {
    {684, 0, 684, 0, 543, 0, 609, 0, 684, 0, 456, 0, 609, 0, 543, 0},
    {271, 0, 305, 342, 0, 305, 271, 0, 228, 0, 271, 305, 0, 342, 305, 0},
    {456, 0, 456, 0, 407, 0, 407, 0, 342, 0, 342, 0, 407, 0, 456, 0}
};

static void TFX_WriteTone(uint8_t channel, uint16_t divisor, uint8_t volume)
{
    uint8_t latch;
    if (!divisor) volume = 15;
    if (divisor > 1023) divisor = 1023;
    if (divisor && old_tone[channel] != divisor) {
        latch = (uint8_t)(0x80 | (channel << 5));
        outp(TFX_PORT, latch | (uint8_t)(divisor & 15));
        outp(TFX_PORT, (uint8_t)(divisor >> 4));
        old_tone[channel] = divisor;
    }
    if (old_attenuation[channel] != volume) {
        outp(TFX_PORT, (uint8_t)(0x90 | (channel << 5) | volume));
        old_attenuation[channel] = volume;
    }
}

static void TFX_WriteNoise(uint8_t attenuation)
{
    if (attenuation != last_noise_attenuation) {
        outp(TFX_PORT, 0xf0 | attenuation);
        last_noise_attenuation = attenuation;
    }
}

/* PIT channel 2 ~1193182 Hz / divisor. SN76489 tone clock runs at
 * ~3579545 Hz / (32*divider): divider ~= PIT divider*3/32.
 * Use integer arithmetic and clamp to ten hardware bits.
 */
static uint16_t TFX_PitToPSG(uint16_t pit)
{
    uint32_t divider;
    if (!pit) return 0;
    divider = ((uint32_t)pit * 3u + 16u) >> 5;
    if (divider == 0) return 1;
    if (divider > 1023) return 1023;
    return (uint16_t)divider;
}

static uint8_t TFX_ClampedAttenuation(uint8_t base, uint16_t progress,
                                     uint16_t length)
{
    uint16_t attenuation = base;
    /* Short 4-step fade prevents loud digital clicks. */
    if (length) attenuation += (uint16_t)((progress * 4u) / length);
    return attenuation > 15 ? 15 : (uint8_t)attenuation;
}

static void TFX_Service(void)
{
    uint8_t i;
    /* 140 Hz IRQ service: integer-only and no far WAD or DOS calls. */
    if (music_playing && ++music_clock >= MUSIC_TICKS_PER_STEP) {
        music_clock = 0;
        if (++music_step >= MUSIC_STEPS) {
            music_step = 0;
            if (!music_loop) music_playing = 0;
        }
    }
    for (i = 0; i < TFX_VOICES; ++i) {
        tfx_voice_t *v = &voices[i];
        if (v->active) {
            uint16_t pit = v->samples[v->position];
            uint8_t attenuation = TFX_ClampedAttenuation(
                v->attenuation, v->position, v->length);
            TFX_WriteTone(i, TFX_PitToPSG(pit), attenuation);
            if (++v->position >= v->length) v->active = 0;
        } else if (music_playing && music_volume) {
            uint8_t position = (uint8_t)((music_step + (music_track & 3u) * 4u)
                                          & (MUSIC_STEPS - 1));
            uint8_t attenuation =
                (uint8_t)(15 - (music_volume * 8u) / 15u);
            TFX_WriteTone(i, music_notes[i][position], attenuation);
        } else {
            TFX_WriteTone(i, 0, 15);
        }
    }
    if (noise_remaining) {
        uint8_t elapsed = (uint8_t)(noise_length - noise_remaining);
        TFX_WriteNoise(TFX_ClampedAttenuation(noise_level, elapsed,
                                             noise_length));
        --noise_remaining;
        if (!noise_remaining) TFX_WriteNoise(15);
    }
}

static uint8_t TFX_NoiseClass(sfxenum_t id)
{
    switch (id) {
        case sfx_pistol: case sfx_shotgn: case sfx_sgcock:
        case sfx_rlaunc: case sfx_firsht: case sfx_sgtatk:
        case sfx_sawhit: case sfx_punch: return 1;
        case sfx_rxplod: case sfx_firxpl: case sfx_barexp:
        case sfx_brssit: case sfx_brsdth: return 2;
        default: return 0;
    }
}

void TFX_Init(void)
{
    uint8_t i;
    if (installed) return;
    for (i = 0; i < TFX_VOICES; ++i) {
        voices[i].active = 0;
        old_tone[i] = 0xffffu;
        old_attenuation[i] = 15;
        outp(TFX_PORT, (uint8_t)(0x9f | (i << 5)));
    }
    outp(TFX_PORT, 0xff);
    last_noise_attenuation = 15;
    noise_remaining = music_playing = music_clock = music_step = 0;
    TS_ScheduleTask(TFX_Service, TFX_RATE, TFX_TIMER_PRIORITY);
    installed = 1;
}

int16_t TFX_Start(int16_t lumpnum, int16_t channel, int16_t volume, sfxenum_t id)
{
    const tfx_muse_t __far *muse;
    uint16_t length, bytes;
    tfx_voice_t *voice;
    uint8_t kind;
    uint8_t attenuation;

    if (channel < 0 || channel >= TFX_VOICES || !installed) return -1;
    bytes = W_LumpLength(lumpnum);
    if (bytes < 2) return -1;
    muse = (const tfx_muse_t __far *)W_GetLumpByNum(lumpnum);
    length = muse->length;
    if (length > (bytes - 2u) / 2u) length = (bytes - 2u) / 2u;
    if (length > TFX_MAX_SAMPLES) length = TFX_MAX_SAMPLES;
    if (!length) {
        Z_ChangeTagToCache(muse);
        return -1;
    }
    if (volume < 0) volume = 0;
    if (volume > 120) volume = 120;
    attenuation = (uint8_t)(15 - volume / 8);
    voice = &voices[channel];

    /* Protect the far-to-near copy and state publish from the timer ISR. */
    _disable();
    voice->active = 0;
    _fmemcpy(voice->samples, muse->data, length * sizeof(uint16_t));
    voice->length = length;
    voice->position = 0;
    voice->attenuation = attenuation;
    voice->active = 1;
    kind = TFX_NoiseClass(id);
    if (kind && (!noise_remaining || kind >= noise_priority)) {
        /* White noise: alternate fixed-rate divider per weapon class. */
        outp(TFX_PORT, kind == 2 ? 0xe6 : 0xe4);
        noise_length = kind == 2 ? 32 : 12;
        noise_remaining = noise_length;
        noise_level = attenuation < 10 ? attenuation : 10;
        noise_priority = kind;
        last_noise_attenuation = 0xff;
    }
    _enable();
    Z_ChangeTagToCache(muse);
    return channel;
}

void TFX_Stop(int16_t channel)
{
    if (!installed || channel < 0 || channel >= TFX_VOICES) return;
    _disable();
    voices[channel].active = 0;
    TFX_WriteTone((uint8_t)channel, 0, 15);
    _enable();
}

void TFX_MusicPlay(musicenum_t id, int16_t looping)
{
    if (!installed) return;
    _disable();
    music_track = (uint8_t)id;
    music_loop = looping != 0;
    music_clock = 0;
    music_step = 0;
    music_playing = 1;
    _enable();
}

void TFX_MusicStop(void)
{
    if (!installed) return;
    _disable();
    music_playing = 0;
    _enable();
}

void TFX_MusicVolume(int16_t volume)
{
    if (volume < 0) volume = 0;
    if (volume > 15) volume = 15;
    _disable();
    music_volume = (uint8_t)volume;
    _enable();
}

void TFX_Shutdown(void)
{
    uint8_t i;
    if (!installed) return;
    TS_Terminate(TFX_TIMER_PRIORITY);
    _disable();
    for (i = 0; i < TFX_VOICES; ++i) {
        voices[i].active = 0;
        outp(TFX_PORT, (uint8_t)(0x9f | (i << 5)));
    }
    outp(TFX_PORT, 0xff);
    music_playing = 0;
    noise_remaining = 0;
    installed = 0;
    _enable();
}

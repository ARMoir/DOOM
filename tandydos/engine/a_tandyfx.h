/* Native Tandy 1000 SN76489 PSG driver, real-mode 8086 safe. */
/* Hardware register caching and volume strategy adapted from TandyAMP (MIT). */
#ifndef DOOM_TANDYFX_H
#define DOOM_TANDYFX_H
#include <stdint.h>
#include "sounds.h"

void TFX_Init(void);
void TFX_Shutdown(void);
int16_t TFX_Start(int16_t lumpnum, int16_t channel, int16_t volume, sfxenum_t id);
void TFX_Stop(int16_t channel);
void TFX_MusicPlay(musicenum_t id, int16_t loop);
void TFX_MusicStop(void);
void TFX_MusicVolume(int16_t volume);
#endif

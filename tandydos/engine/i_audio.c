/* Emacs style mode select   -*- C++ -*-
 *-----------------------------------------------------------------------------
 *
 *
 *  PrBoom: a Doom port merged with LxDoom and LSDLDoom
 *  based on BOOM, a modified and improved DOOM engine
 *  Copyright (C) 1999 by
 *  id Software, Chi Hoang, Lee Killough, Jim Flynn, Rand Phares, Ty Halderman
 *  Copyright (C) 1999-2000 by
 *  Jess Haas, Nicolas Kalkhof, Colin Phipps, Florian Schulze
 *  Copyright 2005, 2006 by
 *  Florian Schulze, Colin Phipps, Neil Stevens, Andrey Budko
 *  Copyright 2023-2025 by
 *  Frenkel Smeijers
 *
 *  This program is free software; you can redistribute it and/or
 *  modify it under the terms of the GNU General Public License
 *  as published by the Free Software Foundation; either version 2
 *  of the License, or (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program; if not, write to the Free Software
 *  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
 *  02111-1307, USA.
 *
 * DESCRIPTION:
 *  System interface for sound.
 *
 *-----------------------------------------------------------------------------
 */


#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <stdint.h>
#ifdef HAVE_UNISTD_H
#include <unistd.h>
#endif

#include "z_zone.h"

#include "m_swap.h"
#include "i_sound.h"
#include "w_wad.h"
#include "s_sound.h"

#include "doomdef.h"
#include "d_player.h"
#include "doomtype.h"

#include "d_main.h"

#include "m_fixed.h"

#include "a_pcfx.h"
#include "a_tandyfx.h"
#include <dos.h>

#include "globdata.h"


/* Sound hardware is detected independently of graphics: VGA in a
 * Tandy 1000 still has the native PSG at port 0xC0.
 */
#define SOUND_PC 0
#define SOUND_TANDY 1

static int16_t sound_device = SOUND_PC;
static int16_t firstsfx;
extern int myargc;
extern char **myargv;

static int16_t I_HasTandyPSG(void)
{
    const uint8_t __far *model =
        (const uint8_t __far *)MK_FP(0xffff, 0x000e);
    const uint8_t __far *signature =
        (const uint8_t __far *)MK_FP(0xfc00, 0x0000);
    return *model == 0xff && *signature == 0x21;
}

int16_t I_SoundChannels(void)
{
    return sound_device == SOUND_TANDY ? 3 : 1;
}

int16_t I_StartSound(sfxenum_t id, int16_t channel, int16_t vol, int16_t sep)
{
    int16_t lumpnum;
    UNUSED(sep);
    if (nosfxparm) return -1;
    lumpnum = firstsfx + id;
    if (sound_device == SOUND_TANDY)
        return TFX_Start(lumpnum, channel, vol, id);
    if (channel != 0) return -1;
    PCFX_Play(lumpnum);
    return channel;
}

void I_StopSound(int16_t channel)
{
    if (sound_device == SOUND_TANDY) TFX_Stop(channel);
    else if (channel == 0) PCFX_StopSound();
}

void I_InitSound(void)
{
    int16_t i = M_CheckParm("-sound");
    sound_device = I_HasTandyPSG() ? SOUND_TANDY : SOUND_PC;

    if (i && i + 1 < myargc) {
        if (stricmp(myargv[i + 1], "pc") == 0) sound_device = SOUND_PC;
        else if (stricmp(myargv[i + 1], "tandy") == 0)
            sound_device = SOUND_TANDY;
        else if (stricmp(myargv[i + 1], "auto") != 0) {
            printf("Unknown -sound mode. Use auto, tandy or pc.\n");
            sound_device = SOUND_PC;
        }
    }
    /* The 16-step demo loop is deliberately OPT-IN. Hearing it on every
       level/attract screen was repetitive on a real Tandy EX. Native
       weapon and monster PSG sound effects stay on by default. */
    nomusicparm = (sound_device != SOUND_TANDY ||
                   !M_CheckParm("-ambient") ||
                   M_CheckParm("-nomusic") ||
                   M_CheckParm("-nosound"));
    if (M_CheckParm("-nosound")) nosfxparm = true;
    if (M_CheckParm("-nosfx")) nosfxparm = true;
    if (nomusicparm && nosfxparm) {
        printf("I_InitSound: sound disabled\n");
        return;
    }

    if (sound_device == SOUND_TANDY) {
        TFX_Init();
        printf("I_InitSound: Tandy PSG 3 tones + noise%s\n",
               nomusicparm ? " (effects only)" : " (original ambient music, opt-in)");
    } else {
        PCFX_Init();
        printf("I_InitSound: PC speaker (one voice)\n");
    }
}

void I_InitSound2(void)
{
    firstsfx = W_GetNumForName("DPPISTOL") - 1;
}

void I_ShutdownSound(void)
{
    if (nomusicparm && nosfxparm) return;
    if (sound_device == SOUND_TANDY) TFX_Shutdown();
    else PCFX_Shutdown();
}

void I_PlaySong(musicenum_t handle, boolean looping)
{
    if (!nomusicparm && sound_device == SOUND_TANDY)
        TFX_MusicPlay(handle, looping);
}


void I_StopSong(musicenum_t handle)
{
    UNUSED(handle);
    if (sound_device == SOUND_TANDY) TFX_MusicStop();
}

void I_SetMusicVolume(int16_t volume)
{
    if (sound_device == SOUND_TANDY) TFX_MusicVolume(volume);
}

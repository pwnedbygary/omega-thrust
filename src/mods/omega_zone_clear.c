/* Trusted plugin for the hidden test package omega.debug.zone-clear. While its
 * feature is enabled, a zone that runs the shared wave timeline ends as
 * cleared as soon as the player is in play, through the game's own clear path,
 * so scripted runs reach a zone's results, and the campaign step after it,
 * without live play. Runs have checked it in the 1ST to 4TH ZONE of CAMPAIGN
 * PLAY. The 5TH ZONE, the LAST ZONE, U5, U9 and V5 have no timeline runner
 * and call the clear routine from their own code, so they are not cleared.
 * The 8TH ZONE, U4 and U8 have the runner and also call the routine from
 * their own code; how that meets a forced clear is untested.
 *
 * A zone ends when its wave timeline reaches an empty entry. The runner's
 * update (0x80071544, runner object in $s0) then counts the word at +0xC down
 * to zero and calls the clear routine 0x80034104 for the player object whose
 * pointer is at 0x8009C064; that routine moves the object's state word (+0x128)
 * from 3, in play, to 6 or 7. The plugin sets the countdown to 1 just before
 * the runner loads it, so the clear runs in that same update.
 *
 * The results rate a zone by its destroy ratio, enemies destroyed (0x800A794C)
 * over enemies spawned so far (0x800A794A), and its clear time. With the
 * option all-destroyed the plugin waits until an enemy has spawned and counts
 * every spawned enemy as destroyed, so a quick clear rates S. Without it
 * nothing has been destroyed, and the zone rates low: D in zones 2 to 4, B in
 * the 1ST ZONE, whose destroy factor is 0.5 at a ratio of 0. */
#include <string.h>

#include "mod_plugins.h"
#include "cpu_state.h"

#define RUNNER_TICK 0x80071558u
#define RUNNER_TICK_WORD 0x8E02000Cu /* lw $v0, 0xC($s0) */
#define RUNNER_COUNTDOWN 0xCu
#define PLAYER_POINTER 0x8009C064u
#define PLAYER_STATE 0x128u
#define PLAYER_IN_PLAY 3u
#define ENEMIES_SPAWNED 0x800A794Au
#define ENEMIES_DESTROYED 0x800A794Cu

static int all_destroyed(void) {
    char value[8];
    return psx_mod_current_option_value("all-destroyed", value, sizeof value) &&
           strcmp(value, "true") == 0;
}

static void clear_at_runner_tick(struct CPUState* cpu, uint32_t address) {
    (void)address;
    const uint32_t runner = cpu->gpr[16];
    if (psx_mod_read_word(runner + RUNNER_COUNTDOWN) != 0) return;
    const uint32_t player = psx_mod_read_word(PLAYER_POINTER);
    if (player == 0 ||
            psx_mod_read_word(player + PLAYER_STATE) != PLAYER_IN_PLAY)
        return;
    if (all_destroyed()) {
        const uint16_t spawned = psx_mod_read_half(ENEMIES_SPAWNED);
        if (spawned == 0) return;
        psx_mod_write_half(ENEMIES_DESTROYED, spawned);
    }
    psx_mod_write_word(runner + RUNNER_COUNTDOWN, 1);
    psx_mod_counter_add("omega.zone-clear.clears", 1);
}

PSX_MOD_CONSTRUCTOR(omega_register_zone_clear) {
    (void)psx_mod_register_instruction_plugin("omega.zone-clear", RUNNER_TICK,
                                              RUNNER_TICK_WORD,
                                              clear_at_runner_tick);
}

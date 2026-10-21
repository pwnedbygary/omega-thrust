/* Trusted plugin for the package omega.cheat.unlock-all. While its feature is
 * enabled, it keeps SCUS-94449's own unlock flags set: one byte per zone at
 * 0x800A7E20 (Z1 to Z9, U1 to U9, V5) and one per boost level at 0x800A7E34
 * (1 to 9, A to E). ZONE PLAY and DEMONSTRATION read these bytes, and LOAD/SAVE
 * stores them with the environment data. The next byte of each array (A[19],
 * B[14]) has no zone or level on screen, so it is left alone. Layout:
 * docs/MODDING_FEASIBILITY.md, "Unlocks and the save". */
#include "mod_plugins.h"

#define ZONE_FLAGS 0x800A7E20u
#define ZONE_COUNT 19u
#define LEVEL_FLAGS 0x800A7E34u
#define LEVEL_COUNT 14u

static void set_flags(uint32_t base, uint32_t count) {
    for (uint32_t i = 0; i < count; ++i) {
        if (psx_mod_read_byte(base + i) == 1) continue;
        psx_mod_write_byte(base + i, 1);
        psx_mod_counter_add("omega.unlock-all.writes", 1);
    }
}

static void unlock_all_vblank(void) {
    /* Until the game's EXE starts, this RAM belongs to the BIOS. */
    if (!psx_mod_game_started()) return;
    set_flags(ZONE_FLAGS, ZONE_COUNT);
    set_flags(LEVEL_FLAGS, LEVEL_COUNT);
}

PSX_MOD_CONSTRUCTOR(omega_register_unlock_all) {
    (void)psx_mod_register_vblank_plugin("omega.unlock-all", unlock_all_vblank);
}

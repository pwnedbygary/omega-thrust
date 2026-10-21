/* Trusted plugin for the package omega.gameplay.branching. While its feature
 * is enabled, the grade of the 1ST ZONE picks the campaign's path: an S sends
 * the player straight to the 3RD ZONE, then back to the 2ND ZONE and the movie
 * after it, and on to the 4TH ZONE; any other grade keeps the stock order.
 * Every zone is still played once, so all nine result records are written.
 *
 * The campaign loop (0x8002F814) walks a 17-step script of {kind, scene index}
 * at 0x8001232C, with the script pointer in $s0 and the step in $s1. Only
 * after a step that lets the campaign go on does it reach the step-limit check
 * at 0x8002FB2C, with both already advanced; the plugin rewrites them there.
 * The rules read only the result records, which the campaign resets when it
 * starts, so the plugin keeps no state. Layout: docs/MODDING_FEASIBILITY.md,
 * "The campaign". */
#include "mod_plugins.h"
#include "cpu_state.h"

#define STEP_CHECK 0x8002FB2Cu
#define STEP_CHECK_WORD 0x2E220011u /* sltiu $v0, $s1, 17 */
#define STEP_BYTES 8u
#define STEP_SCENE 4u

/* One record of 0x24 bytes per campaign zone, by scene index minus 3. The
 * grade is 0 (S) to 4 (D), and 6 until the zone has been played. */
#define RECORDS 0x800A7AA8u
#define RECORD_BYTES 0x24u
#define RECORD_GRADE 0x1Cu
#define GRADE_S 0u
#define GRADE_LOWEST 4u

#define STEP_ZONE1 1u
#define STEP_ZONE2 2u
#define STEP_ZONE3 4u
#define STEP_ZONE4 5u
#define SCENE_ZONE1 3u
#define SCENE_ZONE2 4u
#define SCENE_ZONE3 5u

static uint32_t grade(uint32_t scene) {
    return psx_mod_read_word(RECORDS + (scene - SCENE_ZONE1) * RECORD_BYTES +
                             RECORD_GRADE);
}

static int played(uint32_t scene) {
    return grade(scene) <= GRADE_LOWEST;
}

static int stock_script(uint32_t script) {
    return psx_mod_read_word(script + STEP_ZONE1 * STEP_BYTES + STEP_SCENE) ==
               SCENE_ZONE1 &&
           psx_mod_read_word(script + STEP_ZONE2 * STEP_BYTES + STEP_SCENE) ==
               SCENE_ZONE2 &&
           psx_mod_read_word(script + STEP_ZONE3 * STEP_BYTES + STEP_SCENE) ==
               SCENE_ZONE3;
}

static void branch_at_step_check(struct CPUState* cpu, uint32_t address) {
    (void)address;
    const uint32_t next = cpu->gpr[17];
    const uint32_t script = cpu->gpr[16] - next * STEP_BYTES;
    uint32_t target = next;
    if (!stock_script(script)) return;
    if (next == STEP_ZONE2 && grade(SCENE_ZONE1) == GRADE_S &&
            !played(SCENE_ZONE2))
        target = STEP_ZONE3;
    else if (next == STEP_ZONE4 && !played(SCENE_ZONE2))
        target = STEP_ZONE2;
    else if (next == STEP_ZONE3 && played(SCENE_ZONE3))
        target = STEP_ZONE4;
    if (target == next) return;
    cpu->gpr[16] = script + target * STEP_BYTES;
    cpu->gpr[17] = target;
    psx_mod_counter_add("omega.branching.redirects", 1);
}

PSX_MOD_CONSTRUCTOR(omega_register_branching) {
    (void)psx_mod_register_instruction_plugin("omega.branching", STEP_CHECK,
                                              STEP_CHECK_WORD,
                                              branch_at_step_check);
}

/* Trusted plugin for the package omega.enhancement.gamepad-strafe. While its
 * feature is enabled, a gamepad's right stick strafes the mech in flight: it
 * moves the mech up, left, down and right relative to the view without
 * turning it, faster the further the stick is pushed, also while SCAN is
 * held, and the camera falls behind and catches up as it does for Mouse Aim's
 * keys (omega_strafe.c). The left stick steers as in the game, which ignores
 * the right stick in flight.
 *
 * Mouse Aim, while it drives player 1, replaces the gamepad's sticks with the
 * mouse and the keys, and its keys strafe through the same hooks; this plugin
 * then leaves the strafe to it, so that no step is strafed twice. */
#include <stdlib.h>

#include "mod_plugins.h"
#include "omega_mouse_aim.h"
#include "omega_strafe.h"

/* Omega Boost's RAM. */
#define GAME_STATE 0x8009C5B0u          /* word: the state the main loop runs */
#define STATE_CAMPAIGN 8u
#define STATE_ZONE_PLAY 9u
#define STATE_TRAINING 11u

#define PLAYER_1 0u                  /* the mod API counts players from 0 */

/* The force per step that a full push of the right stick adds. */
static double strafe_force = OMEGA_STRAFE_CRUISE_FORCE * 0.5;

/* Whether the pad flies the mech: in CAMPAIGN PLAY, ZONE PLAY or TRAINING,
 * the states in which Mouse Aim drives player 1. A DEMONSTRATION replay runs
 * in another state, so the stick does not strafe it; whether the replay that
 * ZONE PLAY's results screen offers runs in one of these is not known. */
static int pad_flies(void) {
    const uint32_t state = psx_mod_read_word(GAME_STATE);
    return state == STATE_CAMPAIGN || state == STATE_ZONE_PLAY ||
           state == STATE_TRAINING;
}

/* Whether the right stick strafes for this plugin: while the pad flies the
 * mech and Mouse Aim does not drive player 1. */
static int stick_strafes(void) {
    return pad_flies() && !omega_mouse_aim_drives_player_1();
}

/* The instruction hooks at the two force sums. */
static void strafe_at_force_sum(struct CPUState* cpu, uint32_t address) {
    (void)address;
    if (stick_strafes() &&
            omega_strafe(cpu, OMEGA_STRAFE_USUAL, strafe_force))
        psx_mod_counter_add("omega.gamepad-strafe.strafed-steps", 1);
}

static void strafe_at_scan_force_sum(struct CPUState* cpu, uint32_t address) {
    (void)address;
    if (stick_strafes() &&
            omega_strafe(cpu, OMEGA_STRAFE_SCAN, strafe_force))
        psx_mod_counter_add("omega.gamepad-strafe.scan-strafed-steps", 1);
}

/* Each session start: read the strafe speed, in percent of the cruising
 * speed, and present player 1 as an analog pad, so that the game reads the
 * sticks and the pad record holds the right stick. */
static void gamepad_strafe_activate(void) {
    char value[16];
    if (psx_mod_current_option_value("strafe-speed", value, sizeof value))
        strafe_force = OMEGA_STRAFE_CRUISE_FORCE * strtod(value, NULL) / 100.0;
    if (!psx_mod_set_controller_mode_override(PLAYER_1,
                                              PSX_MOD_CONTROLLER_ANALOG))
        psx_mod_counter_add("omega.gamepad-strafe.mode-failures", 1);
}

PSX_MOD_CONSTRUCTOR(omega_register_gamepad_strafe) {
    (void)psx_mod_register_activation_plugin("omega.gamepad-strafe",
                                             gamepad_strafe_activate);
    (void)psx_mod_register_instruction_plugin(
        "omega.gamepad-strafe", OMEGA_STRAFE_FORCE_SUM,
        OMEGA_STRAFE_FORCE_SUM_WORD, strafe_at_force_sum);
    (void)psx_mod_register_instruction_plugin(
        "omega.gamepad-strafe", OMEGA_STRAFE_SCAN_FORCE_SUM,
        OMEGA_STRAFE_FORCE_SUM_WORD, strafe_at_scan_force_sum);
}

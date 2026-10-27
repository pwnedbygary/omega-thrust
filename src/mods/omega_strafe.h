/* The strafe that Mouse Aim and Gamepad Strafe share: at the point where two
 * of the player's three movements add up a step's forces, a force along the
 * screen's right and down axes from the right stick in the pad record. How
 * the movements, the axes and the camera work is in omega_strafe.c. Each
 * plugin registers its own instruction hooks at the two sites and calls
 * omega_strafe() from them while its feature drives the right stick. */
#ifndef OMEGA_STRAFE_H
#define OMEGA_STRAFE_H

struct CPUState;

/* The two hook sites, both listed in game.toml's [recompiler]
 * mod_instruction_sites: the instruction at which the usual movement, and
 * SCAN's, have stored the step's x and y force sums and are about to load
 * the z sum. */
#define OMEGA_STRAFE_FORCE_SUM 0x80033044u
#define OMEGA_STRAFE_SCAN_FORCE_SUM 0x800337CCu
#define OMEGA_STRAFE_FORCE_SUM_WORD 0x8E020024u /* lw $v0, 0x24($s0), at both */

/* The thrust that the game adds along the heading each step, for a cruising
 * speed of about 320 units a step. A strafe speed in percent of the cruising
 * speed is the same percentage of this force. */
#define OMEGA_STRAFE_CRUISE_FORCE 0x238E3

/* The movement that a hook site is in, which decides the screen's axes. */
enum omega_strafe_movement {
    OMEGA_STRAFE_USUAL, /* 0x80032D50, at OMEGA_STRAFE_FORCE_SUM */
    OMEGA_STRAFE_SCAN   /* 0x800334D8, at OMEGA_STRAFE_SCAN_FORCE_SUM */
};

/* At a hook site of that movement, if the object in $s0 is the player's and
 * in play, and the right stick is pushed past the game's deadzone: add the
 * push, as a fraction of a full push, times full_force along the screen's
 * right and down axes, to the step's force sums and to the forces the camera
 * is pushed against. Returns 1 if it added a force, 0 if not. */
int omega_strafe(const struct CPUState* cpu,
                 enum omega_strafe_movement movement, double full_force);

#endif

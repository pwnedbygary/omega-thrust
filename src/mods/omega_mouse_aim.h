/* What the Mouse Aim plugin (omega_mouse_aim.c) tells the other plugins. */
#ifndef OMEGA_MOUSE_AIM_H
#define OMEGA_MOUSE_AIM_H

/* Whether Mouse Aim's controller source drives player 1: in flight, while
 * its feature is enabled. The source then replaces player 1's sticks with the
 * mouse and the keys, and the keys strafe. */
int omega_mouse_aim_drives_player_1(void);

#endif

/* The strafe that Mouse Aim and Gamepad Strafe share (omega_strafe.h). */
#include <math.h>
#include <stdlib.h>

#include "mod_plugins.h"
#include "cpu_state.h"
#include "omega_strafe.h"

/* Omega Boost's RAM. */
#define PLAYER_POINTER 0x8009C064u      /* word: the player's object */
#define PLAYER_STATE 0x128u             /* offset of its state word */
#define PLAYER_IN_PLAY 3u

/* The player's movement, 0x80032D50 with the moving object in $s0, adds up
 * the step's forces in the object's words +0x1C, +0x20 and +0x24, then turns
 * them into velocity, with drag, and into position. When the instruction at
 * 0x80033044 is about to run, the x and y sums are stored and the z sum is
 * about to be loaded, on the way to both drag paths, so a force added there
 * moves the mech as its thrust does. Thrust normally adds
 * OMEGA_STRAFE_CRUISE_FORCE along the heading each step. Where the stage
 * itself moves the player along z, the game drops the z part of the thrust,
 * and the strafe does the same.
 *
 * While SCAN is held (L1 in the game's setup, Q in controls/keybinds.ini),
 * the game runs another movement, 0x800334D8, which ends as that one does:
 * the same instruction, at 0x800337CC, comes at the same point. It thrusts
 * along the view, which the camera follows, rather than the heading, and it
 * slides the mech with the left stick along a rotation that 0x80031ABC builds
 * earlier in the step from the view's angles. The strafe there moves the
 * mech along the same rotation. Where the stage names a target and does not
 * move the player along z, the slide also pulls the mech along the direction
 * the view turns toward (0x8003A0E0), which the strafe does not.
 *
 * After a press of a boost key, in SCAN or not, the game runs a third
 * movement, 0x80032414, which has no hook, so the right stick does not strafe
 * while it runs: 18 steps, or 6 if the boost is a sideways dash, as it is
 * while the word at 0x800A7EF4 is set and the left stick is past half way
 * (0x80032144).
 *
 * The camera (0x800630B4) hangs behind the mech on a spring, pushed against
 * the step's thrust and the forces in the player's words +0xBC, +0xC0 and
 * +0xC4, which the game clears at the start of each step (0x80030580): it
 * falls behind as the mech speeds up and catches up when the push ends. The
 * game's SCAN slide adds its sideways force to those words as well as to the
 * sums (0x80031CCC), and the strafe does the same, so the mech slides across
 * the screen as it strafes. */
#define REG_S0 16
#define PLAYER_FORCE 0x1Cu              /* offset of its force words: x, y, z */
#define PLAYER_CAMERA_FORCE 0xBCu       /* offset of the force words the
                                           camera is pushed against */
#define PLAYER_VIEW_ROTATION 0x40u      /* offset of the rotation built from
                                           the view's angles */
#define ROTATION_ONE 4096.0             /* 1.0 in its 4.12 fixed point */
#define PLAYER_PITCH 0x8Cu              /* binary angles: 2^32 to a turn */
#define PLAYER_YAW 0x90u
#define STAGE_POINTER 0x8009C030u       /* word: the stage's parameters */
#define STAGE_SCROLLS 0x4Cu             /* word: non-zero if it moves along z */

/* The pad record, which the zone loop copies into the game's pad buffer each
 * step (0x8002BAB4): byte 1 is the pad's id, with 7 in its high nibble for an
 * analog pad, and bytes 4 and 5 hold the right stick, centred and signed, in
 * steps of 16 from -128 (left, up) to 112 (right, down). The strafe reads the
 * record: in the buffer, which the player's movement reads, those two bytes
 * stayed zero in every probe sample, also while the stick was pushed. */
#define PAD_RECORD 0x8009C590u
#define PAD_ID 1u
#define PAD_ANALOG 0x7u
#define PAD_RIGHT_X 4u
#define PAD_RIGHT_Y 5u
#define STICK_FULL 112                  /* a stick pushed all the way */
#define STICK_DEADZONE 32               /* the game's, for the left stick */

#define TURN_RADIANS 6.283185307179586
#define BINARY_ANGLE_TURN 4294967296.0

/* A pad record byte as the signed value it holds. */
static int signed_byte(uint8_t byte) {
    return byte < 0x80 ? byte : byte - 0x100;
}

/* A stick axis as a fraction of a full push, from -1 to 1. */
static double push_fraction(int value) {
    const double fraction = (double)value / STICK_FULL;
    return fraction < -1.0 ? -1.0 : fraction > 1.0 ? 1.0 : fraction;
}

/* The right stick from the pad record, at most a full push in any direction,
 * with left and up negative; 0 if the pad is not analog or the stick is
 * within the game's deadzone on both axes. */
static int right_stick(double* x, double* y) {
    if ((psx_mod_read_byte(PAD_RECORD + PAD_ID) >> 4) != PAD_ANALOG) return 0;
    const int rx = signed_byte(psx_mod_read_byte(PAD_RECORD + PAD_RIGHT_X));
    const int ry = signed_byte(psx_mod_read_byte(PAD_RECORD + PAD_RIGHT_Y));
    if (abs(rx) <= STICK_DEADZONE && abs(ry) <= STICK_DEADZONE) return 0;
    *x = push_fraction(rx);
    *y = push_fraction(ry);
    const double push = hypot(*x, *y);
    if (push > 1.0) {
        *x /= push;
        *y /= push;
    }
    return 1;
}

static double radians(uint32_t binary_angle) {
    return binary_angle * (TURN_RADIANS / BINARY_ANGLE_TURN);
}

static int stage_scrolls(void) {
    const uint32_t stage = psx_mod_read_word(STAGE_POINTER);
    return stage != 0 && psx_mod_read_word(stage + STAGE_SCROLLS) != 0;
}

static void add_to_word(uint32_t address, uint32_t value) {
    psx_mod_write_word(address, psx_mod_read_word(address) + value);
}

/* A function that gives the screen's right and down axes in one of the
 * player's movements. */
typedef void ScreenAxes(uint32_t player, double right[3], double down[3]);

/* The screen's right and down axes in the player's usual movement. The game's
 * y axis points up: climbing raises y, turning right lowers the yaw and a
 * positive pitch points the nose down, so for pitch p and yaw y the mech heads
 * along (cos p sin y, -sin p, cos p cos y). The camera follows the heading but
 * not the mech's roll, so screen right is the way the heading turns as the yaw
 * falls, (-cos y, 0, sin y), and screen down the way it turns as the pitch
 * rises, (-sin p sin y, -cos p, -sin p cos y). */
static void heading_axes(uint32_t player, double right[3], double down[3]) {
    const double pitch = radians(psx_mod_read_word(player + PLAYER_PITCH));
    const double yaw = radians(psx_mod_read_word(player + PLAYER_YAW));
    right[0] = -cos(yaw);
    right[1] = 0.0;
    right[2] = sin(yaw);
    down[0] = -sin(pitch) * sin(yaw);
    down[1] = -cos(pitch);
    down[2] = -sin(pitch) * cos(yaw);
}

/* A halfword of the game's RAM as the signed value it holds. */
static int signed_half(uint16_t half) {
    return half < 0x8000 ? half : half - 0x10000;
}

/* One entry of the rotation at PLAYER_VIEW_ROTATION, which holds three rows
 * of three signed halfwords. */
static double view_rotation_entry(uint32_t player, uint32_t row,
                                  uint32_t column) {
    const uint32_t entry = player + PLAYER_VIEW_ROTATION +
                           2u * (3u * row + column);
    return signed_half(psx_mod_read_half(entry)) / ROTATION_ONE;
}

/* The screen's right and down axes in SCAN's movement: minus the first and
 * minus the second column of the rotation built from the view's angles. It
 * includes the view's roll, which the camera follows, and the game's own
 * slide moves the mech along the same axes. */
static void view_axes(uint32_t player, double right[3], double down[3]) {
    for (uint32_t row = 0; row < 3; row++) {
        right[row] = -view_rotation_entry(player, row, 0);
        down[row] = -view_rotation_entry(player, row, 1);
    }
}

int omega_strafe(const struct CPUState* cpu,
                 enum omega_strafe_movement movement, double full_force) {
    const uint32_t player = psx_mod_read_word(PLAYER_POINTER);
    double right, down;
    if (player == 0 || cpu->gpr[REG_S0] != player ||
            psx_mod_read_word(player + PLAYER_STATE) != PLAYER_IN_PLAY ||
            !right_stick(&right, &down))
        return 0;
    ScreenAxes* screen_axes =
        movement == OMEGA_STRAFE_SCAN ? view_axes : heading_axes;
    double screen_right[3], screen_down[3];
    screen_axes(player, screen_right, screen_down);
    double force[3];
    for (uint32_t axis = 0; axis < 3; axis++)
        force[axis] = right * screen_right[axis] + down * screen_down[axis];
    if (stage_scrolls()) force[2] = 0.0;
    for (uint32_t axis = 0; axis < 3; axis++) {
        const uint32_t added = (uint32_t)lround(force[axis] * full_force);
        add_to_word(player + PLAYER_FORCE + 4u * axis, added);
        add_to_word(player + PLAYER_CAMERA_FORCE + 4u * axis, added);
    }
    return 1;
}

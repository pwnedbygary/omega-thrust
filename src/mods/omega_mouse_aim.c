/* Trusted plugin for the package omega.enhancement.mouse-aim. While its
 * feature is enabled, the mouse aims the mech and the keys move it whenever
 * the game is in flight: moving the mouse steers, the keyboard's left-stick
 * keys (W, A, S, D and the arrows in controls/keybinds.ini) strafe, holding
 * the left button lets the game lock on and releasing it launches the homing
 * lasers, and holding the right button keeps firing the laser rifle.
 *
 * The framework's local mouse policy (psxrecomp/docs/LOCAL_MOUSE_POLICY.md)
 * captures the mouse only while the left button is held and moves only the
 * right stick, but Omega Boost steers with the left stick and the left button
 * is a weapon here. So the plugin puts the game window in SDL's relative mouse
 * mode itself and drives player 1 through a controller source: the mouse
 * moves the left stick, and the stick keys move the right stick, which the
 * game ignores and an instruction hook in the player's movement turns into a
 * sideways force. For that it relies on more than mod_plugins.h: on psx_sdl.h
 * (SDL3) and on psx_keybinds.h (the keyboard's stick keys), which a framework
 * update must re-check. All its callbacks run on the main thread, which owns
 * the SDL window: the activation callback at session start, before the window
 * exists, and the others in the emulation loop. */
#include <math.h>
#include <stdlib.h>
#include <string.h>

#include "mod_plugins.h"
#include "cpu_state.h"
#include "psx_keybinds.h"
#include "psx_sdl.h"

#if !defined(PSX_SDL3)
#error "omega_mouse_aim.c uses SDL3's relative mouse mode"
#endif

/* Omega Boost's RAM. */
#define GAME_STATE 0x8009C5B0u          /* word: the state the main loop runs */
#define STATE_CAMPAIGN 8u
#define STATE_ZONE_PLAY 9u
#define STATE_TRAINING 11u
#define PLAYER_POINTER 0x8009C064u      /* word: the player's object */
#define PLAYER_STATE 0x128u             /* offset of its state word */
#define PLAYER_IN_PLAY 3u
#define PLAYER_SCRIPTED 2u              /* a scripted sequence, e.g. zone 1's
                                           fly-by, set by 0x800341C0 */
#define PAUSED 0x800A7A10u              /* byte: 1 while paused */
#define TYPE_SETTING 0x800A7E50u        /* word: CONTROL SETUPS' TYPE */
#define TYPE_UP_FLIES_DOWN 0u           /* TYPE A, the game's default */
#define TYPE_UP_FLIES_UP 1u             /* TYPE B */
#define ZONE_ATTACK_BUTTONS 0x800A7C40u /* word: ATTACK's keys, zone copy */
#define DEFAULT_ATTACK_BUTTONS 0xC0u    /* the game's default: Cross, Square */

/* The player's movement, 0x80032D50 with the moving object in $s0, adds up
 * the step's forces in the object's words +0x1C, +0x20 and +0x24, then turns
 * them into velocity, with drag, and into position. When the instruction at
 * 0x80033044 is about to run, the x and y sums are stored and the z sum is
 * about to be loaded, on the way to both drag paths, so a force added there
 * moves the mech as its thrust does. Thrust normally adds CRUISE_FORCE along
 * the heading each step, for a cruising speed of about 320 units a step.
 * Where the stage itself moves the player along z, the game drops the z part
 * of the thrust, and the strafe does the same. */
#define FORCE_SUM 0x80033044u
#define FORCE_SUM_WORD 0x8E020024u      /* lw $v0, 0x24($s0) */
#define REG_S0 16
#define PLAYER_FORCE 0x1Cu              /* offset of its force words: x, y, z */
#define PLAYER_PITCH 0x8Cu              /* binary angles: 2^32 to a turn */
#define PLAYER_YAW 0x90u
#define CRUISE_FORCE 0x238E3
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

/* The pad. */
#define PLAYER_1 0u                  /* the mod API counts players from 0 */
#define KEYBINDS_PLAYER_1 1          /* psx_keybinds counts them from 1 */
#define STICK_CENTRE 128
#define STICK_MAX 255
#define ALL_BUTTONS_RELEASED 0xFFFFu /* the pad word is active low */

/* Omega Boost runs its game logic every other frame (its replays hold one
 * input for each two frames), so it reads only every second pad sample: a
 * press must last two frames to be seen, and a release two frames to count.
 * The launch press lasts four frames, so that it is seen even if the game
 * takes up to four frames between two reads; a rifle press missed in a held
 * stream costs only one shot. */
#define LAUNCH_PRESS_FRAMES 4
#define RIFLE_PRESS_FRAMES 2
#define RIFLE_RELEASE_FRAMES 2

#define TURN_RADIANS 6.283185307179586
#define BINARY_ANGLE_TURN 4294967296.0

static struct {
    double gain;           /* stick units per pixel moved in one frame */
    double strafe_force;   /* force per step with a stick key held */
    uint32_t type;         /* the TYPE setting the plugin keeps */
    int attached;          /* whether the source drives player 1 */
    SDL_Window* captured;  /* the window in relative mouse mode, or NULL */
    float last_x, last_y;  /* the mouse's movement in the previous frame */
    int left_was_down;
    int launch_frames;     /* frames of the launch press still to give */
    int rifle_frame;       /* position in the right button's press cycle */
} aim = {.gain = 4.0, .strafe_force = CRUISE_FORCE * 0.5,
         .type = TYPE_UP_FLIES_UP};

/* Whether the player is flying: in CAMPAIGN PLAY, ZONE PLAY or TRAINING, with
 * the player's object in play or in a scripted sequence. Mouse Aim stays on
 * through a sequence, so the cursor does not flicker free and back, and a
 * button held across one is still seen. */
static int in_flight(void) {
    const uint32_t state = psx_mod_read_word(GAME_STATE);
    if (state != STATE_CAMPAIGN && state != STATE_ZONE_PLAY &&
            state != STATE_TRAINING)
        return 0;
    const uint32_t player = psx_mod_read_word(PLAYER_POINTER);
    if (player == 0) return 0;
    const uint32_t player_state = psx_mod_read_word(player + PLAYER_STATE);
    return player_state == PLAYER_IN_PLAY || player_state == PLAYER_SCRIPTED;
}

/* The first pad button that the game's key setup gives ATTACK. The setup is a
 * mask of the pad word's high byte, which each zone copies when it starts;
 * while that copy is empty, the game's default setup. */
static uint32_t attack_button(void) {
    uint32_t mask = psx_mod_read_word(ZONE_ATTACK_BUTTONS) & 0xFFu;
    if (mask == 0) mask = DEFAULT_ATTACK_BUTTONS;
    uint32_t lowest = 1;
    while (!(mask & lowest)) lowest <<= 1;
    return lowest << 8;
}

/* Whether ATTACK is pressed this frame, given the mouse buttons. The game has
 * one ATTACK action: each press fires one rifle shot and launches the homing
 * lasers at every target locked so far, and targets lock on by themselves
 * while ATTACK is not pressed. So releasing the left button presses ATTACK
 * once, and holding the right button presses it again and again. */
static int attack_pressed(SDL_MouseButtonFlags buttons) {
    const int left = (buttons & SDL_BUTTON_LMASK) != 0;
    if (aim.left_was_down && !left) {
        aim.launch_frames = LAUNCH_PRESS_FRAMES;
        psx_mod_counter_add("omega.mouse-aim.launches", 1);
    }
    aim.left_was_down = left;
    int pressed = 0;
    if (aim.launch_frames > 0) {
        aim.launch_frames--;
        pressed = 1;
    }
    if (buttons & SDL_BUTTON_RMASK) {
        if (aim.rifle_frame == 0)
            psx_mod_counter_add("omega.mouse-aim.rifle-presses", 1);
        if (aim.rifle_frame < RIFLE_PRESS_FRAMES) pressed = 1;
        aim.rifle_frame = (aim.rifle_frame + 1) %
                          (RIFLE_PRESS_FRAMES + RIFLE_RELEASE_FRAMES);
    } else {
        aim.rifle_frame = 0;
    }
    return pressed;
}

/* One left stick axis, moved from the centre by the mouse's movement. */
static uint32_t stick_axis(float pixels) {
    const long value = STICK_CENTRE + lround(pixels * aim.gain);
    return (uint32_t)(value < 0 ? 0 : value > STICK_MAX ? STICK_MAX : value);
}

/* The controller source: the mouse on the left stick, which the game steers
 * by; the keyboard's left-stick keys on the right stick, which the strafe
 * reads; and ATTACK from the mouse buttons. A source's sticks replace player
 * 1's own, so a gamepad's sticks neither steer nor strafe while the source is
 * attached; the runtime still combines the source's buttons with those
 * pressed on the keyboard and on player 1's device. */
static int mouse_source(PSXModControllerState* state) {
    uint8_t keys[4] = {STICK_CENTRE, STICK_CENTRE, STICK_CENTRE, STICK_CENTRE};
    psx_keybinds_sticks(SDL_GetKeyboardState(NULL), KEYBINDS_PLAYER_1, keys);
    float x = 0.0f, y = 0.0f;
    SDL_MouseButtonFlags buttons = 0;
    if (aim.captured) buttons = SDL_GetRelativeMouseState(&x, &y);
    /* Steer by the average of two frames' movement, so that the movement in a
     * frame whose sample the game skips still counts. Mouse up is stick up;
     * the TYPE setting decides which way that flies. */
    const float steer_x = (x + aim.last_x) / 2, steer_y = (y + aim.last_y) / 2;
    aim.last_x = x;
    aim.last_y = y;
    state->lx = stick_axis(steer_x);
    state->ly = stick_axis(steer_y);
    state->rx = keys[0];
    state->ry = keys[1];
    state->buttons = ALL_BUTTONS_RELEASED;
    if (aim.captured && attack_pressed(buttons))
        state->buttons &= ~attack_button();
    state->analog = 1;
    if (x != 0.0f || y != 0.0f)
        psx_mod_counter_add("omega.mouse-aim.steered-frames", 1);
    return 1;
}

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

/* The instruction hook at FORCE_SUM: while the source drives player 1 and
 * the player is in play, add a force along the screen's right and down axes
 * from the right stick. The game's y axis points up: climbing raises y,
 * turning right lowers the yaw and a positive pitch points the nose down, so
 * for pitch p and yaw y the mech heads along (cos p sin y, -sin p,
 * cos p cos y). The camera follows the heading but not the mech's roll, so
 * screen right is the way the heading turns as the yaw falls,
 * (-cos y, 0, sin y), and screen down the way it turns as the pitch rises,
 * (-sin p sin y, -cos p, -sin p cos y). */
static void strafe_at_force_sum(struct CPUState* cpu, uint32_t address) {
    (void)address;
    const uint32_t player = psx_mod_read_word(PLAYER_POINTER);
    double right, down;
    if (!aim.attached || player == 0 || cpu->gpr[REG_S0] != player ||
            psx_mod_read_word(player + PLAYER_STATE) != PLAYER_IN_PLAY ||
            !right_stick(&right, &down))
        return;
    const double pitch = radians(psx_mod_read_word(player + PLAYER_PITCH));
    const double yaw = radians(psx_mod_read_word(player + PLAYER_YAW));
    const double screen_right[3] = {-cos(yaw), 0.0, sin(yaw)};
    const double screen_down[3] = {-sin(pitch) * sin(yaw), -cos(pitch),
                                   -sin(pitch) * cos(yaw)};
    double force[3];
    for (uint32_t axis = 0; axis < 3; axis++)
        force[axis] = right * screen_right[axis] + down * screen_down[axis];
    if (stage_scrolls()) force[2] = 0.0;
    for (uint32_t axis = 0; axis < 3; axis++) {
        const uint32_t word = player + PLAYER_FORCE + 4u * axis;
        const long added = lround(force[axis] * aim.strafe_force);
        psx_mod_write_word(word, psx_mod_read_word(word) + (uint32_t)added);
    }
    psx_mod_counter_add("omega.mouse-aim.strafed-steps", 1);
}

static void release_mouse(void) {
    if (!aim.captured) return;
    SDL_SetWindowRelativeMouseMode(aim.captured, false);
    aim.captured = NULL;
    aim.last_x = aim.last_y = 0.0f;
    psx_mod_counter_add("omega.mouse-aim.releases", 1);
}

static void capture_mouse(SDL_Window* window) {
    if (aim.captured == window) return;
    release_mouse();
    if (!SDL_SetWindowRelativeMouseMode(window, true)) {
        psx_mod_counter_add("omega.mouse-aim.capture-failures", 1);
        return;
    }
    aim.captured = window;
    SDL_GetRelativeMouseState(NULL, NULL); /* drop the movement from before */
    aim.left_was_down = (SDL_GetMouseState(NULL, NULL) & SDL_BUTTON_LMASK) != 0;
    aim.launch_frames = aim.rifle_frame = 0;
    psx_mod_counter_add("omega.mouse-aim.captures", 1);
}

static void attach_source(void) {
    if (aim.attached) return;
    if (!psx_mod_set_controller_source(PLAYER_1, mouse_source)) {
        psx_mod_counter_add("omega.mouse-aim.attach-failures", 1);
        return;
    }
    aim.attached = 1;
    psx_mod_counter_add("omega.mouse-aim.attaches", 1);
}

static void detach_source(void) {
    if (!aim.attached) return;
    psx_mod_set_controller_source(PLAYER_1, NULL);
    aim.attached = 0;
}

/* Each VBlank once the game has started. The game's TYPE setting (CONTROL
 * SETUPS, help text "FLIP VERTICAL") decides whether stick up flies the mech
 * up (B) or down (A, the game's default); the plugin keeps it at its own
 * value, and each zone copies the setting when it starts. In flight the
 * source drives player 1, and the mouse is captured while the game window has
 * keyboard focus and the game is not paused. The source stays attached while
 * the game is paused: detaching it delivers one neutral frame, which would
 * split a held Start into two presses and unpause the game at once. */
static void mouse_aim_vblank(void) {
    /* Until the game's EXE starts, this RAM belongs to the BIOS. */
    if (!psx_mod_game_started()) return;
    if (psx_mod_read_word(TYPE_SETTING) != aim.type)
        psx_mod_write_word(TYPE_SETTING, aim.type);
    if (!in_flight()) {
        release_mouse();
        detach_source();
        return;
    }
    attach_source();
    SDL_Window* focus = SDL_GetKeyboardFocus();
    if (focus && psx_mod_read_byte(PAUSED) == 0)
        capture_mouse(focus);
    else
        release_mouse();
}

/* The feature's options: the sensitivity, in quarters of a stick unit per
 * pixel; the strafe speed, in percent of the cruising speed; and whether
 * mouse up flies the mech down (TYPE A). */
static void read_options(void) {
    char value[16];
    if (psx_mod_current_option_value("sensitivity", value, sizeof value))
        aim.gain = strtod(value, NULL) / 4.0;
    if (psx_mod_current_option_value("strafe-speed", value, sizeof value))
        aim.strafe_force = CRUISE_FORCE * strtod(value, NULL) / 100.0;
    if (psx_mod_current_option_value("invert-vertical", value, sizeof value) &&
            strcmp(value, "true") == 0)
        aim.type = TYPE_UP_FLIES_DOWN;
}

/* Each session start: read the options and present player 1 as an analog pad,
 * so that in flight the game steers by the stick, not the d-pad. */
static void mouse_aim_activate(void) {
    read_options();
    if (!psx_mod_set_controller_mode_override(PLAYER_1,
                                              PSX_MOD_CONTROLLER_ANALOG))
        psx_mod_counter_add("omega.mouse-aim.mode-failures", 1);
}

PSX_MOD_CONSTRUCTOR(omega_register_mouse_aim) {
    (void)psx_mod_register_activation_plugin("omega.mouse-aim",
                                             mouse_aim_activate);
    (void)psx_mod_register_vblank_plugin("omega.mouse-aim", mouse_aim_vblank);
    (void)psx_mod_register_instruction_plugin("omega.mouse-aim", FORCE_SUM,
                                              FORCE_SUM_WORD,
                                              strafe_at_force_sum);
}

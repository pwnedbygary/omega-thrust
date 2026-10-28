/* Trusted plugin for the package omega.enhancement.widescreen. While its
 * feature is enabled, flight is drawn wider than 4:3: the framework's
 * native-wide renderer widens the picture, so the game shows more of space at
 * the sides instead of stretching its 4:3 picture
 * (psxrecomp/docs/WIDESCREEN.md).
 *
 * When the session starts, before the game window exists, the plugin chooses
 * the view and tells the framework which frames are drawn wide: those of
 * flight, every one of them a 3D scene. Every other frame keeps a 4:3 picture
 * with bars at the sides. game.toml turns on none of the framework's own ways
 * to tell a 3D scene (a gameplay-state gate, sprite tags, a GTE test), so
 * without this mark no frame would be drawn wide. Nor would a gate do: the
 * framework draws a gated frame wide only once enough polygons reach past the
 * screen's edges in two frames running, and the game draws a new picture only
 * every other frame.
 *
 * game.toml's [widescreen.cull] settings, which the framework reads whether
 * this feature is on or not and which change nothing while the view is 4:3,
 * let the game draw the polygons that the wider view reveals, which its
 * renderer would otherwise drop as off the screen's left or right edge. */
#include <string.h>

#include "mod_plugins.h"

#define GAME_STATE 0x8009C5B0u          /* word: the state the main loop runs */
#define STATE_DEMONSTRATION 5u
#define STATE_CAMPAIGN 8u
#define STATE_ZONE_PLAY 9u
#define STATE_TRAINING 11u
#define FLIGHT_DISPLAY_WIDTH 320u       /* the display's width in flight */

/* The views the option offers. "Fit" opens at 16:9 and then follows the
 * window's shape, from 4:3 up to 21:9. */
typedef struct {
    const char* choice;
    uint32_t numerator, denominator;
    int follows_window;
} WidescreenView;

static const WidescreenView VIEWS[] = {
    {"Fit", 16, 9, 1},
    {"16:9", 16, 9, 0},
    {"21:9", 21, 9, 0},
};
#define DEFAULT_VIEW (&VIEWS[0])
/* The widest of VIEWS, up to which "Fit" follows the window. */
#define WIDEST_NUMERATOR 21
#define WIDEST_DENOMINATOR 9

static const WidescreenView* chosen_view(void) {
    char choice[16];
    if (!psx_mod_current_option_value("aspect", choice, sizeof choice))
        return DEFAULT_VIEW;
    for (size_t i = 0; i < sizeof VIEWS / sizeof VIEWS[0]; i++)
        if (strcmp(choice, VIEWS[i].choice) == 0) return &VIEWS[i];
    return DEFAULT_VIEW;
}

/* Whether the frame being drawn is one of flight: in CAMPAIGN PLAY, ZONE
 * PLAY, TRAINING or a DEMONSTRATION replay, with the display 320 pixels wide.
 * The briefings run in CAMPAIGN PLAY's state too, but with a 640-pixel
 * display, so they keep their 4:3 picture, as the menus, the movies and the
 * BIOS do. The framework calls this on the emulation thread whenever it
 * classifies a frame, so it must only read. */
static int flight_frame(void) {
    const uint32_t state = psx_mod_read_word(GAME_STATE);
    return (state == STATE_DEMONSTRATION || state == STATE_CAMPAIGN ||
            state == STATE_ZONE_PLAY || state == STATE_TRAINING) &&
           psx_mod_display_width() == FLIGHT_DISPLAY_WIDTH;
}

/* Each session start: ask for the chosen view, and for Fit also for views
 * that follow the window, and mark flight's frames as 3D scenes. The runtime
 * refuses a view narrower than 4:3, so a refusal here would mean a mistake in
 * VIEWS. */
static void widescreen_activate(void) {
    const WidescreenView* view = chosen_view();
    if (!psx_mod_set_fixed_display_aspect(view->numerator, view->denominator))
        psx_mod_counter_add("omega.widescreen.view-refused", 1);
    if (view->follows_window &&
        !psx_mod_set_adaptive_display_aspect(WIDEST_NUMERATOR,
                                             WIDEST_DENOMINATOR))
        psx_mod_counter_add("omega.widescreen.view-refused", 1);
    psx_mod_set_world_scene_predicate(flight_frame);
}

PSX_MOD_CONSTRUCTOR(omega_register_widescreen) {
    (void)psx_mod_register_activation_plugin("omega.widescreen",
                                             widescreen_activate);
}

// SM2 Core Options blocks in final presentation order; destination keys/artwork path adapted.

    retro_core_option_v2_definition controller_profile{};
    controller_profile.key = "model2emuex_controller_profile_type";
    controller_profile.desc = "Controller Profile Type";
    controller_profile.info = "Select whether controller profiles include Test/Service inputs while retaining gameplay controls and remapping.";
    controller_profile.category_key = "input";
    controller_profile.values[0] = {"normal", "Normal"};
    controller_profile.values[1] = {"test_service", "Normal + Test/Service"};
    controller_profile.default_value = "test_service";
    registered_definitions.push_back(controller_profile);

    retro_core_option_v2_definition gamepad_rumble{};
    gamepad_rumble.key = "model2emuex_gamepad_rumble";
    gamepad_rumble.desc = "Gamepad Rumble";
    gamepad_rumble.info = "Enable gamepad vibration using the game's force-feedback or rumble effects.";
    gamepad_rumble.category_key = "input";
    gamepad_rumble.values[0] = {"enabled", "Enabled"};
    gamepad_rumble.values[1] = {"disabled", "Disabled"};
    gamepad_rumble.default_value = "enabled";
    registered_definitions.push_back(gamepad_rumble);

    retro_core_option_v2_definition crosshair{};
    crosshair.key = "model2emuex_crosshairs";
    crosshair.desc = "Show Crosshair";
    crosshair.info = "Select external crosshair visibility for each player, or use the automatic native-reticle behavior.";
    crosshair.category_key = "input";
    crosshair.values[0] = {"auto", "Automatic"};
    crosshair.values[1] = {"0", "Disabled"};
    crosshair.values[2] = {"1", "Player 1 Only"};
    crosshair.values[3] = {"2", "Player 2 Only"};
    crosshair.values[4] = {"3", "Players 1 & 2"};
    crosshair.default_value = "auto";
    registered_definitions.push_back(crosshair);

    retro_core_option_v2_definition crosshair_style{};
    crosshair_style.key = "model2emuex_crosshair_style";
    crosshair_style.desc = "Crosshair Style";
    crosshair_style.info = "Select the crosshair shape. Auto uses a custom PNG or SM2-Emu; Custom requires a PNG and reports missing artwork. PNGs: system/model2emuex/crosshairs/game-p1.png, game-p2.png or game.png; parent and default names are fallbacks. Maximum 1024 x 1024. Reload content after changing PNGs.";
    crosshair_style.category_key = "input";
    crosshair_style.values[0] = {"auto", "Auto"};
    crosshair_style.values[1] = {"sm2", "SM2-Emu"};
    crosshair_style.values[2] = {"supermodel", "Supermodel"};
    crosshair_style.values[3] = {"custom", "Custom"};
    crosshair_style.default_value = "sm2";
    registered_definitions.push_back(crosshair_style);

    retro_core_option_v2_definition crosshair_timeout{};
    crosshair_timeout.key = "model2emuex_crosshair_timeout";
    crosshair_timeout.desc = "Crosshair Inactivity Timeout";
    crosshair_timeout.info = "Hide each player's external crosshair after the selected time without aiming or firing. Movement or a gun action shows it again. Disabled keeps the selected visibility. Has no effect on native game reticles.";
    crosshair_timeout.category_key = "input";
    crosshair_timeout.values[0] = {"disabled", "Disabled"};
    constexpr std::array<const char*, 12> timeout_values{{"1", "2", "3", "4", "5", "6", "7", "8", "10", "15", "30", "60"}};
    constexpr std::array<const char*, 12> timeout_labels{{"1 Second", "2 Seconds", "3 Seconds", "4 Seconds", "5 Seconds", "6 Seconds", "7 Seconds", "8 Seconds", "10 Seconds", "15 Seconds", "30 Seconds", "60 Seconds"}};
    for (std::size_t i = 0; i < timeout_values.size(); ++i)
        crosshair_timeout.values[i + 1] = {timeout_values[i], timeout_labels[i]};
    crosshair_timeout.default_value = "disabled";
    registered_definitions.push_back(crosshair_timeout);

    retro_core_option_v2_definition gun_input{};
    gun_input.key = "model2emuex_gun_input";
    gun_input.desc = "Gun Input Mode";
    gun_input.info = "Select which input devices control the aiming cursor, including combined and dedicated input modes.";
    gun_input.category_key = "input";
    gun_input.values[0] = {"hybrid", "Standard"};
    gun_input.values[1] = {"lightgun", "Lightgun Only"};
    gun_input.values[2] = {"mouse_analog", "Mouse + Analog Stick"};
    gun_input.values[3] = {"mouse", "Mouse Only"};
    gun_input.values[4] = {"analog", "Analog Stick Only"};
    gun_input.default_value = "hybrid";
    registered_definitions.push_back(gun_input);

    retro_core_option_v2_definition gun_stick{};
    gun_stick.key = "model2emuex_gun_stick_control";
    gun_stick.desc = "Gun Analog Stick Control";
    gun_stick.info = "Select relative cursor movement or absolute-position aiming for the analog stick in gun games. Absolute returns to the centre when the stick is released; Mouse and Lightgun remain available in combined input modes. Changes apply immediately.";
    gun_stick.category_key = "input";
    gun_stick.values[0] = {"relative", "Relative"};
    gun_stick.values[1] = {"absolute", "Absolute"};
    gun_stick.default_value = "relative";
    registered_definitions.push_back(gun_stick);

    retro_core_option_v2_definition offscreen_reload{};
    offscreen_reload.key = "model2emuex_offscreen_reload_shortcut";
    offscreen_reload.desc = "Off-Screen Reload Shortcut";
    offscreen_reload.info = "Enable dedicated inputs that force an off-screen reload while retaining native lightgun off-screen firing.";
    offscreen_reload.category_key = "input";
    offscreen_reload.values[0] = {"enabled", "Enabled"};
    offscreen_reload.values[1] = {"disabled", "Disabled"};
    offscreen_reload.default_value = "enabled";
    registered_definitions.push_back(offscreen_reload);

    retro_core_option_v2_definition mouse_edge_reload{};
    mouse_edge_reload.key = "model2emuex_mouse_edge_offscreen_reload";
    mouse_edge_reload.desc = "Mouse Edge Off-Screen Reload";
    mouse_edge_reload.info = "Allow a mouse shot at the screen edge to trigger off-screen reload.";
    mouse_edge_reload.category_key = "input";
    mouse_edge_reload.values[0] = {"disabled", "Disabled"};
    mouse_edge_reload.values[1] = {"enabled", "Enabled"};
    mouse_edge_reload.default_value = "disabled";
    registered_definitions.push_back(mouse_edge_reload);

    retro_core_option_v2_definition shifter{};
    shifter.key = "model2emuex_four_speed_shifter";
    shifter.desc = "4-Speed Shifter";
    shifter.info = "Select direct directional gear selection or diagonal analog-stick H-gate shifting. Applies only to 4-speed driving games.";
    shifter.category_key = "input";
    shifter.values[0] = {"h_gate", "H-Gate Mode"};
    shifter.values[1] = {"standard", "Standard"};
    shifter.default_value = "h_gate";
    registered_definitions.push_back(shifter);

    retro_core_option_v2_definition neutral_time{};
    neutral_time.key = "model2emuex_gear_shift_neutral_time";
    neutral_time.desc = "Gear Shift Neutral Time";
    neutral_time.info = "Set the time spent in neutral between gears when using Shift Up/Down in 4-speed driving games. Direct gear selection bypasses the delay. 0 disables it. Applies to subsequent shifts on return to gameplay without a machine reset; 0 also cancels a pending delay.";
    neutral_time.category_key = "input";
    for (unsigned step = 0; step <= 50; ++step) {
        option_value_label_storage.push_back(std::to_string(step * 10));
        const char* value = option_value_label_storage.back().c_str();
        option_value_label_storage.push_back(std::to_string(step * 10) + " ms");
        neutral_time.values[step] = {value, option_value_label_storage.back().c_str()};
    }
    neutral_time.default_value = "100";
    registered_definitions.push_back(neutral_time);

    retro_core_option_v2_definition automatic_start_gear{};
    automatic_start_gear.key = "model2emuex_automatic_start_gear";
    automatic_start_gear.desc = "Automatic Start Gear (Restart Required)";
    automatic_start_gear.info = "Use the declared initial gear for rolling starts instead of always starting in first gear. Applies only to 4-speed driving games.";
    automatic_start_gear.category_key = "input";
    automatic_start_gear.values[0] = {"enabled", "Enabled"};
    automatic_start_gear.values[1] = {"disabled", "Disabled"};
    automatic_start_gear.default_value = "enabled";
    registered_definitions.push_back(automatic_start_gear);

    retro_core_option_v2_definition steering_response{};
    steering_response.key = "model2emuex_steering_response";
    steering_response.desc = "Driving Steering Response";
    steering_response.info = "Select the steering response curve to adjust sensitivity around the center while retaining full travel.";
    steering_response.category_key = "input";
    steering_response.values[0] = {"linear", "Linear"};
    steering_response.values[1] = {"progressive", "Progressive (Fine Center)"};
    steering_response.values[2] = {"fbneo", "FBNeo Logarithmic (Fine Center)"};
    steering_response.default_value = "linear";
    registered_definitions.push_back(steering_response);



    const auto add_output_range = [](const char* key, const char* label, const char* info,
                                     bool steering) {
        retro_core_option_v2_definition definition{};
        definition.key = key;
        definition.desc = label;
        definition.info = info;
        definition.category_key = "input";
        static constexpr std::pair<const char*, const char*> steering_values[] = {
            {"50", "50%"}, {"60", "60%"}, {"63", "63% (30-80-D0)"},
            {"70", "70%"}, {"80", "80%"}, {"90", "90%"},
            {"100", "100%"}, {"110", "110%"}, {"120", "120%"},
            {"130", "130%"}, {"140", "140%"}, {"150", "150%"},
        };
        static constexpr std::pair<const char*, const char*> pedal_values[] = {
            {"50", "50%"}, {"60", "60%"}, {"70", "70%"},
            {"75.3", "75.3% (00-C0)"}, {"80", "80%"}, {"90", "90%"},
            {"100", "100%"}, {"110", "110%"}, {"120", "120%"},
            {"130", "130%"}, {"140", "140%"}, {"150", "150%"},
        };
        const auto* values = steering ? steering_values : pedal_values;
        const size_t value_count = steering ? std::size(steering_values)
                                            : std::size(pedal_values);
        for (size_t i = 0; i < value_count; ++i) {
            definition.values[i] = {values[i].first, values[i].second};
        }
        definition.default_value = "100";
        return definition;
    };
    registered_definitions.push_back(add_output_range(
        "model2emuex_steering_output_range", "Driving Steering Output Range",
        "Scale steering output around its center to adjust the input travel needed for full lock.", true));
    registered_definitions.push_back(add_output_range(
        "model2emuex_accelerator_output_range", "Driving Accelerator Output Range",
        "Scale accelerator output from its released position to adjust the input travel needed for full acceleration.", false));
    registered_definitions.push_back(add_output_range(
        "model2emuex_brake_output_range", "Driving Brake Output Range",
        "Scale brake output from its released position to adjust the input travel needed for full braking.", false));

    retro_core_option_v2_definition desert_elevation_control{};
    desert_elevation_control.key = "model2emuex_desert_elevation_control";
    desert_elevation_control.desc = "Desert Tank: Elevation Control";
    desert_elevation_control.info = "Select relative movement or absolute-position control for turret elevation.";
    desert_elevation_control.category_key = "input";
    desert_elevation_control.values[0] = {"relative", "Relative"};
    desert_elevation_control.values[1] = {"absolute", "Absolute"};
    desert_elevation_control.default_value = "relative";
    registered_definitions.push_back(desert_elevation_control);

    retro_core_option_v2_definition desert_elevation_speed{};
    desert_elevation_speed.key = "model2emuex_desert_elevation_speed";
    desert_elevation_speed.desc = "Desert Tank: Elevation Speed (Relative Only)";
    desert_elevation_speed.info = "Adjust the maximum turret elevation speed in relative control mode.";
    desert_elevation_speed.category_key = "input";
    desert_elevation_speed.values[0] = {"10", "10%"};
    desert_elevation_speed.values[1] = {"20", "20%"};
    desert_elevation_speed.values[2] = {"30", "30%"};
    desert_elevation_speed.values[3] = {"40", "40%"};
    desert_elevation_speed.values[4] = {"50", "50%"};
    desert_elevation_speed.values[5] = {"60", "60%"};
    desert_elevation_speed.values[6] = {"70", "70%"};
    desert_elevation_speed.values[7] = {"80", "80%"};
    desert_elevation_speed.values[8] = {"90", "90%"};
    desert_elevation_speed.values[9] = {"100", "100%"};
    desert_elevation_speed.values[10] = {"110", "110%"};
    desert_elevation_speed.values[11] = {"120", "120%"};
    desert_elevation_speed.values[12] = {"130", "130%"};
    desert_elevation_speed.values[13] = {"140", "140%"};
    desert_elevation_speed.values[14] = {"150", "150%"};
    desert_elevation_speed.values[15] = {"160", "160%"};
    desert_elevation_speed.values[16] = {"170", "170%"};
    desert_elevation_speed.values[17] = {"180", "180%"};
    desert_elevation_speed.values[18] = {"190", "190%"};
    desert_elevation_speed.values[19] = {"200", "200%"};
    desert_elevation_speed.default_value = "100";
    registered_definitions.push_back(desert_elevation_speed);

    retro_core_option_v2_definition desert_elevation_axis{};
    desert_elevation_axis.key = "model2emuex_desert_elevation_axis";
    desert_elevation_axis.desc = "Desert Tank: Elevation Axis Mode";
    desert_elevation_axis.info = "Select normal or inverted vertical input for turret elevation.";
    desert_elevation_axis.category_key = "input";
    desert_elevation_axis.values[0] = {"normal", "Normal"};
    desert_elevation_axis.values[1] = {"inverted", "Inverted"};
    desert_elevation_axis.default_value = "normal";
    registered_definitions.push_back(desert_elevation_axis);

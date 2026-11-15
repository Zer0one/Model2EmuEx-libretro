#pragma once
#include <filesystem>
extern "C" {
#include "lua51/lua.h"
#include "lua51/lauxlib.h"
#include "lua51/lualib.h"
}
void lua_video_bind(lua_State *, const std::filesystem::path &, void (*notify)(const char *));
void lua_video_close();

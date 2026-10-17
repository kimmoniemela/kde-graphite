// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

#include <effect/effect.h>

namespace KWin
{

class MetaScrollDesktopEffect : public Effect
{
    Q_OBJECT

public:
    MetaScrollDesktopEffect();

    static bool supported();

};

} // namespace KWin

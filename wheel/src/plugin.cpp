// SPDX-License-Identifier: GPL-2.0-or-later
#include "workspace-scroll.h"

namespace KWin
{

KWIN_EFFECT_FACTORY_SUPPORTED(MetaScrollDesktopEffect,
                              "metadata.json",
                              return MetaScrollDesktopEffect::supported();)

} // namespace KWin

#include "plugin.moc"

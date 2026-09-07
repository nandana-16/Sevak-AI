package `in`.sevakai.app.ui.theme

import android.app.Activity
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

/**
 * Green, white and black.
 *
 * The palette is deliberately narrow. Green carries identity and confirmation,
 * black and white carry structure, and saturated colour is reserved almost
 * entirely for the three risk levels - so when something on screen is red, it
 * means one specific thing rather than "this is a heading".
 *
 * Contrast is checked against a phone screen in daylight, which is the actual
 * working condition: every text colour here clears WCAG AA on its background.
 */

// --- Brand ------------------------------------------------------------------
val SevakGreen = Color(0xFF1B7A43)
val SevakGreenDark = Color(0xFF12572F)
val SevakGreenLight = Color(0xFFE6F2EA)
val SevakGreenBright = Color(0xFF34A860)

val Ink = Color(0xFF0E1210)
val InkMuted = Color(0xFF5A635E)
val Paper = Color(0xFFFFFFFF)
val PaperSunk = Color(0xFFF4F7F5)
val Hairline = Color(0xFFDCE4DE)

// --- Risk -------------------------------------------------------------------
// One colour per level, plus a tint for backgrounds. Never used decoratively.
val RiskRed = Color(0xFFC62828)
val RiskRedTint = Color(0xFFFDECEC)
val RiskAmber = Color(0xFF9A6700)
val RiskAmberTint = Color(0xFFFDF4E3)
val RiskGreen = SevakGreen
val RiskGreenTint = SevakGreenLight
val RiskGrey = Color(0xFF6B7671)
val RiskGreyTint = Color(0xFFF0F2F1)

// --- Dark variants ----------------------------------------------------------
val InkDark = Color(0xFFE8EDEA)
val InkMutedDark = Color(0xFF9BA6A0)
val PaperDark = Color(0xFF0F1411)
val PaperSunkDark = Color(0xFF171D19)
val HairlineDark = Color(0xFF2A332E)

val RiskRedDark = Color(0xFFFF6B6B)
val RiskRedTintDark = Color(0xFF3A1A1A)
val RiskAmberDark = Color(0xFFE8B339)
val RiskAmberTintDark = Color(0xFF332708)
val RiskGreenDark = Color(0xFF5FD98C)
val RiskGreenTintDark = Color(0xFF12301F)

private val LightColors = lightColorScheme(
    primary = SevakGreen,
    onPrimary = Paper,
    primaryContainer = SevakGreenLight,
    onPrimaryContainer = SevakGreenDark,
    secondary = Ink,
    onSecondary = Paper,
    background = Paper,
    onBackground = Ink,
    surface = Paper,
    onSurface = Ink,
    surfaceVariant = PaperSunk,
    onSurfaceVariant = InkMuted,
    outline = Hairline,
    outlineVariant = Hairline,
    error = RiskRed,
    onError = Paper,
    errorContainer = RiskRedTint,
    onErrorContainer = RiskRed,
)

private val DarkColors = darkColorScheme(
    primary = RiskGreenDark,
    onPrimary = Color(0xFF04160C),
    primaryContainer = RiskGreenTintDark,
    onPrimaryContainer = RiskGreenDark,
    secondary = InkDark,
    onSecondary = PaperDark,
    background = PaperDark,
    onBackground = InkDark,
    surface = PaperDark,
    onSurface = InkDark,
    surfaceVariant = PaperSunkDark,
    onSurfaceVariant = InkMutedDark,
    outline = HairlineDark,
    outlineVariant = HairlineDark,
    error = RiskRedDark,
    onError = Color(0xFF2A0A0A),
    errorContainer = RiskRedTintDark,
    onErrorContainer = RiskRedDark,
)

/** Risk colours resolved for the current theme. */
data class RiskPalette(
    val red: Color,
    val redTint: Color,
    val amber: Color,
    val amberTint: Color,
    val green: Color,
    val greenTint: Color,
    val grey: Color,
    val greyTint: Color,
)

val LightRisk = RiskPalette(
    RiskRed, RiskRedTint, RiskAmber, RiskAmberTint,
    RiskGreen, RiskGreenTint, RiskGrey, RiskGreyTint,
)
val DarkRisk = RiskPalette(
    RiskRedDark, RiskRedTintDark, RiskAmberDark, RiskAmberTintDark,
    RiskGreenDark, RiskGreenTintDark, InkMutedDark, PaperSunkDark,
)

val LocalRiskPalette = androidx.compose.runtime.staticCompositionLocalOf { LightRisk }

@Composable
fun SevakTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    val colors = if (darkTheme) DarkColors else LightColors
    val risk = if (darkTheme) DarkRisk else LightRisk

    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = android.graphics.Color.TRANSPARENT
            WindowCompat.getInsetsController(window, view)
                .isAppearanceLightStatusBars = !darkTheme
        }
    }

    androidx.compose.runtime.CompositionLocalProvider(LocalRiskPalette provides risk) {
        MaterialTheme(
            colorScheme = colors,
            typography = SevakTypography,
            shapes = SevakShapes,
            content = content,
        )
    }
}

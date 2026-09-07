package `in`.sevakai.app.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Shapes
import androidx.compose.ui.text.ExperimentalTextApi
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontVariation
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import `in`.sevakai.app.R

/**
 * One typeface everywhere.
 *
 * Noto Sans is bundled as a variable font, so every weight comes from a single
 * 2 MB file instead of four static ones. Devanagari falls through to the
 * system's Noto Sans Devanagari, which is metrically the same design - so a
 * Hindi summary and an English label sit together without looking pasted in
 * from different apps.
 *
 * Sizes start a step larger than Material's defaults. The reader is outdoors,
 * often over 40, and holding a cheap phone at arm's length.
 */

@OptIn(ExperimentalTextApi::class)
private fun notoSans(weight: Int) = Font(
    R.font.noto_sans,
    FontWeight(weight),
    variationSettings = FontVariation.Settings(FontVariation.weight(weight)),
)

val SevakFontFamily = FontFamily(
    notoSans(400),
    notoSans(500),
    notoSans(600),
    notoSans(700),
)

private fun style(
    size: Int,
    lineHeight: Int,
    weight: FontWeight = FontWeight.Normal,
    tracking: Double = 0.0,
) = TextStyle(
    fontFamily = SevakFontFamily,
    fontWeight = weight,
    fontSize = size.sp,
    lineHeight = lineHeight.sp,
    letterSpacing = tracking.sp,
)

val SevakTypography = Typography(
    displaySmall = style(32, 40, FontWeight.SemiBold, (-0.5)),
    headlineLarge = style(28, 36, FontWeight.SemiBold, (-0.4)),
    headlineMedium = style(24, 32, FontWeight.SemiBold, (-0.3)),
    headlineSmall = style(20, 28, FontWeight.SemiBold, (-0.2)),
    titleLarge = style(19, 26, FontWeight.SemiBold),
    titleMedium = style(17, 24, FontWeight.Medium),
    titleSmall = style(15, 20, FontWeight.Medium),
    bodyLarge = style(17, 26),
    bodyMedium = style(15, 23),
    bodySmall = style(13, 19),
    labelLarge = style(16, 20, FontWeight.SemiBold),
    labelMedium = style(13, 17, FontWeight.Medium, 0.2),
    // Used for the small uppercase section markers.
    labelSmall = style(12, 16, FontWeight.SemiBold, 0.8),
)

val SevakShapes = Shapes(
    extraSmall = RoundedCornerShape(6.dp),
    small = RoundedCornerShape(10.dp),
    medium = RoundedCornerShape(14.dp),
    large = RoundedCornerShape(20.dp),
    extraLarge = RoundedCornerShape(28.dp),
)

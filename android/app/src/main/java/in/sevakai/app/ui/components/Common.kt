package `in`.sevakai.app.ui.components

import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CloudOff
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.WarningAmber
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import `in`.sevakai.app.ui.i18n.LocalStrings
import `in`.sevakai.app.ui.theme.LocalRiskPalette

/** Canonical risk levels. Parsing lives here so no screen invents its own. */
enum class Risk { RED, AMBER, GREEN, UNKNOWN;

    companion object {
        fun from(value: String?): Risk = when (value?.lowercase()) {
            "red" -> RED
            "yellow", "amber" -> AMBER
            "green" -> GREEN
            else -> UNKNOWN
        }
    }
}

@Composable
fun Risk.color(): Color = with(LocalRiskPalette.current) {
    when (this@color) {
        Risk.RED -> red
        Risk.AMBER -> amber
        Risk.GREEN -> green
        Risk.UNKNOWN -> grey
    }
}

@Composable
fun Risk.tint(): Color = with(LocalRiskPalette.current) {
    when (this@tint) {
        Risk.RED -> redTint
        Risk.AMBER -> amberTint
        Risk.GREEN -> greenTint
        Risk.UNKNOWN -> greyTint
    }
}

/** Wording a worker acts on, not a colour name. */
@Composable
fun Risk.label(): String = with(LocalStrings.current) {
    when (this@label) {
        Risk.RED -> riskRedAction
        Risk.AMBER -> riskAmberAction
        Risk.GREEN -> riskGreenAction
        Risk.UNKNOWN -> riskUnknownAction
    }
}

@Composable
fun Risk.shortLabel(): String = with(LocalStrings.current) {
    when (this@shortLabel) {
        Risk.RED -> riskRedShort
        Risk.AMBER -> riskAmberShort
        Risk.GREEN -> riskGreenShort
        Risk.UNKNOWN -> riskUnknownShort
    }
}

/**
 * The risk chip.
 *
 * Colour alone is never the signal - every chip carries a word too, because
 * red/green is exactly the pair that around one man in twelve cannot separate,
 * and this is the most consequential piece of information on the screen.
 */
@Composable
fun RiskChip(
    risk: Risk,
    modifier: Modifier = Modifier,
    expanded: Boolean = false,
) {
    val color by animateColorAsState(risk.color(), label = "riskColor")
    Row(
        modifier = modifier
            .clip(CircleShape)
            .background(risk.tint())
            .padding(horizontal = 10.dp, vertical = 5.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Box(
            Modifier
                .size(9.dp)
                .clip(CircleShape)
                .background(color)
        )
        Text(
            text = if (expanded) risk.label() else risk.shortLabel(),
            style = MaterialTheme.typography.labelMedium,
            color = color,
            fontWeight = FontWeight.SemiBold,
        )
    }
}

/** A flat, bordered card. No elevation anywhere in the app - shadows read as
 *  mud on the cheap LCDs these phones have. */
@Composable
fun SectionCard(
    modifier: Modifier = Modifier,
    accent: Color? = null,
    onClick: (() -> Unit)? = null,
    content: @Composable androidx.compose.foundation.layout.ColumnScope.() -> Unit,
) {
    Surface(
        modifier = modifier.fillMaxWidth(),
        shape = MaterialTheme.shapes.medium,
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, accent ?: MaterialTheme.colorScheme.outline),
    ) {
        Column(
            Modifier
                .then(if (onClick != null) Modifier.clickable(onClick = onClick) else Modifier)
                .padding(16.dp),
            content = content,
        )
    }
}

/** Small uppercase marker that starts each block of a profile. */
@Composable
fun SectionLabel(text: String, modifier: Modifier = Modifier) {
    Text(
        text = text.uppercase(),
        style = MaterialTheme.typography.labelSmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        modifier = modifier,
    )
}

@Composable
fun LabelledValue(
    label: String,
    value: String?,
    modifier: Modifier = Modifier,
) {
    Column(modifier) {
        Text(
            label,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Spacer(Modifier.height(2.dp))
        Text(
            value?.takeIf { it.isNotBlank() } ?: LocalStrings.current.notRecorded,
            style = MaterialTheme.typography.bodyLarge,
            fontWeight = FontWeight.Medium,
        )
    }
}

enum class NoticeTone { INFO, WARNING, OFFLINE }

/**
 * Inline notice strip. Used for "showing saved copy", "sent to the queue" and
 * the degraded-pipeline warning - all cases where the app must be candid about
 * what it did rather than quietly looking normal.
 */
@Composable
fun Notice(
    text: String,
    tone: NoticeTone = NoticeTone.INFO,
    modifier: Modifier = Modifier,
    icon: ImageVector? = null,
) {
    val palette = LocalRiskPalette.current
    val (fg, bg) = when (tone) {
        NoticeTone.INFO -> MaterialTheme.colorScheme.primary to MaterialTheme.colorScheme.primaryContainer
        NoticeTone.WARNING -> palette.amber to palette.amberTint
        NoticeTone.OFFLINE -> palette.grey to palette.greyTint
    }
    Row(
        modifier
            .fillMaxWidth()
            .clip(MaterialTheme.shapes.small)
            .background(bg)
            .padding(horizontal = 12.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Icon(
            icon ?: when (tone) {
                NoticeTone.INFO -> Icons.Default.Info
                NoticeTone.WARNING -> Icons.Default.WarningAmber
                NoticeTone.OFFLINE -> Icons.Default.CloudOff
            },
            contentDescription = null,
            tint = fg,
            modifier = Modifier.size(18.dp),
        )
        Text(text, style = MaterialTheme.typography.bodySmall, color = fg)
    }
}

@Composable
fun LoadingBlock(message: String? = null, modifier: Modifier = Modifier) {
    Column(
        modifier
            .fillMaxWidth()
            .padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        CircularProgressIndicator(
            strokeWidth = 3.dp,
            modifier = Modifier.size(30.dp),
            color = MaterialTheme.colorScheme.primary,
        )
        Text(
            message ?: LocalStrings.current.loading,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center,
        )
    }
}

@Composable
fun EmptyState(
    title: String,
    body: String,
    modifier: Modifier = Modifier,
    icon: ImageVector? = null,
) {
    Column(
        modifier
            .fillMaxWidth()
            .padding(horizontal = 32.dp, vertical = 48.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        if (icon != null) {
            Icon(
                icon,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.size(34.dp),
            )
            Spacer(Modifier.height(4.dp))
        }
        Text(
            title,
            style = MaterialTheme.typography.titleMedium,
            textAlign = TextAlign.Center,
        )
        Text(
            body,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center,
        )
    }
}

/** Filter pill used on the roster. */
@Composable
fun FilterPill(
    text: String,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    accent: Color? = null,
) {
    val fg = when {
        selected -> MaterialTheme.colorScheme.onPrimary
        accent != null -> accent
        else -> MaterialTheme.colorScheme.onSurfaceVariant
    }
    val bg = when {
        selected -> accent ?: MaterialTheme.colorScheme.primary
        else -> Color.Transparent
    }
    Box(
        modifier
            .clip(CircleShape)
            .background(bg)
            .border(
                1.dp,
                if (selected) Color.Transparent else MaterialTheme.colorScheme.outline,
                CircleShape,
            )
            .clickable(onClick = onClick)
            .heightIn(min = 36.dp)
            .padding(horizontal = 14.dp, vertical = 8.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(text, style = MaterialTheme.typography.labelMedium, color = fg)
    }
}

@Composable
fun Divider(modifier: Modifier = Modifier) {
    Box(
        modifier
            .fillMaxWidth()
            .height(1.dp)
            .background(MaterialTheme.colorScheme.outline)
    )
}

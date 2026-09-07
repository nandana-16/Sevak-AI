package `in`.sevakai.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import `in`.sevakai.app.sync.SyncWorker
import `in`.sevakai.app.ui.SevakNavHost
import `in`.sevakai.app.ui.theme.SevakTheme
import kotlinx.coroutines.flow.map

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)

        val repository = SevakApp.repository(applicationContext)

        setContent {
            SevakTheme {
                val signedIn by repository.session.session
                    .map { it != null }
                    .collectAsState(initial = null)

                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background,
                ) {
                    // `null` means we have not read the store yet; rendering
                    // the login screen during that gap makes an already
                    // signed-in worker flash a sign-in form on every launch.
                    signedIn?.let { SevakNavHost(repository = repository, signedIn = it) }
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        // Coming back to the app is the most likely moment for the worker to
        // have walked back into signal.
        SyncWorker.syncNow(applicationContext)
    }
}

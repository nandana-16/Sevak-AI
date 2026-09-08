package `in`.sevakai.app.ui

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import androidx.navigation.NavType
import `in`.sevakai.app.data.Repository
import `in`.sevakai.app.ui.login.LoginScreen
import `in`.sevakai.app.ui.patient.PatientScreen
import `in`.sevakai.app.ui.plan.PlanScreen
import `in`.sevakai.app.ui.queue.QueueScreen
import `in`.sevakai.app.ui.register.RegisterScreen
import `in`.sevakai.app.ui.roster.RosterScreen
import `in`.sevakai.app.ui.settings.ServerSettingsScreen
import `in`.sevakai.app.ui.visit.VisitResultScreen
import `in`.sevakai.app.ui.visit.VisitScreen

object Routes {
    const val LOGIN = "login"
    const val ROSTER = "roster"
    const val PLAN = "plan"
    const val QUEUE = "queue"
    const val REGISTER = "register"
    const val SERVER = "server"
    const val PATIENT = "patient/{patientId}"
    const val VISIT = "visit/{patientId}"
    const val VISIT_RESULT = "visitResult/{visitId}"

    fun patient(id: String) = "patient/$id"
    fun visit(id: String) = "visit/$id"
    fun visitResult(id: String) = "visitResult/$id"
}

@Composable
fun SevakNavHost(
    repository: Repository,
    signedIn: Boolean,
    navController: NavHostController = rememberNavController(),
) {
    // A rejected token can arrive at any point, so the whole graph reacts to
    // sign-in state rather than each screen handling it.
    LaunchedEffect(signedIn) {
        val target = if (signedIn) Routes.ROSTER else Routes.LOGIN
        if (navController.currentDestination?.route != target) {
            navController.navigate(target) {
                popUpTo(0) { inclusive = true }
                launchSingleTop = true
            }
        }
    }

    NavHost(
        navController = navController,
        startDestination = if (signedIn) Routes.ROSTER else Routes.LOGIN,
    ) {
        composable(Routes.LOGIN) {
            LoginScreen(
                repository = repository,
                onOpenServerSettings = { navController.navigate(Routes.SERVER) },
            )
        }

        composable(Routes.SERVER) {
            ServerSettingsScreen(
                repository = repository,
                onBack = { navController.popBackStack() },
            )
        }

        composable(Routes.ROSTER) {
            RosterScreen(
                repository = repository,
                onOpenPatient = { navController.navigate(Routes.patient(it)) },
                onOpenPlan = { navController.navigate(Routes.PLAN) },
                onOpenQueue = { navController.navigate(Routes.QUEUE) },
                onRegister = { navController.navigate(Routes.REGISTER) },
                onOpenServerSettings = { navController.navigate(Routes.SERVER) },
            )
        }

        composable(Routes.PLAN) {
            PlanScreen(
                repository = repository,
                onBack = { navController.popBackStack() },
                onOpenPatient = { navController.navigate(Routes.patient(it)) },
            )
        }

        composable(Routes.QUEUE) {
            QueueScreen(
                repository = repository,
                onBack = { navController.popBackStack() },
            )
        }

        composable(Routes.REGISTER) {
            RegisterScreen(
                repository = repository,
                onBack = { navController.popBackStack() },
                onRegistered = { id ->
                    navController.navigate(Routes.patient(id)) {
                        popUpTo(Routes.ROSTER)
                    }
                },
            )
        }

        composable(
            Routes.PATIENT,
            arguments = listOf(navArgument("patientId") { type = NavType.StringType }),
        ) { entry ->
            PatientScreen(
                repository = repository,
                patientId = entry.arguments?.getString("patientId").orEmpty(),
                onBack = { navController.popBackStack() },
                onRecordVisit = { navController.navigate(Routes.visit(it)) },
                onOpenVisit = { navController.navigate(Routes.visitResult(it)) },
            )
        }

        composable(
            Routes.VISIT,
            arguments = listOf(navArgument("patientId") { type = NavType.StringType }),
        ) { entry ->
            VisitScreen(
                repository = repository,
                patientId = entry.arguments?.getString("patientId").orEmpty(),
                onBack = { navController.popBackStack() },
                onDone = { navController.popBackStack() },
            )
        }

        composable(
            Routes.VISIT_RESULT,
            arguments = listOf(navArgument("visitId") { type = NavType.StringType }),
        ) { entry ->
            VisitResultScreen(
                repository = repository,
                visitId = entry.arguments?.getString("visitId").orEmpty(),
                onBack = { navController.popBackStack() },
            )
        }
    }
}

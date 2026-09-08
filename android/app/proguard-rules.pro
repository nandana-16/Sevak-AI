# R8 rules for release builds.
#
# Without these the app compiles and installs, then fails at runtime in ways
# that look like server bugs - serializers stripped, Retrofit interfaces
# losing their generic signatures. Worth having even though the demo ships the
# debug build.

# Note: the package is written plainly as in.sevakai.app here. The Kotlin
# backtick escaping for the `in` keyword is source syntax and is not
# understood by R8's rule parser.

# --- kotlinx.serialization -------------------------------------------------
# Serializers are generated as static fields and companions that nothing
# references directly, so R8 cannot see they are used.
-keepattributes *Annotation*, InnerClasses, Signature, Exceptions
-dontnote kotlinx.serialization.**

-keepclassmembers class kotlinx.serialization.json.** {
    *** Companion;
}
-keepclasseswithmembers class kotlinx.serialization.json.** {
    kotlinx.serialization.KSerializer serializer(...);
}

-keep,includedescriptorclasses class in.sevakai.app.**$$serializer { *; }
-keepclassmembers class in.sevakai.app.** {
    *** Companion;
}
-keepclasseswithmembers class in.sevakai.app.** {
    kotlinx.serialization.KSerializer serializer(...);
}
# The DTOs themselves, since their field names are the wire format.
-keep class in.sevakai.app.data.remote.** { *; }

# --- Retrofit / OkHttp -----------------------------------------------------
-keepattributes RuntimeVisibleAnnotations, RuntimeVisibleParameterAnnotations
-keep,allowobfuscation interface retrofit2.Call
-keep,allowobfuscation class retrofit2.Response
-keepclassmembers,allowshrinking,allowobfuscation interface * {
    @retrofit2.http.* <methods>;
}
-dontwarn okhttp3.internal.platform.**
-dontwarn org.conscrypt.**
-dontwarn org.bouncycastle.**
-dontwarn org.openjsse.**
# Kotlin suspend functions in Retrofit interfaces need Continuation intact.
-keep class kotlin.coroutines.Continuation

# --- Room ------------------------------------------------------------------
-keep class * extends androidx.room.RoomDatabase { <init>(); }
-dontwarn androidx.room.paging.**

# --- WorkManager -----------------------------------------------------------
# Workers are constructed reflectively by class name.
-keep class * extends androidx.work.ListenableWorker { <init>(...); }

# --- Keep line numbers so a crash report is readable -----------------------
-keepattributes SourceFile, LineNumberTable
-renamesourcefileattribute SourceFile

package `in`.sevakai.app.data.remote

import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query

interface ApiService {

    @GET("api/health")
    suspend fun health(): HealthDto

    @POST("api/auth/login")
    suspend fun login(@Body body: LoginRequest): LoginResponse

    @GET("api/auth/me")
    suspend fun me(): WorkerDto

    @GET("api/patients")
    suspend fun patients(
        @Query("search") search: String? = null,
        @Query("village") village: String? = null,
        @Query("category") category: String? = null,
        @Query("risk") risk: String? = null,
        @Query("due_only") dueOnly: Boolean? = null,
    ): List<PatientSummaryDto>

    @GET("api/patients/villages")
    suspend fun villages(): List<String>

    @GET("api/patients/{id}")
    suspend fun patient(@Path("id") id: String): PatientDetailDto

    @POST("api/patients")
    suspend fun createPatient(@Body body: PatientCreateRequest): PatientDetailDto

    @POST("api/patients/aadhaar/check")
    suspend fun checkAadhaar(@Body body: AadhaarCheckRequest): AadhaarCheckResponse

    @POST("api/patients/{patientId}/vaccinations/{vaccinationId}/given")
    suspend fun markVaccinationGiven(
        @Path("patientId") patientId: String,
        @Path("vaccinationId") vaccinationId: String,
    ): VaccinationDto

    @POST("api/visits")
    suspend fun submitVisit(@Body body: VisitCreateRequest): VisitDetailDto

    @Multipart
    @POST("api/visits/audio")
    suspend fun submitVisitAudio(
        @Part("client_uuid") clientUuid: RequestBody,
        @Part("patient_id") patientId: RequestBody,
        @Part("language") language: RequestBody,
        @Part("typed_notes") typedNotes: RequestBody?,
        @Part("manual_fields") manualFields: RequestBody?,
        @Part audio: MultipartBody.Part,
    ): VisitDetailDto

    @GET("api/visits/{id}")
    suspend fun visit(@Path("id") id: String): VisitDetailDto

    @GET("api/visits")
    suspend fun visits(@Query("patient_id") patientId: String): List<VisitDetailDto>

    @GET("api/schedule/today")
    suspend fun scheduleToday(): List<ScheduledVisitDto>

    @GET("api/schedule")
    suspend fun schedule(@Query("days") days: Int = 14): List<ScheduledVisitDto>

    @POST("api/schedule/{id}/snooze")
    suspend fun snooze(
        @Path("id") id: String,
        @Query("days") days: Int = 1,
    ): ScheduledVisitDto

    @GET("api/escalations")
    suspend fun escalations(): List<EscalationDto>
}

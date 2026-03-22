package com.example.amazonwishlist.data

import com.squareup.moshi.Json
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import retrofit2.http.*

data class Wishlist(
    @Json(name = "id") val id: Int,
    @Json(name = "name") val name: String,
    @Json(name = "url") val url: String
)

// Replace with your actual server IP address
private const val BASE_URL = "http://192.168.31.131:8010/"

interface WishlistApiService {
    @GET("items")
    suspend fun getItems(): List<WishlistItem>

    @GET("items/{id}/history")
    suspend fun getItemHistory(@Path("id") itemId: String): List<PriceHistory>

    @GET("notifications")
    suspend fun getNotifications(): List<Notification>

    @POST("notifications/{id}/read")
    suspend fun markNotificationRead(@Path("id") notificationId: Int): Map<String, String>

    @GET("wishlists")
    suspend fun getWishlists(): List<Wishlist>

    @POST("wishlists")
    suspend fun addWishlist(@Body data: Map<String, String>): Wishlist

    @DELETE("wishlists/{id}")
    suspend fun deleteWishlist(@Path("id") id: Int): Map<String, String>
}

private val moshi = Moshi.Builder()
    .add(KotlinJsonAdapterFactory())
    .build()

object WishlistApi {
    val retrofitService: WishlistApiService by lazy {
        Retrofit.Builder()
            .addConverterFactory(MoshiConverterFactory.create(moshi))
            .baseUrl(BASE_URL)
            .build()
            .create(WishlistApiService::class.java)
    }
}

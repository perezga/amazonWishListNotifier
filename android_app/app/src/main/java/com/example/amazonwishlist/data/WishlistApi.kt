package com.example.amazonwishlist.data

import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import retrofit2.http.GET
import retrofit2.http.Path

// Replace with your actual server IP address
private const val BASE_URL = "http://192.168.1.100:8000/"

interface WishlistApiService {
    @GET("items")
    suspend fun getItems(): List<WishlistItem>

    @GET("items/{id}/history")
    suspend fun getItemHistory(@Path("id") itemId: String): List<PriceHistory>
}

object WishlistApi {
    val retrofitService: WishlistApiService by lazy {
        Retrofit.Builder()
            .addConverterFactory(MoshiConverterFactory.create())
            .baseUrl(BASE_URL)
            .build()
            .create(WishlistApiService::class.java)
    }
}

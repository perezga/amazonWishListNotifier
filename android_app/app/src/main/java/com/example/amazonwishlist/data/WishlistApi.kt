package com.example.amazonwishlist.data

import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import retrofit2.http.GET

// Replace with your actual server IP address
private const val BASE_URL = "http://192.168.1.100:8000/"

interface WishlistApiService {
    @GET("items")
    suspend fun getItems(): List<WishlistItem>
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

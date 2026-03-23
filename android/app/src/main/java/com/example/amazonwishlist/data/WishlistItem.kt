package com.example.amazonwishlist.data

import com.squareup.moshi.Json

data class WishlistItem(
    @Json(name = "id") val id: String,
    @Json(name = "title") val title: String,
    @Json(name = "price") val price: Double?,
    @Json(name = "priceUsed") val priceUsed: Double?,
    @Json(name = "savings") val savings: Double,
    @Json(name = "url") val url: String,
    @Json(name = "imageURL") val imageURL: String?,
    @Json(name = "bestUsedPrice") val bestUsedPrice: Double?,
    @Json(name = "wishlistName") val wishlistName: String?,
    @Json(name = "wishlistUrl") val wishlistUrl: String?
)

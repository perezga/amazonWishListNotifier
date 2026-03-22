package com.example.amazonwishlist.data

import com.squareup.moshi.Json

data class PriceHistory(
    @Json(name = "id") val id: Int,
    @Json(name = "item_id") val itemId: String,
    @Json(name = "price") val price: Double?,
    @Json(name = "price_used") val priceUsed: Double?,
    @Json(name = "savings") val savings: Double?,
    @Json(name = "timestamp") val timestamp: String
)

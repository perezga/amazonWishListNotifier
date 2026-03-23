package com.example.amazonwishlist.data

import com.squareup.moshi.Json

data class Notification(
    @Json(name = "id") val id: Int,
    @Json(name = "item_id") val itemId: String,
    @Json(name = "title") val title: String,
    @Json(name = "message") val message: String,
    @Json(name = "price") val price: Float,
    @Json(name = "timestamp") val timestamp: String,
    @Json(name = "is_read") val isRead: Int
)

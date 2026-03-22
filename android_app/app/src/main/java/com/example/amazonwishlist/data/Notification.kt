package com.example.amazonwishlist.data

data class Notification(
    val id: Int,
    val item_id: String,
    val title: String,
    val message: String,
    val price: Float,
    val timestamp: String,
    val is_read: Int
)

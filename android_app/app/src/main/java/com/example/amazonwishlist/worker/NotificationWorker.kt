package com.example.amazonwishlist.worker

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.example.amazonwishlist.MainActivity
import com.example.amazonwishlist.data.WishlistApi
import java.util.concurrent.atomic.AtomicInteger

class NotificationWorker(
    context: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(context, workerParams) {

    companion object {
        private const val PREFS_NAME = "amazon_wishlist_prefs"
        private const val LAST_NOTIFICATION_ID_KEY = "last_notification_id"
        private const val CHANNEL_ID = "price_drop_channel"
        private val notificationIdCounter = AtomicInteger(1)
    }

    override suspend fun doWork(): Result {
        return try {
            val notifications = WishlistApi.retrofitService.getNotifications()
            val prefs = applicationContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            val lastSeenId = prefs.getInt(LAST_NOTIFICATION_ID_KEY, 0)

            val newNotifications = notifications.filter { it.id > lastSeenId }.sortedBy { it.id }

            if (newNotifications.isNotEmpty()) {
                createNotificationChannel()
                for (notification in newNotifications) {
                    showNotification(notification)
                }
                prefs.edit().putInt(LAST_NOTIFICATION_ID_KEY, newNotifications.last().id).apply()
            }

            Result.success()
        } catch (e: Exception) {
            Result.retry()
        }
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val name = "Price Drops"
            val descriptionText = "Notifications for price drops in your Amazon wishlist"
            val importance = NotificationManager.IMPORTANCE_DEFAULT
            val channel = NotificationChannel(CHANNEL_ID, name, importance).apply {
                description = descriptionText
            }
            val notificationManager: NotificationManager =
                applicationContext.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            notificationManager.createNotificationChannel(channel)
        }
    }

    private fun showNotification(notification: com.example.amazonwishlist.data.Notification) {
        val intent = Intent(applicationContext, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        }
        val pendingIntent: PendingIntent = PendingIntent.getActivity(
            applicationContext, 0, intent,
            PendingIntent.FLAG_IMMUTABLE
        )

        val builder = NotificationCompat.Builder(applicationContext, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_info) // Fallback icon
            .setContentTitle(notification.title)
            .setContentText(notification.message)
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)

        with(NotificationManagerCompat.from(applicationContext)) {
            if (ActivityCompat.checkSelfPermission(
                    applicationContext,
                    Manifest.permission.POST_NOTIFICATIONS
                ) == PackageManager.PERMISSION_GRANTED || Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU
            ) {
                notify(notificationIdCounter.incrementAndGet(), builder.build())
            }
        }
    }
}
